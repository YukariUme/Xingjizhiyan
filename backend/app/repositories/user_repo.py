"""用户数据访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    @staticmethod
    def get_by_username(db: Session, username: str) -> User | None:
        return db.scalar(select(User).where(User.username == username))

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        return db.get(User, user_id)

    @staticmethod
    def list_by_role(db: Session, role: str) -> list[User]:
        return list(db.scalars(select(User).where(User.role == role).order_by(User.id)))

