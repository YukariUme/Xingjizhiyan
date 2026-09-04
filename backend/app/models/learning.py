"""学习画像、推荐与对话历史实体。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utcnow


class StudentKnowledgeProfile(Base):
    """学生知识点掌握画像（mastery 0-100）。"""

    __tablename__ = "student_knowledge_profiles"
    __table_args__ = (
        UniqueConstraint("student_id", "knowledge_point_id", name="uq_student_kp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    knowledge_point_id: Mapped[int] = mapped_column(ForeignKey("knowledge_points.id"), index=True)
    mastery: Mapped[float] = mapped_column(default=0.0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(default=0.0)
    evidence_type: Mapped[str] = mapped_column(String(24), default="homework")
    last_assessed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LearningRecommendation(Base):
    """个性化学习推荐。"""

    __tablename__ = "learning_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_points.id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, default="")
    resource_title: Mapped[str] = mapped_column(String(256))
    resource_type: Mapped[str] = mapped_column(String(24))  # chapter | exercise | experiment | paper | next
    resource_ref: Mapped[dict] = mapped_column(JSON, default=dict)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ChatMessage(Base):
    """AI 对话历史（按 Agent 类型区分业务）。"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    agent_type: Mapped[str] = mapped_column(String(32), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text, default="")
    knowledge_points: Mapped[list] = mapped_column(JSON, default=list)
    references: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
