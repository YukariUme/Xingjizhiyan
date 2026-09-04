"""学习中心路由：AI 学科导师、代码诊断、学习画像与个性化路径。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import User
from app.repositories.learning_repo import LearningRepository
from app.models import ChatMessage
from app.schemas.learning import DiagnosisIn, TutorChatIn
from app.services.agent.factory import get_agent_service
from app.services.learning_path_service import LearningPathService

router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.post("/tutor")
def tutor_chat(
    data: TutorChatIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """AI 学科导师：提示模式 / 详细解析模式，回答附带知识点与引用来源。"""
    agent = get_agent_service("learning")
    return agent.run(
        db,
        user,
        {"task": "tutor", "message": data.message, "mode": data.mode, "history": data.history},
    )


@router.post("/diagnose")
def diagnose_code(
    data: DiagnosisIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """AI 代码错误诊断。"""
    agent = get_agent_service("learning")
    return agent.run(
        db,
        user,
        {
            "task": "diagnose",
            "question_title": data.question_title,
            "question_description": data.question_description,
            "source_code": data.source_code,
            "language": data.language,
            "judge_report": data.judge_report,
            "error_message": data.error_message,
            "mode": data.mode,
        },
    )


@router.get("/history")
def chat_history(
    agent_type: str = "learning",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    messages = LearningRepository.list_messages(db, user.id, agent_type, limit=50)
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "knowledge_points": m.knowledge_points,
            "references": m.references,
            "created_at": m.created_at.isoformat(),
        }
        for m in reversed(messages)
    ]


@router.delete("/history")
def clear_chat_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """清空自己的 AI 学科导师对话历史。"""
    db.query(ChatMessage).filter(
        ChatMessage.user_id == user.id, ChatMessage.agent_type == "learning"
    ).delete()
    db.commit()
    return {"ok": True}


@router.get("/profile")
def learning_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.services.analytics_service import AnalyticsService

    return AnalyticsService.student_profile(db, user.id)


@router.get("/recommendations")
def recommendations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """返回（并按需生成）个性化学习路径。"""
    items = LearningRepository.list_recommendations(db, user.id)
    if not items:
        items = LearningPathService.generate(db, user.id)
    from app.models import KnowledgePoint

    return [
        {
            "id": r.id,
            "student_id": r.student_id,
            "knowledge_point_id": r.knowledge_point_id,
            "knowledge_point": (
                db.get(KnowledgePoint, r.knowledge_point_id).name
                if r.knowledge_point_id and db.get(KnowledgePoint, r.knowledge_point_id)
                else ""
            ),
            "reason": r.reason,
            "resource_title": r.resource_title,
            "resource_type": r.resource_type,
            "resource_ref": r.resource_ref,
            "priority": r.priority,
            "created_at": r.created_at.isoformat(),
        }
        for r in items
    ]


@router.post("/path/generate")
def generate_path(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可以使用个性化学习路径")
    items = LearningPathService.generate(db, user.id)
    return {"ok": True, "count": len(items)}
