"""RAG 工厂。"""

import logging

from app.config import get_settings
from app.services.rag.base import RAGService

logger = logging.getLogger(__name__)


def get_rag_service() -> RAGService:
    """返回检索 RAG。

    RAG_PROVIDER:
      - auto / postgres : 数据库为 PostgreSQL 时用 PostgresRAGService（pgvector），
                          否则回退 SQLiteRAGService（本地混合检索）
      - local / mock    : 强制使用本地混合检索（测试与离线演示）
      - sqlite          : 同 local

    LLM 按需惰性创建，避免 AI 未配置时拖垮知识库模块。
    """
    provider = get_settings().rag_provider.lower()
    if provider in {"local", "mock", "sqlite"}:
        from app.services.rag.sqlite import SQLiteRAGService

        return SQLiteRAGService()
    db_url = get_settings().database_url.lower()
    if db_url.startswith("postgresql"):
        from app.services.rag.postgres import PostgresRAGService

        return PostgresRAGService()
    from app.services.rag.sqlite import SQLiteRAGService

    return SQLiteRAGService()
