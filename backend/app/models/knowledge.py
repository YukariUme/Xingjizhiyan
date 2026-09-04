"""计算机学科知识库实体。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utcnow


class KnowledgePoint(Base):
    """知识点（跨课程、章节组织，是学情分析的最小单元）。"""

    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    subject: Mapped[str] = mapped_column(String(64), index=True)
    chapter: Mapped[str] = mapped_column(String(128), default="")
    difficulty: Mapped[str] = mapped_column(String(16), default="中")  # 易 | 中 | 难
    description: Mapped[str] = mapped_column(Text, default="")
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)
    related_points: Mapped[list] = mapped_column(JSON, default=list)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    sub_points: Mapped[list] = mapped_column(JSON, default=list)  # 二级知识点 [{name,description,difficulty}]
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("course_chapters.id"), nullable=True)


class KnowledgeDocument(Base):
    """知识库文档（教材讲义、课件、规范等），带统一 metadata。"""

    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(128), default="")
    course: Mapped[str] = mapped_column(String(128), index=True)
    topic: Mapped[str] = mapped_column(String(128), index=True)
    chapter: Mapped[str] = mapped_column(String(128), default="")
    difficulty: Mapped[str] = mapped_column(String(16), default="中")
    type: Mapped[str] = mapped_column(String(32), default="讲义")  # 讲义 | 教材 | 论文 | 实验
    year: Mapped[int] = mapped_column(Integer, default=2026)
    content: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True, index=True)
    source_level: Mapped[str] = mapped_column(String(8), default="S")  # S 官方 | A 审核共享 | P 个人
    visibility: Mapped[str] = mapped_column(String(16), default="official")  # official | shared | private
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    page: Mapped[str] = mapped_column(String(64), default="")
    document_type: Mapped[str] = mapped_column(String(32), default="讲义")
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rag_hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class KnowledgeChunk(Base):
    """知识文档切片，本地检索的最小单位。"""

    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True, index=True)
    source_level: Mapped[str] = mapped_column(String(8), default="S")
    visibility: Mapped[str] = mapped_column(String(16), default="official")


class KnowledgeJob(Base):
    """知识库后台任务（上传 / 批量导入），异步处理并回报进度。"""

    __tablename__ = "knowledge_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="upload")  # upload | import
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    filename: Mapped[str] = mapped_column(String(512), default="")
    course: Mapped[str] = mapped_column(String(128), default="")
    file_path: Mapped[str] = mapped_column(String(1024), default="")
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    message: Mapped[str] = mapped_column(String(512), default="")
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
