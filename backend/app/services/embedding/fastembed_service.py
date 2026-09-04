"""FastEmbed 真实 Embedding 服务。

使用 ONNX 本地推理（fastembed），默认模型 BAAI/bge-small-zh-v1.5：
- 512 维稠密向量，中文/英文混合检索效果好、体积小（~100MB 模型）；
- 首次加载会从 HuggingFace 下载模型，之后本地缓存；
- 模型下载/加载失败时由工厂回退到 HashEmbeddingService，保证离线可用。
"""

import logging
from typing import Any

from app.services.embedding.base import EmbeddingService

logger = logging.getLogger(__name__)


class FastEmbeddingService(EmbeddingService):
    """基于 fastembed 的本地真实 Embedding（惰性加载模型）。"""

    name = "fastembed"

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5") -> None:
        self.model_name = model_name
        self._model: Any | None = None
        self._dim = 0

    @property
    def dimension(self) -> int:
        """向量维度：未加载模型时为 0。"""
        return self._dim

    def _ensure_model(self) -> Any:
        """惰性加载 fastembed 模型（线程安全由 fastembed 内部保证）。"""
        if self._model is None:
            from fastembed import TextEmbedding

            logger.info("正在加载本地 Embedding 模型：%s ...", self.model_name)
            self._model = TextEmbedding(model_name=self.model_name)
            # 通过一次嵌入探测维度
            probe = list(self._model.embed(["探"]))[0]
            self._dim = len(probe)
            logger.info("Embedding 模型加载完成，维度=%d", self._dim)
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """单条文本向量化，返回归一化浮点列表。"""
        model = self._ensure_model()
        vec = next(iter(model.embed([text or " "])), None)
        if vec is None:
            return []
        return [round(float(v), 6) for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量向量化（分块执行，避免一次性提交过多文本）。"""
        if not texts:
            return []
        model = self._ensure_model()
        results: list[list[float]] = []
        batch = 256
        for start in range(0, len(texts), batch):
            part = texts[start : start + batch]
            for vec in model.embed(part):
                results.append([round(float(v), 6) for v in vec])
        self._dim = len(results[0]) if results else self._dim
        return results
