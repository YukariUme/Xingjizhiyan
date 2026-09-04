"""统一 AI 助手入口：按 Agent 类型路由到不同业务逻辑。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import User
from app.services.agent.factory import get_agent_service
from app.services.workflow.service import WorkflowService

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/assistant")
def assistant(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """统一入口：{agent: teaching|learning|research, payload: {...}}。"""
    agent_type = data.get("agent", "learning")
    if agent_type not in {"teaching", "learning", "research"}:
        raise HTTPException(status_code=400, detail="不支持的 Agent 类型")
    payload = data.get("payload") or {}
    if agent_type == "learning":
        # 课程答疑走“课程答疑工作流”，保证可追踪（RAG 命中/扩展知识 + 对话历史）
        payload.setdefault("mode", "hint")
        payload.setdefault("history", [])
        run = WorkflowService.run(db, "tutor", payload, user)
        if run.status == "failed":
            raise HTTPException(status_code=500, detail=run.error)
        content = dict(run.output_json.get("agent") or {})
        content["workflow_run_id"] = run.id
        return content
    agent = get_agent_service(agent_type)
    return agent.run(db, user, payload)
