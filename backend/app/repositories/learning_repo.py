"""学习画像与推荐数据访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChatMessage, LearningRecommendation, StudentKnowledgeProfile


class LearningRepository:
    @staticmethod
    def get_profile(db: Session, student_id: int, kp_id: int) -> StudentKnowledgeProfile | None:
        return db.scalar(
            select(StudentKnowledgeProfile).where(
                StudentKnowledgeProfile.student_id == student_id,
                StudentKnowledgeProfile.knowledge_point_id == kp_id,
            )
        )

    @staticmethod
    def list_profiles(db: Session, student_id: int) -> list[StudentKnowledgeProfile]:
        return list(
            db.scalars(
                select(StudentKnowledgeProfile)
                .where(StudentKnowledgeProfile.student_id == student_id)
                .order_by(StudentKnowledgeProfile.mastery)
            )
        )

    @staticmethod
    def save_profile(db: Session, profile: StudentKnowledgeProfile) -> None:
        db.add(profile)
        db.commit()

    @staticmethod
    def list_recommendations(db: Session, student_id: int) -> list[LearningRecommendation]:
        return list(
            db.scalars(
                select(LearningRecommendation)
                .where(LearningRecommendation.student_id == student_id)
                .order_by(LearningRecommendation.priority.desc())
            )
        )

    @staticmethod
    def replace_recommendations(db: Session, items: list[LearningRecommendation]) -> None:
        student_ids = {it.student_id for it in items}
        for sid in student_ids:
            old = db.scalars(
                select(LearningRecommendation).where(
                    LearningRecommendation.student_id == sid
                )
            )
            for row in old:
                db.delete(row)
        db.add_all(items)
        db.commit()

    @staticmethod
    def add_message(db: Session, message: ChatMessage) -> ChatMessage:
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def list_messages(db: Session, user_id: int, agent_type: str, limit: int = 50) -> list[ChatMessage]:
        return list(
            db.scalars(
                select(ChatMessage)
                .where(ChatMessage.user_id == user_id, ChatMessage.agent_type == agent_type)
                .order_by(ChatMessage.id.desc())
                .limit(limit)
            )
        )

