"""EmbeddingService 统一接口。未来可替换为 BGE-M3 / Qwen Embedding 等真实服务。"""

import hashlib
import math
import re
from abc import ABC, abstractmethod


class EmbeddingService(ABC):
    name: str = "base"

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class HashEmbeddingService(EmbeddingService):
    """确定性哈希向量（128 维），仅用于演示；替换真实 Embedding 时保持接口不变。"""

    name = "hash"

    def embed_text(self, text: str) -> list[float]:
        tokens = re.findall(r"[a-z0-9_]{2,}", text.lower()) + re.findall(
            r"[\u4e00-\u9fff]", text
        )
        dim = 128
        vec = [0.0] * dim
        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16)
            vec[h % dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [round(v / norm, 6) for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]
