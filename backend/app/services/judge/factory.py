"""Judge 工厂。"""

from app.config import get_settings
from app.services.judge.base import CodeJudgeService
from app.services.judge.mock import MockCodeJudgeService


def get_judge_service() -> CodeJudgeService:
    provider = get_settings().judge_provider.lower()
    if provider == "docker":
        from app.services.judge.docker import DockerCodeJudgeService

        return DockerCodeJudgeService()
    if provider in {"codecrucible", "crucible"}:
        from app.services.judge.codecrucible import CodeCrucibleJudgeService

        return CodeCrucibleJudgeService()
    if provider == "auto":
        settings = get_settings()
        if settings.codecrucible_base_url:
            from app.services.judge.codecrucible import CodeCrucibleJudgeService

            return CodeCrucibleJudgeService()
    return MockCodeJudgeService()
