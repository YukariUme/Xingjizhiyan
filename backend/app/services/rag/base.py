"""RAGService 统一接口。

后续接入真实 Embedding + Vector DB 时，实现同一接口即可替换。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy.orm import Session


@dataclass
class RetrievedChunk:
    """一条检索结果：内容 + 来源元数据 + 相似度。"""

    chunk_id: int
    text: str
    document_title: str
    document_source: str
    course: str
    chapter: str
    topic: str
    score: float = 0.0
    metadata: dict = field(default_factory=dict)


class RAGService(ABC):
    """检索增强生成服务统一接口。"""

    name: str = "base"

    @abstractmethod
    def chunk_document(self, text: str, chunk_size: int = 400, overlap: int = 60) -> list[str]:
        """文档切分：按段落聚合为带重叠的文本块。"""
        raise NotImplementedError

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """文本向量化（Mock 实现为确定性哈希向量）。"""
        raise NotImplementedError

    @abstractmethod
    def ingest_document(self, db: Session, document_id: int) -> int:
        """将知识文档切分、向量化并入库，返回切片数量。"""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
        course: str | None = None,
        document_ids: list[int] | None = None,
    ) -> list[RetrievedChunk]:
        """语义/关键词检索，返回排序后的切片。"""
        raise NotImplementedError

    @abstractmethod
    def rerank(self, results: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """重排：结合元数据匹配度调整顺序。"""
        raise NotImplementedError

    @abstractmethod
    def generate_answer(self, db: Session, query: str, top_k: int = 5) -> dict:
        """检索 + 生成：返回 {answer, references}，references 供界面展示引用来源。"""
        raise NotImplementedError

    @abstractmethod
    def retrieve_context(self, db: Session, query: str, top_k: int = 5, **filters) -> dict:
        """只检索不生成：返回 {context, references, grounded, confidence, note}。"""
        raise NotImplementedError
