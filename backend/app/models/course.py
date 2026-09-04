"""课程、选课与备课计划实体。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    semester: Mapped[str] = mapped_column(String(32), default="2026 春季")
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("course_id", "student_id", name="uq_enroll"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    course: Mapped[Course] = relationship(back_populates="enrollments")


class LessonPlan(Base):
    """教师智能备课生成的教案。"""

    __tablename__ = "lesson_plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course: Mapped[str] = mapped_column(String(128))
    chapter: Mapped[str] = mapped_column(String(128))
    topic: Mapped[str] = mapped_column(String(128))
    grade: Mapped[str] = mapped_column(String(64), default="")
    objectives: Mapped[str] = mapped_column(Text, default="")
    knowledge_points: Mapped[list] = mapped_column(JSON, default=list)
    key_points: Mapped[list] = mapped_column(JSON, default=list)
    difficulties: Mapped[list] = mapped_column(JSON, default=list)
    flow: Mapped[list] = mapped_column(JSON, default=list)
    cases: Mapped[list] = mapped_column(JSON, default=list)
    exercises: Mapped[list] = mapped_column(JSON, default=list)
    homework: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class GradeBand(Base):
    """预留：成绩区间配置（当前未使用）。"""

    __tablename__ = "grade_bands"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32))
    min_score: Mapped[float] = mapped_column(Float, default=0)
    max_score: Mapped[float] = mapped_column(Float, default=100)


class CourseInvitation(Base):
    """课程邀请：教师发出 → 学生接受后才成为正式选课。"""

    __tablename__ = "course_invitations"
    __table_args__ = (
        UniqueConstraint("course_id", "student_id", name="uq_course_invitation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | accepted | declined | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
