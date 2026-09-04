"""最近活动路由。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("")
def recent_activities(
    role: str | None = None,
    limit: int = 12,
    db: Session = Depends(get_db),
) -> list[dict]:
    """最近活动（公开，供首页展示）。"""
    activities = ActivityService.recent(db, role=role, limit=limit)
    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "role": a.role,
            "kind": a.kind,
            "title": a.title,
            "detail": a.detail,
            "created_at": a.created_at.isoformat(),
        }
        for a in activities
    ]
