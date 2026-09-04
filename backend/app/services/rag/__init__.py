"""RAG 抽象层：接口 + SQLite 本地检索实现 + 工厂。"""

from app.services.rag.base import RAGService
from app.services.rag.factory import get_rag_service

__all__ = ["RAGService", "get_rag_service"]

