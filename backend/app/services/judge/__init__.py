"""代码评测抽象层。"""

from app.services.judge.base import CodeJudgeService, JudgeResult, TestCaseResult
from app.services.judge.factory import get_judge_service
from app.services.judge.mock import MockCodeJudgeService

__all__ = ["CodeJudgeService", "JudgeResult", "TestCaseResult", "get_judge_service", "MockCodeJudgeService"]

