"""作业与题目实体。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status: Mapped[str] = mapped_column(String(16), default="published")  # draft | published
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    questions: Mapped[list["Question"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan", order_by="Question.id"
    )


class Question(Base):
    """题目：programming | subjective | report。"""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"), index=True)
    qtype: Mapped[str] = mapped_column(String(24), index=True)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(16), default="python")
    code_template: Mapped[str] = mapped_column(Text, default="")
    test_cases: Mapped[list] = mapped_column(JSON, default=list)
    max_score: Mapped[float] = mapped_column(Float, default=10.0)
    knowledge_point_ids: Mapped[list] = mapped_column(JSON, default=list)

    assignment: Mapped[Assignment] = relationship(back_populates="questions")

