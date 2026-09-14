"""可重复自学链（LearningSession）HTTP 路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models import Course, LearningSession, User
from app.repositories.course_repo import CourseRepository
from app.services.learning_session_service import LearningSessionService

router = APIRouter(prefix="/api/sessions", tags=["learning-session"])


def _session_or_404(db: Session, session_id: int) -> LearningSession:
    session = db.get(LearningSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="自学会话不存在")
    return session


def _own_or_403(session: LearningSession, user: User) -> None:
    if session.student_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该会话")


def _enrolled_or_403(db: Session, user: User, course_id: int) -> None:
    if user.role == "teacher":
        course = db.get(Course, course_id)
        if course and course.teacher_id == user.id:
            return
    if user.id in CourseRepository.student_ids(db, course_id):
        return
    raise HTTPException(status_code=403, detail="未选课，无法发起自学")


@router.post("/create")
def create_session(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    course_id = int(data.get("course_id", 0))
    if not db.get(Course, course_id):
        raise HTTPException(status_code=404, detail="课程不存在")
    _enrolled_or_403(db, user, course_id)
    try:
        session = LearningSessionService.generate_session(
            db,
            user,
            course_id=course_id,
            chapter_id=int(data["chapter_id"]) if data.get("chapter_id") else None,
            knowledge_point_id=int(data["knowledge_point_id"]) if data.get("knowledge_point_id") else None,
            depth=str(data.get("depth", "standard")),
            mode=str(data.get("mode", "learn")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LearningSessionService.serialize(db, session)


@router.get("/list")
def list_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    sessions = LearningSessionService.list_sessions(db, user, limit=30)
    return [LearningSessionService.serialize(db, s) for s in sessions]


@router.get("/teacher")
def teacher_sessions(
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> list[dict]:
    """教师查看所授课程下学生的自学会话（卡在哪一步、对错情况）。"""
    course_ids = [c.id for c in db.query(Course).filter(Course.teacher_id == user.id).all()]
    if not course_ids:
        return []
    sessions = (
        db.query(LearningSession)
        .filter(LearningSession.course_id.in_(course_ids))
        .order_by(LearningSession.updated_at.desc())
        .limit(100)
        .all()
    )
    out = []
    for s in sessions:
        item = LearningSessionService.serialize(db, s)
        student = db.get(User, s.student_id)
        item["student_id"] = s.student_id
        item["student_name"] = student.display_name if student else ""
        out.append(item)
    return out


@router.get("/{session_id}")
def get_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session = _session_or_404(db, session_id)
    _own_or_403(session, user)
    return LearningSessionService.serialize(db, session)


@router.post("/{session_id}/steps/{step_index}/action")
def record_step_action(
    session_id: int,
    step_index: int,
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session = _session_or_404(db, session_id)
    _own_or_403(session, user)
    try:
        return LearningSessionService.record_step_action(
            db, user, session, step_index, data
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{session_id}/complete")
def complete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session = _session_or_404(db, session_id)
    _own_or_403(session, user)
    try:
        return LearningSessionService.complete(db, user, session)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
