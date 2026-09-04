"""提交、评测与批改实体。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow


class Submission(Base):
    """一次作业提交。qtype: programming | subjective | report。"""

    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("question_id", "student_id", name="uq_submission"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    qtype: Mapped[str] = mapped_column(String(24), index=True)
    status: Mapped[str] = mapped_column(String(24), default="submitted")  # submitted | under_review | graded
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    code: Mapped["CodeSubmission | None"] = relationship(
        back_populates="submission", cascade="all, delete-orphan", uselist=False
    )
    subjective: Mapped["SubjectiveSubmission | None"] = relationship(
        back_populates="submission", cascade="all, delete-orphan", uselist=False
    )


class CodeSubmission(Base):
    __tablename__ = "code_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), unique=True, index=True
    )
    source_code: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(16), default="python")
    verdict: Mapped[str] = mapped_column(String(32), default="pending")
    passed_tests: Mapped[int] = mapped_column(default=0)
    total_tests: Mapped[int] = mapped_column(default=0)
    runtime_ms: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    judge_report: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    submission: Mapped[Submission] = relationship(back_populates="code")


class SubjectiveSubmission(Base):
    """简答题 / 实验报告提交 + AI 建议批改 + 教师确认。"""

    __tablename__ = "subjective_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), unique=True, index=True
    )
    content: Mapped[str] = mapped_column(Text, default="")
    ai_suggestion_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_reasoning: Mapped[str] = mapped_column(Text, default="")
    ai_knowledge_points: Mapped[list] = mapped_column(JSON, default=list)
    ai_error_analysis: Mapped[str] = mapped_column(Text, default="")
    ai_improvement: Mapped[str] = mapped_column(Text, default="")
    teacher_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    teacher_comment: Mapped[str] = mapped_column(Text, default="")
    graded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    submission: Mapped[Submission] = relationship(back_populates="subjective")


class Evaluation(Base):
    """评分记录（AI 建议分 / 教师最终分）。"""

    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True)
    source: Mapped[str] = mapped_column(String(16))  # ai | teacher
    score: Mapped[float] = mapped_column(Float, default=0)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Feedback(Base):
    """批改反馈 / 学生疑问。"""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True)
    author_role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

