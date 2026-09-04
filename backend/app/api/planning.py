"""教案历史路由：自动保存的教案可查看、复用与删除。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models import LessonPlan, User
from app.repositories.course_repo import CourseRepository
from app.schemas.course import LessonPlanOut

router = APIRouter(prefix="/api/lesson-plans", tags=["lesson-plans"])


def _owned(db: Session, user: User, plan_id: int) -> LessonPlan:
    plan = db.get(LessonPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="教案不存在")
    if plan.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能查看自己的教案")
    return plan


@router.get("", response_model=list[LessonPlanOut])
def list_lesson_plans(
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> list[LessonPlanOut]:
    """查看自己自动保存的历史教案（最新在前）。"""
    plans = CourseRepository.list_lesson_plans(db, user.id)
    return [LessonPlanOut.model_validate(p) for p in plans]


@router.get("/{plan_id}", response_model=LessonPlanOut)
def get_lesson_plan(
    plan_id: int,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> LessonPlanOut:
    return LessonPlanOut.model_validate(_owned(db, user, plan_id))


@router.delete("/{plan_id}")
def delete_lesson_plan(
    plan_id: int,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    plan = _owned(db, user, plan_id)
    db.delete(plan)
    db.commit()
    return {"ok": True}

