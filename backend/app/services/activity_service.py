"""活动日志服务。"""

from sqlalchemy.orm import Session

from app.models import Activity, User
from app.repositories.activity_repo import ActivityRepository


class ActivityService:
    @staticmethod
    def log(db: Session, user: User, kind: str, title: str, detail: dict | None = None) -> Activity:
        return ActivityRepository.add(
            db,
            Activity(
                user_id=user.id,
                role=user.role,
                kind=kind,
                title=title,
                detail=detail or {},
            ),
        )

    @staticmethod
    def recent(db: Session, role: str | None = None, user_id: int | None = None, limit: int = 12) -> list[Activity]:
        if user_id is not None:
            return ActivityRepository.recent_for_user(db, user_id, limit)
        if role:
            return ActivityRepository.recent_for_role(db, role, limit)
        return ActivityRepository.recent(db, limit)

