"""课程章节、知识空间、测验、学习任务/计划/记录、科研资料等实体（Phase 2 新增）。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utcnow


class CourseChapter(Base):
    """课程章节（按官方教材结构维护，支撑预习/复习/模拟的范围）。"""

    __tablename__ = "course_chapters"
    __table_args__ = (UniqueConstraint("course_id", "order", name="uq_chapter_order"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    order: Mapped[int] = mapped_column(Integer, default=1)
    key: Mapped[str] = mapped_column(String(32), default="")  # ch1, ch2...
    title: Mapped[str] = mapped_column(String(256))
    official_ref: Mapped[str] = mapped_column(String(256), default="")  # 教材章节映射
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CourseKnowledgeSpace(Base):
    """每门课程的独立知识空间配置。"""

    __tablename__ = "course_knowledge_spaces"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    default_scope: Mapped[str] = mapped_column(String(16), default="official")  # official | shared | personal
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class KnowledgeReview(Base):
    """学生共享资料审核（申请 → 教师通过/驳回/仅自己）。"""

    __tablename__ = "knowledge_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | approved | rejected | private
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Quiz(Base):
    """测验（章节测验 / 模拟考试 / 薄弱专项 / 错题重测 / 自定义）。"""

    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("course_chapters.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(256))
    quiz_type: Mapped[str] = mapped_column(String(24), default="chapter")  # chapter | mock_exam | weakness | wrong_retest | custom
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(16), default="published")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), index=True)
    qtype: Mapped[str] = mapped_column(String(24))  # single | multiple | judge | short | algorithm | code | sql | analysis
    title: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON, default=list)
    answer: Mapped[dict] = mapped_column(JSON, default=dict)
    analysis: Mapped[str] = mapped_column(Text, default="")
    knowledge_point_ids: Mapped[list] = mapped_column(JSON, default=list)
    max_score: Mapped[float] = mapped_column(Float, default=5.0)
    order: Mapped[int] = mapped_column(Integer, default=1)


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    max_score: Mapped[float] = mapped_column(Float, default=0)
    answers: Mapped[list] = mapped_column(JSON, default=list)
    details: Mapped[dict] = mapped_column(JSON, default=dict)  # 每题对错 + 知识点
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LearningTask(Base):
    """今日/近期学习任务（可解释：携带 reason 与证据）。"""

    __tablename__ = "learning_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_points.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(256))
    reason: Mapped[str] = mapped_column(Text, default="")
    task_type: Mapped[str] = mapped_column(String(24), default="study")
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="todo")  # todo | done | overdue
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[list] = mapped_column(JSON, default=list)  # 步骤列表
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class LearningRecord(Base):
    """学习行为记录（预习/讲堂/复习/测验/作业/答疑/资料）。"""

    __tablename__ = "learning_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("course_chapters.id"), nullable=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_points.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(24))  # preview | lecture | review | quiz | homework | exam | qa | material
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ResearchDocument(Base):
    """科研资料（论文等，默认私有）。"""

    __tablename__ = "research_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    paper_id: Mapped[int | None] = mapped_column(ForeignKey("papers.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    file_path: Mapped[str] = mapped_column(String(1024), default="")
    source: Mapped[str] = mapped_column(String(256), default="")
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), default="private")  # private | shared
    status: Mapped[str] = mapped_column(String(16), default="ok")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserResearchProfile(Base):
    __tablename__ = "user_research_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String(16), default="beginner")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

