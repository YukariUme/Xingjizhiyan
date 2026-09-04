"""科研模块数据访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Paper, PaperReading, ResearchTopic, User


class ResearchRepository:
    @staticmethod
    def list_papers(db: Session, limit: int = 100) -> list[Paper]:
        return list(db.scalars(select(Paper).order_by(Paper.year.desc()).limit(limit)))

    @staticmethod
    def get_paper(db: Session, paper_id: int) -> Paper | None:
        return db.get(Paper, paper_id)

    @staticmethod
    def search_papers(db: Session, keyword: str, limit: int = 20) -> list[Paper]:
        kw = keyword.strip()
        if not kw:
            return []
        papers = []
        for p in db.scalars(select(Paper).limit(500)):
            haystack = " ".join(
                [p.title, p.abstract, p.venue, " ".join(p.topics), " ".join(p.keywords)]
            ).lower()
            if kw.lower() in haystack:
                papers.append(p)
        return papers[:limit]

    @staticmethod
    def get_reading(db: Session, user_id: int, paper_id: int) -> PaperReading | None:
        return db.scalar(
            select(PaperReading).where(
                PaperReading.user_id == user_id, PaperReading.paper_id == paper_id
            )
        )

    @staticmethod
    def list_readings(db: Session, user_id: int) -> list[PaperReading]:
        return list(
            db.scalars(
                select(PaperReading)
                .where(PaperReading.user_id == user_id)
                .order_by(PaperReading.last_read_at.desc())
            )
        )

    @staticmethod
    def save_reading(db: Session, reading: PaperReading) -> PaperReading:
        db.add(reading)
        db.commit()
        db.refresh(reading)
        return reading

    @staticmethod
    def list_topics(db: Session, owner_id: int) -> list[ResearchTopic]:
        return list(
            db.scalars(
                select(ResearchTopic)
                .where(ResearchTopic.owner_id == owner_id)
                .order_by(ResearchTopic.id)
            )
        )

    @staticmethod
    def create_topic(db: Session, topic: ResearchTopic) -> ResearchTopic:
        db.add(topic)
        db.commit()
        db.refresh(topic)
        return topic

    @staticmethod
    def author_name(db: Session, user_id: int) -> str:
        u = db.get(User, user_id)
        return u.display_name if u else ""

