"""DockerCodeJudgeService：Docker 容器沙箱判题。

每个提交在一次性容器中执行：
  - --network none          ：断网，学生代码无法外联/泄露数据
  - --read-only + tmpfs     ：根文件系统只读，代码只能写 /sandbox 与 /tmp
  - --memory / --cpus / --pids-limit：硬性 CPU/内存/进程数限制（OOM 由内核杀）
  - --rm                    ：结束后容器自动删除，无残留
  - 容器内 bash runner 编译 → 逐测试点运行 → 输出 results.txt（同 CodeCrucible 语义）

语言镜像（可配置）：python:3.11-slim / gcc:13 / eclipse-temurin:17-jdk。
Docker 不可用时返回可读错误（internal_error），不会降级为本地裸跑。
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.judge.base import CodeJudgeService, JudgeResult, TestCaseResult
from app.services.judge.codecrucible import (
    VERDICT_AC,
    VERDICT_CE,
    VERDICT_INTERNAL,
    VERDICT_MLE,
    VERDICT_RE,
    VERDICT_TLE,
    VERDICT_WA,
    _LANG_ALIASES,
)

_RUNNER_TEMPLATE = r"""#!/usr/bin/env bash
# 容器内判题 runner（bash 实现，兼容 python/gcc/temurin 镜像）
set -u
cd "$(dirname "$0")"

RUN_LANG="$1"
TIME_MS="$2"
RESULTS=/sandbox/results.txt
CURRENT=/sandbox/current.txt
: > "$RESULTS"
: > "$CURRENT"

slack=2
wall=$(( (TIME_MS + 999) / 1000 + slack ))

normalize() { sed 's/[[:space:]]*$//' | grep -v '^$'; }

echo "CE|编译中" > "$RESULTS"
case "$RUN_LANG" in
  python)
    python3 -m py_compile solution.py 2> compile_err.txt || {
      echo "CE|$(head -c 800 compile_err.txt)"; exit 0; }
    RUN_CMD="python3 solution.py"
    ;;
  c)
    gcc -O2 -std=c11 -o a.out solution.c 2> compile_err.txt || {
      echo "CE|$(head -c 800 compile_err.txt)"; exit 0; }
    RUN_CMD="./a.out"
    ;;
  cpp)
    g++ -O2 -std=c++17 -o a.out solution.cpp 2> compile_err.txt || {
      echo "CE|$(head -c 800 compile_err.txt)"; exit 0; }
    RUN_CMD="./a.out"
    ;;
  java)
    javac -encoding UTF-8 Main.java 2> compile_err.txt || {
      echo "CE|$(head -c 800 compile_err.txt)"; exit 0; }
    RUN_CMD="java -cp . Main"
    ;;
  *)
    echo "CE|不支持的容器语言: $RUN_LANG"; exit 0
    ;;
esac

: > "$RESULTS"
N=$(ls case_*.in 2>/dev/null | wc -l)
for i in $(seq 1 "$N" 2>/dev/null); do
  echo "$i" > "$CURRENT"
  start=$(date +%s%N)
  timeout "$wall" $RUN_CMD < "case_$i.in" > "out_$i.txt" 2> "err_$i.txt"
  rc=$?
  end=$(date +%s%N)
  ms=$(( (end - start) / 1000000 ))
  if [ "$rc" -eq 124 ]; then
    echo "FAIL|TLE|运行超时" >> "$RESULTS"
    continue
  fi
  if [ "$rc" -ne 0 ]; then
    echo "FAIL|RE|exit=$rc $(head -c 300 "err_$i.txt")" >> "$RESULTS"
    continue
  fi
  if normalize < "out_$i.txt" | cmp -s - <(normalize < "case_$i.out"); then
    echo "PASS|$ms" >> "$RESULTS"
  else
    echo "FAIL|WA|输出与期望不符" >> "$RESULTS"
  fi
