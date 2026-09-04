"""科研模块实体。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utcnow


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512))
    authors: Mapped[list] = mapped_column(JSON, default=list)
    abstract: Mapped[str] = mapped_column(Text, default="")
    venue: Mapped[str] = mapped_column(String(128), default="")
    year: Mapped[int] = mapped_column(Integer, default=2026)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    citations: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, default="")
    knowledge_point_ids: Mapped[list] = mapped_column(JSON, default=list)
    url: Mapped[str] = mapped_column(String(512), default="")
    is_hot: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ResearchTopic(Base):
    """用户私人研究方向。"""

    __tablename__ = "research_topics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PaperReading(Base):
    """阅读记录与收藏（默认用户私有）。"""

    __tablename__ = "paper_readings"
    __table_args__ = (UniqueConstraint("user_id", "paper_id", name="uq_paper_reading"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="reading")  # reading | read | favorite
    progress: Mapped[int] = mapped_column(Integer, default=0)
    last_read_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

