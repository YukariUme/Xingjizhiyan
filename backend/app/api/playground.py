"""随堂代码 Playground：现场运行代码片段（非作业判题）。"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.services.judge.factory import get_judge_service

router = APIRouter(prefix="/api/playground", tags=["playground"])


@router.post("/run")
def run_code(data: dict, _user=Depends(get_current_user)) -> dict:
    """运行一段代码并返回 stdout/stderr/exit code（复用 Judge 沙箱）。"""
    code = str(data.get("code", ""))
    language = str(data.get("language", "python"))
    stdin = str(data.get("stdin", ""))
    return get_judge_service().run(code, language, stdin)
