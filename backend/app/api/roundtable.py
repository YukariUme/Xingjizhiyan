"""AI 圆桌讨论路由：开始 / 学生加入并回应 / 实时总结。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.services.roundtable_service import RoundtableService

router = APIRouter(prefix="/api/roundtable", tags=["roundtable"])


@router.post("/start")
def start_roundtable(
    data: dict,
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    course_id = int(data["course_id"]) if data.get("course_id") else None
    return RoundtableService.start(db, str(data.get("topic", "")), course_id)


@router.post("/reply")
def reply_roundtable(
    data: dict,
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    course_id = int(data["course_id"]) if data.get("course_id") else None
    return RoundtableService.reply(
        db,
        str(data.get("topic", "")),
        data.get("turns") or [],
        str(data.get("student_message", "")),
        course_id,
    )


@router.post("/summary")
def summarize_roundtable(
    data: dict,
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    course_id = int(data["course_id"]) if data.get("course_id") else None
    return RoundtableService.summarize(
        db,
        str(data.get("topic", "")),
        data.get("turns") or [],
        course_id,
    )
