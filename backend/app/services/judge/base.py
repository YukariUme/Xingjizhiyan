"""CodeJudgeService 统一接口。

输入 source code + language + test cases，输出统一评测结果。
未来可替换为 Docker / 安全沙箱等真实评测服务，业务代码无需改动。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TestCaseResult:
    """单个测试点的结果。"""

    test_id: int
    name: str
    passed: bool
    message: str = ""
    expected: str = ""
    actual: str = ""
    time_ms: int = 0


@dataclass
class JudgeResult:
    """一次代码评测的完整结果。"""

    # accepted | wrong_answer | compile_error | time_limit_exceeded
    # | memory_limit_exceeded | runtime_error | internal_error
    verdict: str
    passed_tests: int
    total_tests: int
    runtime_ms: int = 0
    error_message: str = ""
    report: list[TestCaseResult] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class CodeJudgeService(ABC):
    """代码评测服务统一接口。"""

    name: str = "base"

    @abstractmethod
    def judge(
        self,
        source_code: str,
        language: str,
        test_cases: list[dict],
    ) -> JudgeResult:
        """评测源代码并返回统一结果。"""
        raise NotImplementedError
