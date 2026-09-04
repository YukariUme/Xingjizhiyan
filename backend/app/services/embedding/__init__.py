"""Embedding 抽象层：接口 + 工厂（hash / fastembed / auto）。"""

from app.config import get_settings
from app.services.embedding.base import EmbeddingService, HashEmbeddingService
from app.services.embedding.fastembed_service import FastEmbeddingService


def get_embedding_service() -> EmbeddingService:
    """按配置创建 Embedding 服务。

    EMBEDDING_PROVIDER:
      - hash      : 确定性哈希向量（离线演示，无模型依赖）
      - fastembed : 本地 ONNX 真实 Embedding（BAAI/bge-small-zh-v1.5）
      - auto      : 返回 fastembed（惰性加载）；模型不可用时由 RAG 服务回退 hash

    模型加载是惰性的：首次真正向量化时才会下载/加载，避免阻塞请求。
    """
    provider = get_settings().embedding_provider.lower()
    if provider == "hash":
        return HashEmbeddingService()
    if provider == "fastembed":
        return FastEmbeddingService()
    return FastEmbeddingService()


__all__ = ["EmbeddingService", "HashEmbeddingService", "FastEmbeddingService", "get_embedding_service"]

__all__ = ["EmbeddingService", "HashEmbeddingService"]
