"""CodeCrucibleJudgeService：按 CodeCrucible 判题逻辑接入真实代码评测。

两种模式：
1. 本地模式（默认）：复用 CodeCrucible judge-worker 的判题语义
   （编译 → 逐测试点运行 → 双计时 → AC/WA/TLE/MLE/RE/CE），
   在开发者机器上直接运行，不依赖 K8s / Kafka / MinIO。
   注意：本地模式未做 nsjail 级隔离，仅限开发与演示
   （JUDGE_ALLOW_UNSAFE_LOCAL=true），生产请接远程 CodeCrucible 集群。
2. 远程模式：配置 CODECRUCIBLE_BASE_URL 后，通过 submission-service
   HTTP API 提交并轮询结果（与 CodeCrucible 判题集群同语义）。

语言支持：python / c / cpp / java（远程模式受 CodeCrucible 侧语言白名单限制）。
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.services.judge.base import CodeJudgeService, JudgeResult, TestCaseResult


VERDICT_AC = "accepted"
VERDICT_WA = "wrong_answer"
VERDICT_CE = "compile_error"
VERDICT_TLE = "time_limit_exceeded"
VERDICT_MLE = "memory_limit_exceeded"
VERDICT_RE = "runtime_error"
VERDICT_INTERNAL = "internal_error"

# CodeCrucible 终态 verdict → 本平台 verdict
_CRUCIBLE_VERDICT_MAP = {
    "AC": VERDICT_AC,
    "WA": VERDICT_WA,
    "TLE": VERDICT_TLE,
    "MLE": VERDICT_MLE,
    "RE": VERDICT_RE,
    "CE": VERDICT_CE,
}

_LANG_ALIASES = {"c++": "cpp", "c": "c", "python": "python", "py": "python", "java": "java"}
_WALL_SLACK_SECONDS = int(os.getenv("JUDGE_WALL_SLACK_SECONDS", "2"))


@dataclass
class _RunOutcome:
    exit_code: int
    stdout: str
    stderr: str
    time_ms: int
    memory_kb: int
    timed_out: bool
    oom_killed: bool = False


class CodeCrucibleJudgeService(CodeJudgeService):
    name = "codecrucible"

    def judge(self, source_code: str, language: str, test_cases: list[dict]) -> JudgeResult:
        lang = _LANG_ALIASES.get(language.lower().strip(), language.lower().strip())
        if lang not in {"python", "c", "cpp", "java"}:
            return JudgeResult(
                verdict=VERDICT_CE,
                passed_tests=0,
                total_tests=len(test_cases),
                error_message=f"暂不支持的语言：{language}（支持 python / c / cpp / java）",
            )
        if not source_code.strip():
            return JudgeResult(
                verdict=VERDICT_CE,
                passed_tests=0,
                total_tests=len(test_cases),
                error_message="提交的代码为空，请先编写实现后再提交。",
            )
        settings = get_settings()
        if settings.codecrucible_base_url:
            return self._judge_remote(source_code, lang, test_cases)
        if not settings.judge_allow_unsafe_local:
            return JudgeResult(
                verdict=VERDICT_INTERNAL,
                passed_tests=0,
                total_tests=len(test_cases),
                error_message="本地执行已禁用（JUDGE_ALLOW_UNSAFE_LOCAL=false），请配置 CODECRUCIBLE_BASE_URL 接入判题集群。",
            )
        return self._judge_local(source_code, lang, test_cases)

    # ------------------------------------------------------------------
    # 本地模式：复用 CodeCrucible 判题语义
    # ------------------------------------------------------------------
    def _judge_local(self, source_code: str, language: str, test_cases: list[dict]) -> JudgeResult:
        settings = get_settings()
        workdir = tempfile.mkdtemp(prefix=f"crucible-{int(time.time())}-")
        try:
            source_path = self._write_source(workdir, source_code, language)
            compile_error = self._compile(workdir, source_path, language)
            if compile_error:
                return JudgeResult(
                    verdict=VERDICT_CE,
                    passed_tests=0,
                    total_tests=len(test_cases),
                    error_message=f"编译失败：\n{compile_error[:800]}",
                )

            report: list[TestCaseResult] = []
            passed = 0
            worst_time = 0
            worst_memory = 0
            final_verdict = VERDICT_AC
            for tc in test_cases:
                tc_id = int(tc.get("id", 0))
                name = tc.get("name", f"测试点 {tc_id}")
                # 兼容旧式静态检查测试点
                if "check" in tc:
                    ok, verdict, message, time_ms = self._static_check(source_code, tc, language)
                else:
                    ok, verdict, message, time_ms, memory_kb = self._run_testcase(
                        workdir,
                        language,
                        tc,
                        int(tc.get("time_limit_ms", settings.judge_time_limit_ms)),
                        int(tc.get("memory_limit_kb", settings.judge_memory_limit_kb)),
                    )
                    worst_memory = max(worst_memory, memory_kb)
                worst_time = max(worst_time, time_ms)
                if ok:
                    passed += 1
                elif verdict in (VERDICT_TLE, VERDICT_MLE, VERDICT_RE):
                    final_verdict = verdict
                report.append(
                    TestCaseResult(
                        test_id=tc_id,
                        name=name,
                        passed=ok,
                        message=message,
                        expected=str(tc.get("output", tc.get("expected", "")))[:200],
                        actual="通过" if ok else "未通过",
                        time_ms=time_ms,
                    )
                )

            total = len(test_cases)
            verdict = final_verdict if passed == total and total > 0 else (
                final_verdict if final_verdict != VERDICT_AC else VERDICT_WA
            )
            error = "" if verdict == VERDICT_AC else next(
                (r.message for r in report if not r.passed), "存在未通过的测试点"
            )
            return JudgeResult(
                verdict=verdict,
                passed_tests=passed,
                total_tests=total,
                runtime_ms=worst_time,
                error_message=error,
                report=report,
                metadata={"memory_kb": worst_memory, "engine": "codecrucible-local"},
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _write_source(self, workdir: str, source: str, language: str) -> str:
        ext = {"python": "solution.py", "c": "solution.c", "cpp": "solution.cpp", "java": "Main.java"}[language]
        path = Path(workdir) / ext
        path.write_text(source, encoding="utf-8")
        return str(path)

    def _compile(self, workdir: str, source_path: str, language: str) -> str:
        """返回空串表示编译成功，否则返回错误信息。"""
        if language == "python":
            result = self._run_cmd(
                [sys.executable, "-m", "py_compile", source_path], workdir, 20_000
            )
            return "" if result.exit_code == 0 else result.stderr[:800] or "Python 语法错误"
        if language == "java":
            javac = shutil.which("javac")
            if not javac:
                return "未检测到 javac，请先安装 JDK。"
            result = self._run_cmd([javac, "-encoding", "UTF-8", source_path], workdir, 20_000)
            return "" if result.exit_code == 0 else result.stderr[:800] or "javac 编译失败"
        compiler = shutil.which("g++" if language == "cpp" else "gcc")
        if not compiler:
            return f"未检测到 {compiler or 'g++/gcc'}，请先安装编译器。"
        std = "-std=c++17" if language == "cpp" else "-std=c11"
        out = "a.exe" if os.name == "nt" else "a.out"
        result = self._run_cmd(
            [compiler, "-O2", std, "-o", os.path.join(workdir, out), source_path],
            workdir,
            20_000,
        )
        return "" if result.exit_code == 0 else result.stderr[:800] or "编译失败"

    def _run_testcase(
        self, workdir: str, language: str, tc: dict, time_limit_ms: int, memory_limit_kb: int
    ) -> tuple[bool, str, str, int, int]:
        """按 CodeCrucible 语义运行单个测试点：stdin → stdout 对比。"""
        stdin_data = str(tc.get("input", tc.get("stdin", tc.get("in", ""))))
        expected = str(tc.get("output", tc.get("stdout", tc.get("out", ""))))
        cmd = self._run_command(workdir, language)
        outcome = self._run_cmd(
            cmd,
            workdir,
            time_limit_ms + _WALL_SLACK_SECONDS * 1000,
            stdin_data=stdin_data,
            memory_limit_kb=memory_limit_kb,
        )
        if outcome.timed_out:
            return False, VERDICT_TLE, "运行超时（Time Limit Exceeded）", outcome.time_ms, outcome.memory_kb
        if outcome.oom_killed:
            return False, VERDICT_MLE, "内存超限（Memory Limit Exceeded）", outcome.time_ms, outcome.memory_kb
        if outcome.exit_code != 0:
            return False, VERDICT_RE, f"运行错误（exit={outcome.exit_code}）：{outcome.stderr[:300]}", outcome.time_ms, outcome.memory_kb
        if tc.get("strict"):
            ok = outcome.stdout == expected
        else:
            ok = self._same_output(outcome.stdout, expected)
        message = "通过" if ok else "输出与期望不符（Wrong Answer）"
        return ok, VERDICT_AC if ok else VERDICT_WA, message, outcome.time_ms, outcome.memory_kb

    def _run_command(self, workdir: str, language: str) -> list[str]:
        if language == "python":
            return [sys.executable, "solution.py"]
        if language == "java":
            return ["java", "-cp", ".", "Main"]
        exe = "a.exe" if os.name == "nt" else "./a.out"
        return [os.path.join(workdir, exe)]

    @staticmethod
    def _same_output(actual: str, expected: str) -> bool:
        """输出对比：忽略行尾空白与末尾空行（常见 OJ 宽容策略）。"""

        def normalize(text: str) -> list[str]:
            return [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]

        a = [line for line in normalize(actual) if line]
        e = [line for line in normalize(expected) if line]
        return a == e

    def _run_cmd(
        self,
        cmd: list[str],
        cwd: str,
        timeout_ms: int,
        stdin_data: str = "",
        memory_limit_kb: int = 0,
    ) -> _RunOutcome:
        """执行命令并做双计时（CPU + 墙钟），兼容 Windows/POSIX。"""
        timeout_s = max(0.05, timeout_ms / 1000.0)
        start = time.monotonic()
        kwargs = {}
        if os.name == "posix":
            kwargs["preexec_fn"] = self._posix_rlimit(timeout_ms, memory_limit_kb)
        else:
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **kwargs,
            )
            stdout_bytes, stderr_bytes = proc.communicate(
                input=stdin_data.encode("utf-8"), timeout=timeout_s
            )
        except subprocess.TimeoutExpired as exc:
            try:
                proc.kill()
                proc.communicate()
            except Exception:  # noqa: BLE001
                pass
            return _RunOutcome(
                exit_code=-1,
                stdout="",
                stderr="wall-clock time limit exceeded",
                time_ms=int((time.monotonic() - start) * 1000),
                memory_kb=0,
                timed_out=True,
            )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
        stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")
        cpu_ms, memory_kb = self._measure_usage(proc, elapsed_ms, memory_limit_kb)
        oom = os.name == "posix" and proc.returncode == -9 and memory_kb >= memory_limit_kb
        return _RunOutcome(
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            time_ms=cpu_ms or elapsed_ms,
            memory_kb=memory_kb,
            timed_out=False,
            oom_killed=oom,
        )

    @staticmethod
    def _posix_rlimit(time_limit_ms: int, memory_limit_kb: int):
        """POSIX 子进程限制：CPU 秒数 + 内存（CodeCrucible 双计时思想）。"""
        import resource
        import signal

        cpu_s = max(1, -(-time_limit_ms // 1000))
        mem_bytes = memory_limit_kb * 1024 if memory_limit_kb > 0 else resource.RLIM_INFINITY

        def _apply() -> None:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s + 1))
            if mem_bytes != resource.RLIM_INFINITY:
                try:
                    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
                except (ValueError, OSError):
                    pass
            signal.signal(signal.SIGXCPU, signal.SIG_DFL)

        return _apply

    @staticmethod
    def _measure_usage(proc, wall_ms: int, memory_limit_kb: int) -> tuple[int, int]:
        """测量 CPU 时间与峰值内存（优先 psutil，POSIX 用 getrusage）。"""
        cpu_ms = wall_ms
        memory_kb = 0
        try:
            import psutil

            try:
                p = psutil.Process(proc.pid)
                cpu_ms = int(p.cpu_times().user * 1000 + p.cpu_times().system * 1000)
                memory_kb = int(p.memory_info().rss / 1024)
            except psutil.Error:
                pass
        except ImportError:
            pass
        if os.name == "posix":
            import resource

            usage = resource.getrusage(resource.RUSAGE_CHILDREN)
            if memory_kb == 0:
                memory_kb = int(usage.ru_maxrss)  # Linux: KB；macOS: bytes
                if sys.platform == "darwin":
                    memory_kb //= 1024
        return max(0, cpu_ms), max(0, memory_kb)

    def _static_check(self, source_code: str, tc: dict, language: str) -> tuple[bool, str, str, int]:
        """旧式静态检查测试点：委托 MockCodeJudgeService 的规则。"""
        from app.services.judge.mock import MockCodeJudgeService

        result = MockCodeJudgeService().judge(
            source_code,
            language,
            [tc],
        )
        report = result.report[0] if result.report else None
        return (
            result.passed_tests > 0,
            VERDICT_AC if result.passed_tests > 0 else VERDICT_WA,
            report.message if report else ("通过" if result.passed_tests else "未通过"),
            report.time_ms if report else 0,
        )

    # ------------------------------------------------------------------
    # 远程模式：CodeCrucible submission-service HTTP API
    # ------------------------------------------------------------------
    def _judge_remote(self, source_code: str, language: str, test_cases: list[dict]) -> JudgeResult:
        settings = get_settings()
        import uuid

        import httpx

        base = settings.codecrucible_base_url.rstrip("/")
        problem_id = settings.codecrucible_problem_id
        if not problem_id:
            return JudgeResult(
                verdict=VERDICT_INTERNAL,
                passed_tests=0,
                total_tests=len(test_cases),
                error_message="远程判题需要配置 CODECRUCIBLE_PROBLEM_ID。",
            )
        if language not in {"python", "cpp"}:
            return JudgeResult(
                verdict=VERDICT_CE,
                passed_tests=0,
                total_tests=len(test_cases),
                error_message=f"CodeCrucible 远程判题暂不支持 {language}（支持 python / cpp）。",
            )
        headers = {"Authorization": f"Bearer {self._remote_token(settings)}"}
        payload = {
            "problem_id": str(uuid.UUID(problem_id) if _is_uuid(problem_id) else problem_id),
            "language": language,
            "source_code": source_code,
        }
        try:
            resp = httpx.post(f"{base}/api/submissions", json=payload, headers=headers, timeout=20)
            resp.raise_for_status()
            submission = resp.json()
            sid = submission["id"]
            for _ in range(180):
                detail = httpx.get(
                    f"{base}/api/submissions/{sid}", headers=headers, timeout=10
                ).json()
                if detail.get("verdict"):
                    return self._map_remote_result(detail, test_cases)
                time.sleep(0.5)
            return JudgeResult(
                verdict=VERDICT_INTERNAL,
                passed_tests=0,
                total_tests=len(test_cases),
                error_message="远程判题超时（90 秒未返回结果）。",
            )
        except Exception as exc:  # noqa: BLE001
            return JudgeResult(
                verdict=VERDICT_INTERNAL,
                passed_tests=0,
                total_tests=len(test_cases),
                error_message=f"远程判题请求失败：{exc}",
            )

    @staticmethod
    def _remote_token(settings) -> str:
        if settings.codecrucible_auth_token:
            return settings.codecrucible_auth_token
        if settings.codecrucible_jwt_secret:
            import jwt
            import time as _time

            return jwt.encode(
                {"sub": "jbgs-platform", "exp": int(_time.time()) + 3600},
                settings.codecrucible_jwt_secret,
                algorithm="HS256",
            )
        return ""

    def _map_remote_result(self, detail: dict, test_cases: list[dict]) -> JudgeResult:
        verdict = _CRUCIBLE_VERDICT_MAP.get((detail.get("verdict") or "").upper(), VERDICT_INTERNAL)
        passed = int(detail.get("passed_cases") or 0)
        total = int(detail.get("total_cases") or len(test_cases))
        return JudgeResult(
            verdict=verdict,
            passed_tests=passed,
            total_tests=total,
            runtime_ms=int(detail.get("time_used_ms") or 0),
            error_message=detail.get("message") or "",
            metadata={"engine": "codecrucible-remote", "submission_id": detail.get("id")},
        )


def _is_uuid(value: str) -> bool:
    import uuid

    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False