done
echo "done" > "$CURRENT"
"""

_DOCKER_VERDICT_MAP = {
    "AC": VERDICT_AC,
    "WA": VERDICT_WA,
    "TLE": VERDICT_TLE,
    "MLE": VERDICT_MLE,
    "RE": VERDICT_RE,
    "CE": VERDICT_CE,
}


class DockerCodeJudgeService(CodeJudgeService):
    name = "docker-sandbox"

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
        if not test_cases:
            return JudgeResult(
                verdict=VERDICT_INTERNAL,
                passed_tests=0,
                total_tests=0,
                error_message="该题目尚未配置测试点，请教师在作业编辑中补充标准输入输出。",
            )
        docker = shutil.which("docker")
        if not docker:
            return self._docker_unavailable(
                "未检测到 docker 命令。请安装并启动 Docker Desktop 后重试，"
                "或设置 JUDGE_PROVIDER=codecrucible 接入远程判题集群。",
                test_cases,
            )
        base = Path(__file__).resolve().parent.parent.parent / "data" / "judge_work"
        base.mkdir(parents=True, exist_ok=True)
        workdir = Path(tempfile.mkdtemp(prefix="jbgs-docker-judge-", dir=str(base)))
        try:
            self._prepare_workdir(Path(workdir), source_code, lang, test_cases)
            return self._run_container(docker, Path(workdir), lang, test_cases)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    # ------------------------------------------------------------------
    def _prepare_workdir(
        self, workdir: Path, source_code: str, language: str, test_cases: list[dict]
    ) -> None:
        ext = {"python": "solution.py", "c": "solution.c", "cpp": "solution.cpp", "java": "Main.java"}[language]
        (workdir / ext).write_text(source_code, encoding="utf-8")
        (workdir / "runner.sh").write_text(_RUNNER_TEMPLATE, encoding="utf-8")
        names: list[str] = []
        for idx, tc in enumerate(test_cases, 1):
            (workdir / f"case_{idx}.in").write_text(str(tc.get("input", tc.get("stdin", ""))), encoding="utf-8")
            (workdir / f"case_{idx}.out").write_text(str(tc.get("output", tc.get("stdout", ""))), encoding="utf-8")
            names.append(str(tc.get("name", f"测试点 {idx}")))
        (workdir / "names.txt").write_text("\n".join(names), encoding="utf-8")

    def _run_container(
        self, docker: str, workdir: Path, language: str, test_cases: list[dict]
    ) -> JudgeResult:
        settings = get_settings()
        image = {
            "python": settings.judge_docker_image_python,
            "c": settings.judge_docker_image_c,
            "cpp": settings.judge_docker_image_cpp,
            "java": settings.judge_docker_image_java,
        }[language]
        time_limit = int(test_cases[0].get("time_limit_ms", settings.judge_time_limit_ms)) if test_cases else settings.judge_time_limit_ms
        mem_kb = int(test_cases[0].get("memory_limit_kb", settings.judge_memory_limit_kb)) if test_cases else settings.judge_memory_limit_kb
        cmd = [
            docker, "run", "--rm",
            "--network", "none",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--memory", f"{mem_kb}k",
            "--cpus", str(settings.judge_docker_cpus),
            "--pids-limit", str(settings.judge_docker_pids_limit),
        ]
        sub_dir = workdir.name
        if settings.judge_docker_volume_name:
            # 后端容器化：判题工作目录经命名卷与后端共享
            cmd += ["-v", f"{settings.judge_docker_volume_name}:/sandbox"]
            judge_wd = f"/sandbox/judge_work/{sub_dir}"
            runner_path = f"{judge_wd}/runner.sh"
        else:
            cmd += ["-v", f"{str(workdir).replace(chr(92), '/')}:/sandbox"]
            judge_wd = "/sandbox"
            runner_path = "/sandbox/runner.sh"
        cmd += ["-w", judge_wd, image, "bash", runner_path, language, str(time_limit)]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.judge_docker_global_timeout_s,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            return JudgeResult(
                verdict=VERDICT_INTERNAL,
                passed_tests=0,
                total_tests=len(test_cases),
                error_message=f"Docker 判题整体超时（>{settings.judge_docker_global_timeout_s}s）。",
            )
        except Exception as exc:  # noqa: BLE001 - Docker 守护进程不可用等
            return self._docker_unavailable(f"Docker 执行失败：{exc}", test_cases)

        results = self._read_results(workdir)
        # 容器被 OOM 杀死（exit 137）：定位当前测试点并标记 MLE
        if proc.returncode == 137:
            current = (workdir / "current.txt").read_text(encoding="utf-8", errors="replace").strip()
            idx = int(current) if current.isdigit() else None
            if not results and idx and idx <= len(test_cases):
                results = [(idx, "FAIL", VERDICT_MLE, "内存超限（Memory Limit Exceeded）")]
            elif len(results) < len(test_cases):
                # 容器中途被 OOM 杀死：当前用例标记 MLE，其余未测用例标记容器异常
                done = {r[0] for r in results}
                start = idx if idx and idx not in done else (max(done) + 1 if done else 1)
                for i in range(start, len(test_cases) + 1):
                    if i not in done:
                        results.append((i, "FAIL", VERDICT_MLE, "容器内存超限，后续测试点未执行"))
        if not results:
            detail = (proc.stderr or "")[:500] or f"容器退出码 {proc.returncode}（镜像 {image} 是否已拉取？）"
            return self._docker_unavailable(f"判题容器未产出结果：{detail}", test_cases)

        report: list[TestCaseResult] = []
        passed = 0
        final_verdict = VERDICT_AC
        worst_time = 0
        for idx, status, verdict, message in results:
            tc = test_cases[idx - 1] if idx - 1 < len(test_cases) else {}
            ok = status == "PASS"
            time_ms = 0
            if ok:
                passed += 1
                try:
                    time_ms = int(message)
                except ValueError:
                    time_ms = 0
                message = "通过"
            elif verdict in (VERDICT_TLE, VERDICT_MLE, VERDICT_RE):
                final_verdict = verdict
            worst_time = max(worst_time, time_ms)
            report.append(
                TestCaseResult(
                    test_id=int(tc.get("id", idx)),
                    name=str(tc.get("name", f"测试点 {idx}")),
                    passed=ok,
                    message=message,
                    expected=str(tc.get("output", ""))[:200],
                    actual="通过" if ok else "未通过",
                    time_ms=time_ms,
                )
            )
        total = len(test_cases)
        verdict = final_verdict if passed == total and total > 0 else (
            final_verdict if final_verdict != VERDICT_AC else VERDICT_WA
        )
        return JudgeResult(
            verdict=verdict,
            passed_tests=passed,
            total_tests=total,
            runtime_ms=worst_time,
            error_message="" if verdict == VERDICT_AC else next(
                (r.message for r in report if not r.passed), "存在未通过的测试点"
            ),
            report=report,
            metadata={"engine": "docker-sandbox", "image": image},
        )

    @staticmethod
    def _read_results(workdir: Path) -> list[tuple[int, str, str, str]]:
        """解析 results.txt（PASS|ms / FAIL|TLE|msg / FAIL|WA|msg / FAIL|RE|msg / CE|msg）。"""
        path = workdir / "results.txt"
        if not path.is_file():
            return []
        rows: list[tuple[int, str, str, str]] = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            parts = line.split("|", 2)
            if len(parts) < 2:
                continue
            status = parts[0]
            if status == "CE":
                rows.append((1, "FAIL", VERDICT_CE, parts[1] if len(parts) > 1 else "编译错误"))
                break
            if status == "PASS" and len(parts) >= 2:
                rows.append((line_no, "PASS", VERDICT_AC, parts[1]))
            elif status == "FAIL" and len(parts) >= 3:
                rows.append(
                    (
                        line_no,
                        "FAIL",
                        _DOCKER_VERDICT_MAP.get(parts[1].upper(), VERDICT_WA),
                        parts[2],
                    )
                )
        return rows

    @staticmethod
    def _docker_unavailable(message: str, test_cases: list[dict]) -> JudgeResult:
        return JudgeResult(
            verdict=VERDICT_INTERNAL,
            passed_tests=0,
            total_tests=len(test_cases),
            error_message=message,
            metadata={"engine": "docker-sandbox", "available": False},
        )
