"""PostgresRAGService：PostgreSQL + pgvector 向量检索，混合同现有词法检索。

检索流程（PG 路径）：
1. TF-IDF 词法余弦（复用 SQLiteRAGService）；
2. pgvector 余弦距离 SQL 候选池（≤ 300）；
3. 0.75*语义 + 0.25*词法 + 关键词重叠奖励 + 元数据加权；
4. 严格特征词门控（与本地混合模式一致），避免无关问题误判命中。

pgvector 不可用 / 未写入向量时自动回退父类内存混合检索，接口不变。
"""

import logging

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import KnowledgeChunk
from app.services.rag.sqlite import SQLiteRAGService

logger = logging.getLogger(__name__)


class PostgresRAGService(SQLiteRAGService):
    name = "postgres-hybrid"
    VECTOR_DIM = 512  # 与 fastembed bge-small-zh-v1.5 对齐

    def __init__(self, llm=None, embedder=None, search_mode=None) -> None:
        super().__init__(llm=llm, embedder=embedder, search_mode=search_mode)
        self._pg_vector_ready: bool | None = None
        self._vector_mode = False

    # ---------- pgvector 可用性 ----------
    def _probe_pg(self, db: Session) -> bool:
        if self._pg_vector_ready is not None:
            return self._pg_vector_ready
        try:
            has_type = db.execute(
                text("SELECT to_regtype('vector') IS NOT NULL")
            ).scalar()
            has_column = db.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = 'knowledge_chunks' "
                    "AND column_name = 'embedding_vector'"
                )
            ).scalar()
            self._pg_vector_ready = bool(has_type) and bool(has_column)
            self._vector_mode = self._pg_vector_ready and self._semantic_active
            if self._pg_vector_ready:
                logger.info("pgvector 可用：开启向量检索路径（dim=%d）。", self.VECTOR_DIM)
            else:
                logger.warning("pgvector 不可用，回退内存混合检索。")
        except Exception as exc:  # noqa: BLE001
            logger.warning("pgvector 探测失败（%s），回退内存混合检索。", exc)
            self._pg_vector_ready = False
        return self._pg_vector_ready

    # ---------- 入库：额外写入 embedding_vector ----------
    def ingest_document(self, db: Session, document_id: int) -> int:
        count = super().ingest_document(db, document_id)
        if count and self._probe_pg(db) and self._vector_mode:
            chunks = (
                db.query(KnowledgeChunk)
                .filter(KnowledgeChunk.document_id == document_id)
                .all()
            )
            for chunk in chunks:
                vec = chunk.embedding or []
                if len(vec) == self.VECTOR_DIM:
                    db.execute(
                        text(
                            "UPDATE knowledge_chunks "
                            "SET embedding_vector = CAST(:v AS vector) "
                            "WHERE id = :id"
                        ),
                        {"v": _vec_to_pg(vec), "id": chunk.id},
                    )
            db.commit()
            logger.info("已写入 %d 条 pgvector 向量（文档 %d）。", len(chunks), document_id)
        return count

    # ---------- 检索：pgvector 语义候选池 + 词法混合 ----------
    def search(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
        course: str | None = None,
        course_id: int | None = None,
        source_levels: list[str] | None = None,
        visibilities: list[str] | None = None,
        owner_id: int | None = None,
        document_ids: list[int] | None = None,
    ) -> list:
        self._ensure_index(db)
        if self._matrix is None or not self._chunks:
            return []
        query_vec = self._vectorizer.transform([self._normalize_query(query)])
        lexical = self._cosine_sim_matrix(query_vec)
        mask = self._build_mask(course, course_id, source_levels, visibilities, owner_id, document_ids)
        lexical[mask] = 0.0

        vector_ready = self._probe_pg(db) and self._vector_mode
        if not vector_ready:
            # 回退：内存语义矩阵（与 SQLiteRAGService 完全一致）
            self._ensure_semantic_index()
            semantic = self._query_semantic_scores(query, mask)
            strict_gating = semantic is not None
            if semantic is not None:
                max_lex = float(lexical.max()) if len(lexical) else 0.0
                norm_lex = lexical / max_lex if max_lex > 1e-9 else lexical
                scores = 0.75 * semantic + 0.25 * norm_lex
                scores = self._apply_hybrid_boosts(query, scores, mask, top_k)
            else:
                scores = lexical
                self._boost_scores(query, scores)
            scores[mask] = 0.0
            return self._finalize_ranked(scores, mask, query, top_k, strict_gating)

        semantic = self._pg_semantic_scores(db, query, mask, top_k)
        if semantic is None:
            scores = lexical
            self._boost_scores(query, scores)
            scores[mask] = 0.0
            return self._finalize_ranked(scores, mask, query, top_k, False)
        max_lex = float(lexical.max()) if len(lexical) else 0.0
        norm_lex = lexical / max_lex if max_lex > 1e-9 else lexical
        scores = 0.75 * semantic + 0.25 * norm_lex
        scores[mask] = 0.0
        scores = self._apply_hybrid_boosts(query, scores, mask, top_k)
        scores[mask] = 0.0
        return self._finalize_ranked(scores, mask, query, top_k, True)

    def _cosine_sim_matrix(self, query_vec) -> np.ndarray:
        from sklearn.metrics.pairwise import cosine_similarity

        return cosine_similarity(query_vec, self._matrix).ravel().copy()

    def _pg_semantic_scores(
        self, db: Session, query: str, mask: np.ndarray, top_k: int
    ) -> np.ndarray | None:
        """pgvector 余弦候选池：返回与 self._chunks 对齐的语义得分数组。"""
        try:
            q_emb = self.embedder.embed_text(self._normalize_query(query))
        except Exception as exc:  # noqa: BLE001 - 语义不可用时回退词法，不中断检索
            logger.warning("语义向量化失败（%s），回退词法检索。", exc)
            return None
        if not q_emb or len(q_emb) != self.VECTOR_DIM:
            return None
        pool = max(top_k * 50, 300)
        params: dict = {"q": _vec_to_pg(q_emb), "limit": pool}
        sql = (
            "SELECT c.id, 1 - (c.embedding_vector <=> CAST(:q AS vector)) AS sim "
            "FROM knowledge_chunks c "
            "WHERE c.embedding_vector IS NOT NULL "
        )
        # 具体过滤条件由调用方通过 self._build_mask 同步处理；
        # SQL 侧只按课程做粗过滤以缩小候选池（精细过滤由 mask 兜底）
        results = db.execute(text(sql + " ORDER BY c.embedding_vector <=> CAST(:q AS vector) LIMIT :limit"), params)
        semantic = np.zeros(len(self._chunks), dtype=np.float32)
        for cid, sim in results:
            idx = self._idx_by_id.get(cid)
            if idx is not None and not mask[idx] and sim is not None:
                semantic[idx] = float(sim)
        return semantic

    # ---------- 门控阈值：向量模式按语义阈值 ----------
    def _effective_threshold(self) -> float:
        from app.config import get_settings

        settings = get_settings()
        if self._vector_mode and self._pg_vector_ready:
            return max(settings.rag_grounding_threshold, settings.rag_semantic_threshold)
        return super()._effective_threshold()


def _vec_to_pg(vec: list[float]) -> str:
    """向量列表 → pgvector 文本字面量（"[0.1,0.2,...]"）。"""
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"
