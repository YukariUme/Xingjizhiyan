"""活动数据访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Activity


class ActivityRepository:
    @staticmethod
    def add(db: Session, activity: Activity) -> Activity:
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return activity

    @staticmethod
    def recent(db: Session, limit: int = 12) -> list[Activity]:
        return list(
            db.scalars(select(Activity).order_by(Activity.created_at.desc()).limit(limit))
        )

    @staticmethod
    def recent_for_role(db: Session, role: str, limit: int = 12) -> list[Activity]:
        return list(
            db.scalars(
                select(Activity)
                .where(Activity.role == role)
                .order_by(Activity.created_at.desc())
                .limit(limit)
            )
        )

    @staticmethod
    def recent_for_user(db: Session, user_id: int, limit: int = 12) -> list[Activity]:
        return list(
            db.scalars(
                select(Activity)
                .where(Activity.user_id == user_id)
                .order_by(Activity.created_at.desc())
                .limit(limit)
            )
        )

