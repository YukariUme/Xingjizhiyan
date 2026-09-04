"""SQLiteRAGService 单元测试。"""

from app.database import SessionLocal
from app.services.embedding import get_embedding_service
from app.services.embedding.base import EmbeddingService
from app.services.rag.sqlite import SQLiteRAGService


class _FakeSemanticEmbedder(EmbeddingService):
    """假语义 Embedding：含“二叉树”文本映射到 [1,0]，其他映射到 [0,1]。"""

    name = "fake-semantic"

    def embed_text(self, text: str) -> list[float]:
        if "二叉树" in text or "binary tree" in text.lower():
            return [1.0, 0.0]
        return [0.0, 1.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


def test_chunk_document_with_overlap():
    rag = SQLiteRAGService()
    text = "\n\n".join(f"第 {i} 段：这是用于测试切分的演示内容，包含若干知识点描述。" for i in range(20))
    chunks = rag.chunk_document(text, chunk_size=100, overlap=20)
    assert len(chunks) >= 5
    assert all(c.strip() for c in chunks)


def test_embed_is_deterministic():
    rag = SQLiteRAGService()
    a = rag.embed("二叉树前序遍历")
    b = rag.embed("二叉树前序遍历")
    assert a == b
    assert len(a) == 128


def test_search_returns_relevant_chunk():
    rag = SQLiteRAGService()
    db = SessionLocal()
    try:
        results = rag.search(db, "二叉树前序遍历 递归", top_k=3)
        assert results
        assert results[0].score > 0
        assert any("二叉" in r.text for r in results)
    finally:
        db.close()


def test_generate_answer_has_references():
    rag = SQLiteRAGService()
    db = SessionLocal()
    try:
        out = rag.generate_answer(db, "什么是动态规划", top_k=3)
        assert out["answer"]
        assert isinstance(out["references"], list)
        assert out["grounded"] is True
        assert out["references"][0]["title"]
    finally:
        db.close()


def test_search_rejects_generic_only_queries():
    """跨语言检索与可信门控：中文术语可命中英文教材；纯通用词提问不误判。"""
    rag = SQLiteRAGService()
    db = SessionLocal()
    try:
        # 中文“婚姻匹配”应命中英文教材（跨语言扩展）
        hits = rag.search(db, "婚姻匹配问题", top_k=3)
        assert hits
        assert "Stable Matching" in hits[0].document_title
        # 中文“算法设计”通过课程名元数据命中英文教材
        hits_course = rag.search(db, "算法设计", top_k=3)
        assert hits_course and hits_course[0].document_title
        # 纯通用词/无关提问不误判
        hits_generic = rag.search(db, "附近有什么好吃的川菜馆", top_k=3)
        assert hits_generic == []
        hits2 = rag.search(db, "二叉树的先序遍历怎么写", top_k=3)
        assert hits2 and "二叉树" in hits2[0].document_title
        # 主题名完整出现在问题中时允许命中（“栈和队列的区别”）
        hits3 = rag.search(db, "栈和队列的区别是什么", top_k=3)
        assert hits3 and hits3[0].topic == "栈和队列"
    finally:
        db.close()


def test_generate_answer_cross_language():
    """中文提问命中英文教材时给出引用（grounded=True）。"""
    rag = SQLiteRAGService()
    db = SessionLocal()
    try:
        out = rag.generate_answer(db, "婚姻匹配问题", top_k=3)
        assert out["grounded"] is True
        assert out["references"]
        assert out["confidence"] > 0
    finally:
        db.close()


def test_embedding_factory_hash_mode():
    """测试环境固定 hash：工厂返回确定性哈希 Embedding。"""
    service = get_embedding_service()
    assert service.name == "hash"
    a = service.embed_text("二叉树前序遍历")
    b = service.embed_text("二叉树前序遍历")
    assert a == b


def test_hybrid_search_uses_semantic_score():
    """混合检索：语义向量主导排序，命中“二叉树”相关切片。"""
    rag = SQLiteRAGService(
        embedder=_FakeSemanticEmbedder(),
        search_mode="hybrid",
    )
    assert rag._semantic_active is True
    db = SessionLocal()
    try:
        results = rag.search(db, "二叉树前序遍历 递归", top_k=3)
        assert results
        assert "二叉" in results[0].text
        assert results[0].score >= 0.3
    finally:
        db.close()


def test_hybrid_search_honors_filters():
    """混合检索仍遵守课程过滤（过滤掉的切片不得出现在结果中）。"""
    rag = SQLiteRAGService(
        embedder=_FakeSemanticEmbedder(),
        search_mode="hybrid",
    )
    db = SessionLocal()
    try:
        results = rag.search(db, "二叉树", top_k=5, course="操作系统")
        assert all(r.course == "操作系统" for r in results)
    finally:
        db.close()
