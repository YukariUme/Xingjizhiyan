"""PostgreSQL 切换冒烟测试：建表、种子、向量列、RAG 入库与检索。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal, engine, init_db  # noqa: E402
from app.seed import seed_if_empty  # noqa: E402


def main() -> None:
    print("db url:", get_settings().database_url)
    init_db()
    db = SessionLocal()
    try:
        seed_if_empty(db)
        print("seed ok")
    finally:
        db.close()

    with engine.connect() as conn:
        users = conn.execute(text("SELECT count(*) FROM users")).scalar()
        docs = conn.execute(text("SELECT count(*) FROM knowledge_documents")).scalar()
        cols = [
            r[0]
            for r in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'knowledge_chunks' ORDER BY ordinal_position"
                )
            )
        ]
        has_vec = conn.execute(text("SELECT to_regtype('vector') IS NOT NULL")).scalar()
        print("users:", users, "| docs:", docs)
        print("chunk cols:", cols)
        print("vector type:", has_vec)

    # RAG 入库 + 检索冒烟
    from app.models import KnowledgeDocument
    from app.services.rag.factory import get_rag_service

    rag = get_rag_service()
    print("rag service:", rag.name)
    with SessionLocal() as db:
        doc = (
            db.query(KnowledgeDocument)
            .filter(KnowledgeDocument.course == "操作系统")
            .first()
        )
        if doc:
            n = rag.ingest_document(db, doc.id)
            print("ingest chunks:", n)
            results = rag.search(db, "进程同步 信号量", top_k=3, course="操作系统")
            print("search hits:", len(results))
            for r in results:
                print("  -", r.score, r.document_title, r.text[:60].replace("\n", " "))
            with engine.connect() as conn:
                vec_count = conn.execute(
                    text(
                        "SELECT count(*) FROM knowledge_chunks "
                        "WHERE embedding_vector IS NOT NULL"
                    )
                ).scalar()
                print("pgvector rows:", vec_count)


if __name__ == "__main__":
    main()
