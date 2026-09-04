"""学情分析路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models import User
from app.repositories.course_repo import CourseRepository
from app.services.analytics_service import AnalyticsService
from app.services.llm.factory import get_llm_service
from app.services.ai_meta import ai_meta, references_from_hits
from app.services.rag.factory import get_rag_service
from app.services.workflow.service import WorkflowService


def _parse_json(raw: str) -> dict:
    import json
    import re

    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/courses/{course_id}")
def course_analytics(
    course_id: int,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    course = CourseRepository.get(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能分析自己课程的学情")
    return AnalyticsService.class_analytics(db, course_id)


@router.get("/me")
def my_analytics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role != "student":
        return {"student_id": user.id, "knowledge": [], "weak_points": [], "strong_points": [], "avg_mastery": 0}
    return AnalyticsService.student_profile(db, user.id)


@router.post("/courses/{course_id}/diagnose")
def diagnose_course(
    course_id: int,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    """AI 教学诊断：数据 → 诊断 → 教学建议（可“采用建议”进入教学设计）。"""
    course = CourseRepository.get(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能诊断自己课程")
    """AI 教学诊断（教学诊断工作流）：数据 → 诊断 → 建议 → 可追踪。"""
    run = WorkflowService.run(db, "diagnose", {"course_id": course_id}, user)
    if run.status == "failed":
        raise HTTPException(status_code=500, detail=run.error)
    agent_out = run.output_json.get("agent", {})
    return {
        "analytics": agent_out.get("analytics", {}),
        "diagnosis": agent_out.get("diagnosis", {}),
        "workflow_run_id": run.id,
    }
