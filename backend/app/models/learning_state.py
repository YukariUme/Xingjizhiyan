"""学习状态、教师干预与前后对比数据。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utcnow


class StudentLearningState(Base):
    """统一学习状态：把画像、行为、答疑、测验和作业信号收敛到一个状态机。"""

    __tablename__ = "student_learning_states"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "course_id",
            "knowledge_point_id",
            name="uq_student_learning_state",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    knowledge_point_id: Mapped[int] = mapped_column(ForeignKey("knowledge_points.id"), index=True)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    recent_error_count: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_error_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    last_learning_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_assessment_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recent_question_count: Mapped[int] = mapped_column(Integer, default=0)
    learning_stability: Mapped[float] = mapped_column(Float, default=0.0)
    state: Mapped[str] = mapped_column(String(32), default="WEAK")
    state_reason: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class TeacherSuggestionDecision(Base):
    """教师对 AI 建议的采纳 / 修改 / 忽略记录。"""

    __tablename__ = "teacher_suggestion_decisions"

    id: Mapped[str] = mapped_column(String(48), primary_key=True, default=lambda: uuid4().hex[:16])
    suggestion_id: Mapped[str] = mapped_column(String(64), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True, index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(16))  # ACCEPT | EDIT | REJECT
    original_suggestion: Mapped[str] = mapped_column(Text, default="")
    modified_content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LearningProgressComparison(Base):
    """学习前后对比快照。"""

    __tablename__ = "learning_progress_comparisons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True, index=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True, index=True)
    before_mastery: Mapped[float] = mapped_column(Float, default=0.0)
    after_mastery: Mapped[float] = mapped_column(Float, default=0.0)
    before_state: Mapped[str] = mapped_column(String(32), default="")
    after_state: Mapped[str] = mapped_column(String(32), default="")
    interventions: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
