"""MockCodeJudgeService：静态规则评测（不执行任意用户代码）。

安全原则：MVP 阶段不运行用户代码，仅通过静态检查 + 规则判定，
为未来替换 Docker / 安全沙箱保留统一接口。
"""

import hashlib
import re

from app.services.judge.base import CodeJudgeService, JudgeResult, TestCaseResult

SUPPORTED_LANGUAGES = {"python", "java", "c", "cpp", "c++", "javascript", "js", "go"}


class MockCodeJudgeService(CodeJudgeService):
    name = "mock"

    def judge(
        self,
        source_code: str,
        language: str,
        test_cases: list[dict],
    ) -> JudgeResult:
        lang = language.lower()
        if lang not in SUPPORTED_LANGUAGES:
            return JudgeResult(
                verdict="compile_error",
                passed_tests=0,
                total_tests=len(test_cases),
                error_message=f"暂不支持的语言：{language}（Mock Judge 支持：{', '.join(sorted(SUPPORTED_LANGUAGES))}）",
            )
        if not source_code.strip():
            return JudgeResult(
                verdict="compile_error",
                passed_tests=0,
                total_tests=len(test_cases),
                error_message="提交的代码为空，请先编写实现后再提交。",
            )

        report: list[TestCaseResult] = []
        passed = 0
        for tc in test_cases:
            tc_id = int(tc.get("id", 0))
            name = tc.get("name", f"测试点 {tc_id}")
            check = tc.get("check", "contains")
            value = str(tc.get("value", ""))
            hint = tc.get("hint", "")
            expected = tc.get("expected", value)

            ok, message = self._check_case(source_code, check, value, hint, lang)
            if ok:
                passed += 1
            report.append(
                TestCaseResult(
                    test_id=tc_id,
                    name=name,
                    passed=ok,
                    message=message,
                    expected=expected,
                    actual="通过" if ok else "未通过",
                    time_ms=self._stable_time(source_code, tc_id),
                )
            )

        total = len(test_cases)
        if passed == total and total > 0:
            verdict = "accepted"
            error = ""
        else:
            verdict = "wrong_answer"
            error = next((r.message for r in report if not r.passed), "存在未通过的测试点")

        # 常见静态错误检测，增强演示效果
        static_error = self._detect_static_error(source_code)
        if static_error and passed < total:
            verdict = "wrong_answer"
            error = static_error

        runtime_ms = sum(r.time_ms for r in report)
        return JudgeResult(
            verdict=verdict,
            passed_tests=passed,
            total_tests=total,
            runtime_ms=runtime_ms,
            error_message=error,
            report=report,
        )

    @staticmethod
    def _check_case(
        code: str, check: str, value: str, hint: str, language: str = "python"
    ) -> tuple[bool, str]:
        """按检查规则判定单个测试点。"""
        if check == "regex":
            ok = re.search(value, code, re.S) is not None
            msg = "匹配到要求的代码模式" if ok else f"未匹配到模式：{value}"
            return ok, msg
        if check == "not_contains":
            ok = value not in code
            msg = "代码中不包含应避免的内容" if ok else f"代码中包含应避免的内容：{value}"
            return ok, msg
        # 默认 contains：兼容跨语言（如 “def reverse_list” 在 C/Java 中检查函数名）
        match = re.search(r"def\s+([A-Za-z_]\w*)", value)
        if match and "def " in value:
            identifier = match.group(1)
            variants = {identifier}
            if "_" in identifier:
                parts = identifier.split("_")
                variants.add(parts[0] + "".join(p.title() for p in parts[1:]))
            ok = any(re.search(rf"\b{re.escape(v)}\b", code) for v in variants)
            msg = (
                f"包含要求的关键结构：{value}"
                if ok
                else f"缺少要求的关键结构：{value}（{hint}）"
            )
            return ok, msg
        candidates = [value]
        if language != "python":
            # 常见跨语言关键字等价（None→null/nullptr、True/False→true/false）
            value_key = value.strip()
            equivalents = {
                "None": ["null", "nullptr", "NULL"],
                "True": ["true"],
                "False": ["false"],
            }
            candidates += equivalents.get(value_key, [])
        ok = any(c in code for c in candidates)
        msg = (
            f"包含要求的关键结构：{value}"
            if ok
            else f"缺少要求的关键结构：{value}。{hint}"
        )
        return ok, msg

    @staticmethod
    def _detect_static_error(code: str) -> str:
        """检测常见静态问题，用于演示错误诊断。"""
        if re.search(r"\bpass\b", code) and "def " in code:
            return "函数体仍是占位符 pass，尚未实现核心逻辑。"
        if "TODO" in code.upper():
            return "代码中包含未完成的 TODO 标记。"
        return ""

    @staticmethod
    def _stable_time(code: str, test_id: int) -> int:
        """基于代码与测试点的确定性伪运行时间。"""
        h = int(hashlib.md5(f"{code}|{test_id}".encode()).hexdigest()[:8], 16)
        return 3 + h % 40
