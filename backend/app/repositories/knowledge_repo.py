"""知识库数据访问。"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import KnowledgeChunk, KnowledgeDocument, KnowledgePoint


class KnowledgeRepository:
    @staticmethod
    def list_points(db: Session, subject: str | None = None) -> list[KnowledgePoint]:
        q = select(KnowledgePoint)
        if subject:
            q = q.where(KnowledgePoint.subject == subject)
        return list(db.scalars(q.order_by(KnowledgePoint.id)))

    @staticmethod
    def get_point(db: Session, point_id: int) -> KnowledgePoint | None:
        return db.get(KnowledgePoint, point_id)

    @staticmethod
    def get_points_by_ids(db: Session, ids: list[int]) -> list[KnowledgePoint]:
        if not ids:
            return []
        return list(db.scalars(select(KnowledgePoint).where(KnowledgePoint.id.in_(ids))))

    @staticmethod
    def list_documents(db: Session, course: str | None = None) -> list[KnowledgeDocument]:
        q = select(KnowledgeDocument)
        if course:
            q = q.where(KnowledgeDocument.course == course)
        return list(db.scalars(q.order_by(KnowledgeDocument.id)))

    @staticmethod
    def get_document(db: Session, doc_id: int) -> KnowledgeDocument | None:
        return db.get(KnowledgeDocument, doc_id)

    @staticmethod
    def count_chunks(db: Session) -> int:
        return db.scalar(select(func.count(KnowledgeChunk.id))) or 0

    @staticmethod
    def all_chunks(db: Session) -> list[KnowledgeChunk]:
        return list(db.scalars(select(KnowledgeChunk).order_by(KnowledgeChunk.id)))

    @staticmethod
    def save_chunks(db: Session, chunks: list[KnowledgeChunk]) -> None:
        """批量写入切片（executemany，大文档入库显著提速）。"""
        if not chunks:
            return
        from sqlalchemy import insert

        rows = [
            {
                "document_id": c.document_id,
                "chunk_index": c.chunk_index,
                "text": c.text,
                "embedding": c.embedding,
                "metadata_json": c.metadata_json,
            }
            for c in chunks
        ]
        db.execute(insert(KnowledgeChunk), rows)
        db.commit()

    @staticmethod
    def search_by_keywords(db: Session, keywords: list[str], limit: int = 5) -> list[KnowledgeChunk]:
        """基于关键词的简单检索（Mock RAG 的底层实现）。"""
        if not keywords:
            return []
        q = select(KnowledgeChunk)
        conds = [
            KnowledgeChunk.text.ilike(f"%{kw}%")
            for kw in keywords
            if len(kw.strip()) > 1
        ]
        if not conds:
            return []
        return list(db.scalars(q.where(or_(*conds)).limit(limit)))
