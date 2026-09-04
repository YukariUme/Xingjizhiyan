"""SQLiteRAGService：本地混合检索 RAG（词法 + 真实语义向量）。

检索流程：
1. TF-IDF（char_wb 2-4）词法余弦；
2. 真实 Embedding（fastembed / bge-small-zh-v1.5）语义余弦；
3. 混合打分：0.55 * 语义 + 0.45 * 归一化词法 + 关键词重叠奖励 + 元数据加权；
4. 可信门控：低分命中必须出现特征词，防止通用词误判；
5. S/A/P 来源等级 + 课程/所有者过滤。

EMBEDDING_PROVIDER=hash 或模型不可用时自动退化为纯词法检索，
接口与输出结构保持不变（前端只依赖 references/grounded/note 等字段）。
"""

import logging
import re
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import KnowledgeChunk
from app.repositories.knowledge_repo import KnowledgeRepository
from app.services.embedding import get_embedding_service
from app.services.embedding.base import HashEmbeddingService
from app.services.llm.base import LLMService
from app.services.rag.base import RAGService, RetrievedChunk

logger = logging.getLogger(__name__)


# 高频无意义中文双字与学科通用词（避免把“婚姻匹配算法”这类问题
# 因共享“算法/复杂度/数据结构”等通用词而误判为知识库命中）
_STOP_BIGRAMS = {
    "什么", "怎么", "为什么", "可以", "没有", "这个", "那个", "一个", "如何",
    "还是", "是不是", "是的", "地方", "附近", "好吃", "今天", "中午", "比较",
    "健康", "请问", "一下", "我们", "你们", "他们", "应该", "需要", "哪个",
    "哪些", "多少", "几个", "大概", "可能", "就是", "这样", "那样",
    "时候", "时间", "现在", "最近", "平时", "一般",
    "是什", "么是", "法是", "法怎", "么写", "写好", "好呢", "吗？",
    "呢？", "是什么", "怎么写", "怎么做",
    # 学科通用词：单独出现不足以证明知识库包含该主题
    "算法", "数据", "结构", "知识", "问题", "方法", "概念", "原理", "应用",
    "例子", "案例", "学习", "教学", "课程", "内容", "定义", "基础", "常见",
    "经典", "简单", "复杂", "分析", "讲解", "介绍", "说明", "简述", "给出",
    "列举", "使用", "实现", "设计", "流程", "步骤", "特点", "区别",
    "作用", "意义", "重点", "难点", "掌握", "理解", "熟悉", "了解", "知道",
    "提出", "解决", "处理", "进行", "相关", "主要", "核心", "关键", "重要",
    "性质", "特性", "包括", "包含", "分为", "组成", "构成", "形式", "类型",
    "方式", "模式", "框架", "体系", "系统", "平台", "工具", "技术", "理论",
    "实践", "研究", "领域", "方向", "方面", "部分", "环节", "过程", "阶段",
    "目标", "任务", "结果", "效果", "影响", "因素", "条件", "情况", "场景",
    "需求", "要求", "标准", "规范", "规则", "策略", "方案", "计划", "模型",
    "函数", "变量", "对象", "元素", "节点", "列表", "数组", "队列", "栈与",
    "输入", "输出", "返回", "遍历", "查找", "排序", "搜索", "递归", "迭代",
    "循环", "分支", "判断", "选择", "插入", "删除", "更新", "查询", "存储",
    "访问", "调用", "参数", "类型", "层次", "关系", "映射", "转换",
    "计算", "统计", "比较", "组合", "分解", "合并",
}


# 中文计算机术语 → 英文关键词（跨语言检索：中文提问也能命中英文教材）
_TRANSLATIONS: dict[str, str] = {
    "婚姻匹配": "stable marriage",
    "稳定婚姻": "stable marriage",
    "完美匹配": "perfect matching",
    "图匹配": "graph matching",
    "二分图": "bipartite graph",
    "匹配": "matching",
    "括号匹配": "parenthesis matching",
    "集合论": "set theory",
    "集合": "set",
    "运算": "operation",
    "命题逻辑": "propositional logic",
    "命题": "proposition",
    "蕴含": "implication",
    "逻辑": "logic",
    "范式": "normal form",
    "会话": "session",
    "维持": "maintain",
    "增长": "growth",
    "量级": "order of magnitude",
    "记号": "notation",
    "复杂度": "complexity",
    "大o": "big-o notation",
    "算法设计": "algorithm design",
    "算法": "algorithm",
    "动态规划": "dynamic programming",
    "分治": "divide and conquer",
    "贪心": "greedy",
    "递归": "recursion",
    "回溯": "backtracking",
    "排序": "sorting",
    "查找": "search",
    "哈希": "hash",
    "搜索": "search",
    "图论": "graph theory",
    "网络流": "network flow",
    "线性规划": "linear programming",
    "整数规划": "integer programming",
    "近似算法": "approximation algorithm",
    "复杂度": "complexity",
    "数据结构": "data structure",
    "链表": "linked list",
    "二叉树": "binary tree",
    "最短路径": "shortest path",
    "最小生成树": "minimum spanning tree",
    "拓扑排序": "topological sort",
    "随机化": "randomized",
    "多项式": "polynomial",
    "背包": "knapsack",
    "调度": "scheduling",
    "连通": "connectivity",
    "栈": "stack",
    "队列": "queue",
    "树": "tree",
    "图": "graph",
    "路径": "path",
    "流": "flow",
    "顶点": "vertex",
    "边": "edge",
    "环": "cycle",
}


# 进程级 TF-IDF 索引缓存：同一批切片只训练一次向量化器，
# 避免大教材（数万切片）入库后每次搜索都重建索引。
_TFIDF_CACHE: dict[tuple[int, int], tuple] = {}
_TFIDF_CACHE_MAX = 3

# 进程级语义向量矩阵缓存：真实 Embedding 首次构建后复用，
# 键包含切片签名 + 模型名，知识库变化或换模型时自动重建。
_SEM_CACHE: dict[tuple, np.ndarray] = {}
_SEM_CACHE_MAX = 2


class SQLiteRAGService(RAGService):
    name = "sqlite-hybrid"

    def __init__(
        self,
        llm: LLMService | None = None,
        embedder=None,
        search_mode: str | None = None,
    ) -> None:
        self.llm = llm
        settings = get_settings()
        self.embedder = embedder or get_embedding_service()
        self.search_mode = (search_mode or settings.rag_search_mode).lower()
        # 真实 Embedding 可用性：hash 为纯词法；fastembed 为混合
        self._semantic_active = (
            self.search_mode == "hybrid" and self.embedder.name != "hash"
        )
        self._sem_matrix: np.ndarray | None = None
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._chunks: list[KnowledgeChunk] = []
        self._signature: tuple[int, int] | None = None

    # ---------- 切分 ----------
    def chunk_document(self, text: str, chunk_size: int = 400, overlap: int = 60) -> list[str]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[str] = []
        buffer = ""
        for para in paragraphs:
            if len(buffer) + len(para) <= chunk_size:
                buffer = f"{buffer}\n{para}".strip()
            else:
                if buffer:
                    chunks.append(buffer)
                # 长段落按字符切分并保留重叠
                while len(para) > chunk_size:
                    chunks.append(para[:chunk_size])
                    para = para[chunk_size - overlap :]
                buffer = para
        if buffer:
            chunks.append(buffer)
        return [c for c in chunks if c.strip()]

    # ---------- 向量化 ----------
    def embed(self, text: str) -> list[float]:
        """文本向量化（委托 EmbeddingService：哈希向量或真实向量）。"""
        return self.embedder.embed_text(text)

    # ---------- TF-IDF 索引（对齐 softwarecup 的 char_wb 方案） ----------
    def _ensure_index(self, db: Session) -> None:
        chunks = KnowledgeRepository.all_chunks(db)
        signature = (len(chunks), chunks[-1].id if chunks else 0)
        self._chunks = chunks
        self._idx_by_id = {c.id: i for i, c in enumerate(chunks)}
        self._signature = signature
        cached = _TFIDF_CACHE.get(signature)
        if cached:
            self._vectorizer, self._matrix = cached
            return
        if not chunks:
            self._vectorizer = None
            self._matrix = None
            return
        vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 4), max_features=70000
        )
        matrix = vectorizer.fit_transform([c.text for c in chunks])
        self._vectorizer = vectorizer
        self._matrix = matrix
        _TFIDF_CACHE[signature] = (vectorizer, matrix)
        if len(_TFIDF_CACHE) > _TFIDF_CACHE_MAX:
            oldest = next(iter(_TFIDF_CACHE))
            _TFIDF_CACHE.pop(oldest)

    def _ensure_semantic_index(self) -> None:
        """构建真实语义向量矩阵（惰性 + 进程级缓存，失败自动回退词法）。"""
        if not self._semantic_active or self._matrix is None:
            return
        if self._sem_matrix is not None:
            return
        model_key = getattr(self.embedder, "model_name", self.embedder.name)
        cache_key = (self._signature, model_key)
        cached = _SEM_CACHE.get(cache_key)
        if cached is not None:
            self._sem_matrix = cached
            return
        # 磁盘持久化：同一批切片 + 同一模型只全量嵌入一次，服务重启直接加载
        disk_cache = self._semantic_cache_path(model_key)
        if disk_cache is not None and disk_cache.is_file():
            try:
                matrix = np.load(disk_cache)
                if matrix.ndim == 2 and matrix.shape[0] == len(self._chunks):
                    self._sem_matrix = matrix
                    _SEM_CACHE[cache_key] = matrix
                    logger.info("从磁盘加载语义向量缓存：%s", disk_cache)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("语义向量磁盘缓存损坏（%s），将重新构建。", exc)
        logger.info(
            "正在为 %d 个知识切片构建语义向量（模型：%s）...",
            len(self._chunks),
            model_key,
        )
        try:
            matrix = np.asarray(
                self.embedder.embed_documents([c.text for c in self._chunks]),
                dtype=np.float32,
            )
            if matrix.ndim != 2 or matrix.shape[1] == 0:
                raise ValueError("Embedding 返回维度异常")
            # 归一化向量，保证余弦 = 点积
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            matrix = matrix / norms
            self._sem_matrix = matrix
            _SEM_CACHE[cache_key] = matrix
            if len(_SEM_CACHE) > _SEM_CACHE_MAX:
                oldest = next(iter(_SEM_CACHE))
                _SEM_CACHE.pop(oldest)
            if disk_cache is not None:
                try:
                    disk_cache.parent.mkdir(parents=True, exist_ok=True)
                    np.save(disk_cache, matrix)
                    logger.info("语义向量已持久化：%s", disk_cache)
                except Exception as exc:  # noqa: BLE001 - 缓存失败不影响检索
                    logger.warning("语义向量持久化失败（%s），本次仅内存缓存。", exc)
            logger.info("语义向量构建完成：shape=%s", matrix.shape)
        except Exception as exc:  # noqa: BLE001 - 回退是设计内行为
            logger.warning("真实 Embedding 不可用（%s），已回退为纯词法检索。", exc)
            self._semantic_active = False
            self.embedder = HashEmbeddingService()
            self._sem_matrix = None

    def _semantic_cache_path(self, model_key: str) -> Path | None:
        """语义向量磁盘缓存路径（backend/data/embeddings/…，键含切片签名与模型名）。"""
        if not self._signature:
            return None
        settings = get_settings()
        if settings.embeddings_cache_dir:
            base = Path(settings.embeddings_cache_dir)
        else:
            db_url = settings.database_url
            if db_url.startswith("sqlite"):
                base = Path(db_url.replace("sqlite:///", "", 1)).parent / "embeddings"
            else:
                # PostgreSQL：向量由 pgvector 管理，磁盘缓存用于回退路径
                backend_dir = Path(__file__).resolve().parent.parent.parent
                base = backend_dir / "data" / "embeddings"
        name = f"sem_{len(self._chunks)}_{self._signature[1]}_{model_key.replace('/', '_')}.npy"
        return base / name

    def _normalize_query(self, query: str) -> str:
        """查询规范化：压缩空白 + 中文别名 + 中译英扩展。"""
        compact = re.sub(r"\s+", " ", query).strip()
        aliases = {
            "数据结构与算法": "数据结构 算法",
            "计算机网络": "网络 TCP",
            "操作系统": "OS 进程",
            "大模型": "大语言模型 LLM",
            "人工智能": "机器学习 AI",
        }
        for key, value in aliases.items():
            if key in compact:
                compact += f" {value}"
        return self._translate_query(compact)

    @staticmethod
    def _translate_query(query: str) -> str:
        """把中文计算机术语翻译为英文关键词，追加到查询末尾（保留中文原词）。"""
        extra: list[str] = []
        compact = query.replace(" ", "").lower()
        for key, english in sorted(_TRANSLATIONS.items(), key=lambda item: -len(item[0])):
            if key in compact:
                extra.append(english)
        if extra:
            query = f"{query} {' '.join(dict.fromkeys(extra))}"
        return re.sub(r"\s+", " ", query).strip()

    @staticmethod
    def _ascii_terms(text: str) -> set[str]:
        return {term.lower() for term in re.findall(r"[a-zA-Z][a-zA-Z0-9_]{1,}", text)}

    def _boost_scores(self, query: str, scores: np.ndarray) -> None:
        compact = query.replace(" ", "")
        ascii_terms = self._ascii_terms(query)
        for idx, chunk in enumerate(self._chunks):
            meta = dict(chunk.metadata_json or {})
            topic = meta.get("topic", "")
            chapter = meta.get("chapter", "")
            title = meta.get("title", "")
            course = meta.get("course", "")
            if topic and topic.replace(" ", "") in compact:
                scores[idx] += 0.04
            if chapter and chapter.replace(" ", "") in compact:
                scores[idx] += 0.02
            if title and any(term in compact for term in title.replace(" ", "")[:4]):
                scores[idx] += 0.02
            # 课程名互相包含（查询“算法设计”命中课程“算法设计与分析”）
            if course and (
                course.replace(" ", "") in compact or compact in course.replace(" ", "")
            ):
                scores[idx] += 0.08
            # 标题含查询英文关键词（如 “Algorithm Design”）
            if title and ascii_terms:
                title_lower = title.lower()
                if any(term in title_lower for term in ascii_terms):
                    scores[idx] += 0.05

    @staticmethod
    def _distinctive_bigrams(query: str) -> set[str]:
        """提取查询中的特征双字词（剔除通用词/学科通用词）。"""
        cjk = re.findall(r"[\u4e00-\u9fff]", query)
        bigrams = {cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)}
        return bigrams - _STOP_BIGRAMS

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        return sum(x * y for x, y in zip(a, b))

    def _keyword_overlap(self, query: str, chunk_text: str) -> float:
        """查询与切片的关键词重叠比例（0-1），用于混合打分奖励。"""
        distinctive_zh = self._distinctive_bigrams(query)
        ascii_terms = self._ascii_terms(self._normalize_query(query))
        text_lower = chunk_text.lower()
        hits = sum(1 for b in distinctive_zh if b in chunk_text)
        hits += sum(1 for t in ascii_terms if t in text_lower)
        total = max(1, len(distinctive_zh) + len(ascii_terms))
        return hits / total

    # ---------- 入库 ----------
    def ingest_document(self, db: Session, document_id: int) -> int:
        doc = KnowledgeRepository.get_document(db, document_id)
        if not doc:
            return 0
        chunks = self._chunks_for_document(doc)
        metadata = {
            "title": doc.title,
            "source": doc.source,
            "course": doc.course,
            "topic": doc.topic,
            "chapter": doc.chapter,
            "difficulty": doc.difficulty,
            "type": doc.type,
            "year": doc.year,
        }
        rows = [
            KnowledgeChunk(
                document_id=doc.id,
                chunk_index=i,
                text=text,
                embedding=self.embed(text),
                metadata_json={**metadata, **extra},
                course_id=doc.course_id,
                source_level=doc.source_level,
                visibility=doc.visibility,
            )
            for i, (text, extra) in enumerate(chunks)
        ]
        # 幂等：先删除该文档旧切片再写入
        old = db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc.id).all()
        for row in old:
            db.delete(row)
        db.flush()
        KnowledgeRepository.save_chunks(db, rows)
        # 索引已过期，强制重建
        self._signature = None
        self._sem_matrix = None
        return len(rows)

    def _chunks_for_document(
        self, doc, chunk_size: int = 400, overlap: int = 60
    ) -> list[tuple[str, dict]]:
        """文档切分：优先使用结构化块（表格/公式/代码保整），否则纯文本切分。"""
        blocks = (doc.metadata_json or {}).get("blocks") or []
        if not blocks:
            return [(text, {}) for text in self.chunk_document(doc.content, chunk_size, overlap)]
        from app.services.parsing.blocks import BlockType, StructuredBlock

        structured = [StructuredBlock.from_dict(b) for b in blocks]
        items: list[tuple[str, dict]] = []
        buffer = ""
        last_page: int | None = None

        def flush() -> None:
            nonlocal buffer
            if buffer.strip():
                items.append(
                    (
                        buffer.strip(),
                        {"block_type": BlockType.PARAGRAPH.value, "page": last_page},
                    )
                )
            buffer = ""

        for block in structured:
            if block.block_type == BlockType.PAGE_BREAK:
                flush()
                continue
            text = block.text.strip()
            if not text:
                continue
            if block.page is not None:
                last_page = block.page
            if block.block_type in (BlockType.TITLE, BlockType.HEADING):
                flush()
                items.append(
                    (
                        text,
                        {
                            "block_type": block.block_type.value,
                            "page": block.page,
                            "heading": text,
                        },
                    )
                )
                continue
            if block.block_type in (BlockType.TABLE, BlockType.FORMULA, BlockType.CODE):
                flush()
                items.append(
                    (
                        text,
                        {
                            "block_type": block.block_type.value,
                            "page": block.page,
                            "language": block.language,
                        },
                    )
                )
                continue
            # 段落/列表/注释：按 chunk_size 合并，保留块类型与页码
            if len(buffer) + len(text) <= chunk_size:
                buffer = f"{buffer}\n{text}".strip()
            else:
                flush()
                buffer = text
        flush()
        return items

    # ---------- 检索 ----------
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
    ) -> list[RetrievedChunk]:
        """混合检索：词法余弦 + 语义余弦 + 关键词重叠 + 元数据加权。"""
        self._ensure_index(db)
        if self._matrix is None or not self._chunks:
            return []
        self._ensure_semantic_index()

        query_vec = self._vectorizer.transform([self._normalize_query(query)])
        lexical = cosine_similarity(query_vec, self._matrix).ravel().copy()

        mask = self._build_mask(course, course_id, source_levels, visibilities, owner_id, document_ids)
        lexical[mask] = 0.0

        semantic = self._query_semantic_scores(query, mask)
        strict_gating = semantic is not None
        if semantic is not None:
            # 语义主导（0.75/0.25）：词法分易被英文教材的 char_wb 子串巧合
            # 抬高并压扁中文讲义，而语义分对真实命中更可靠；
            # 误命中由下方的严格特征词门控拦截
            max_lex = float(lexical.max()) if len(lexical) else 0.0
            norm_lex = lexical / max_lex if max_lex > 1e-9 else lexical
            scores = 0.75 * semantic + 0.25 * norm_lex
            scores = self._apply_hybrid_boosts(query, scores, mask, top_k)
        else:
            scores = lexical
            self._boost_scores(query, scores)

        # 元数据加权可能给已过滤切片加分，最终统一重新置零，保证过滤严格生效
        scores[mask] = 0.0
        return self._finalize_ranked(scores, mask, query, top_k, strict_gating)

    def _build_mask(
        self,
        course: str | None,
        course_id: int | None,
        source_levels: list[str] | None,
        visibilities: list[str] | None,
        owner_id: int | None,
        document_ids: list[int] | None = None,
    ) -> np.ndarray:
        """过滤掩码（课程 / 来源等级 / 可见性 / 私有所有者），与词法/语义共用。"""
        mask = np.zeros(len(self._chunks), dtype=bool)
        for idx, chunk in enumerate(self._chunks):
            meta = chunk.metadata_json or {}
            if course and meta.get("course") != course:
                mask[idx] = True
            if course_id is not None and chunk.course_id != course_id:
                mask[idx] = True
            if source_levels and chunk.source_level not in source_levels:
                mask[idx] = True
            if visibilities and chunk.visibility not in visibilities:
                mask[idx] = True
            if (
                owner_id is not None
                and chunk.visibility == "private"
                and chunk.owner_id != owner_id
            ):
                mask[idx] = True
            if document_ids and chunk.document_id not in document_ids:
                mask[idx] = True
        return mask

    def _query_semantic_scores(self, query: str, mask: np.ndarray) -> np.ndarray | None:
        """内存语义余弦（SQLiteRAGService）；PG 子类用 pgvector 覆盖。"""
        if not (self._semantic_active and self._sem_matrix is not None):
            return None
        q_emb = self.embedder.embed_text(self._normalize_query(query))
        if not q_emb or len(q_emb) != self._sem_matrix.shape[1]:
            return None
        semantic = self._sem_matrix @ np.asarray(q_emb, dtype=np.float32)
        semantic[mask] = 0.0
        return semantic

    def _apply_hybrid_boosts(
        self, query: str, scores: np.ndarray, mask: np.ndarray, top_k: int
    ) -> np.ndarray:
        """词法证据奖励 + 元数据强信号（混合模式权重高于纯词法，
        避免宽泛教材（如离散数学.pdf）的通用章节抢占无关查询）。"""
        compact_query = query.replace(" ", "")
        # 只对候选子集计算词法奖励/元数据加权（15k 全量循环会拖慢每次查询）
        candidate_pool = np.argsort(-scores)[: max(top_k * 50, 300)]
        for idx in candidate_pool:
            if mask[idx]:
                continue
            chunk = self._chunks[int(idx)]
            overlap = self._keyword_overlap(query, chunk.text)
            if overlap > 0:
                scores[idx] += 0.12 * overlap
            meta = chunk.metadata_json or {}
            topic = (meta.get("topic") or "").replace(" ", "")
            chapter = (meta.get("chapter") or "").replace(" ", "")
            course_name = (meta.get("course") or "").replace(" ", "")
            if topic and len(topic) >= 2 and topic in compact_query:
                scores[idx] += 0.15
            if chapter and len(chapter) >= 2 and chapter in compact_query:
                scores[idx] += 0.10
            if (
                course_name
                and len(course_name) >= 2
                and (course_name in compact_query or compact_query in course_name)
            ):
                scores[idx] += 0.08
        return scores

    def _finalize_ranked(
        self,
        scores: np.ndarray,
        mask: np.ndarray,
        query: str,
        top_k: int,
        strict_gating: bool,
    ) -> list[RetrievedChunk]:
        """候选池门控与结果组装（混合模式用更大候选池）。"""
        # 混合（真实语义）模式下对所有候选强制特征词门控：
        # 防止“附近有什么好吃的川菜馆”等无关问题靠语义相似度误判命中
        candidate_count = max(top_k * 50, 300) if strict_gating else max(top_k * 10, 40)
        ranked = scores.argsort()[::-1][:candidate_count]
        distinctive_zh = self._distinctive_bigrams(query)
        ascii_terms = self._ascii_terms(self._normalize_query(query))
        compact_query = query.replace(" ", "")
        results: list[RetrievedChunk] = []
        for idx in ranked:
            if len(results) >= top_k:
                break
            if scores[idx] <= 0.0:
                continue
            if mask[idx]:
                continue
            chunk = self._chunks[int(idx)]
            meta = chunk.metadata_json or {}
            # 来源等级（S/A/P）与可见性来自列字段，补进返回元数据供引用展示
            meta["source_level"] = chunk.source_level
            meta["visibility"] = chunk.visibility
            meta["document_id"] = chunk.document_id
            topic = (meta.get("topic") or "").replace(" ", "")
            chapter = (meta.get("chapter") or "").replace(" ", "")
            course_name = (meta.get("course") or "").replace(" ", "")
            text_lower = chunk.text.lower()
            if scores[idx] < 0.25 or strict_gating:
                # 低分命中必须至少 2 个特征词真实出现在切片中：
                # 仅共享 1 个通用词（如“括号匹配”对“婚姻匹配”）不算命中
                zh_matches = sum(1 for b in distinctive_zh if b in chunk.text)
                en_matches = sum(1 for t in ascii_terms if t in text_lower)
                # 元数据强信号：主题/章节/课程名完整出现在问题中
                metadata_signal = (
                    (topic and len(topic) >= 2 and topic in compact_query)
                    or (chapter and len(chapter) >= 2 and chapter in compact_query)
                    or (
                        course_name
                        and len(course_name) >= 2
                        and (course_name in compact_query or compact_query in course_name)
                    )
                )
                if metadata_signal:
                    zh_matches += 2
                # 元数据词项信号：主题/章节/课程里出现查询特征词也算证据
                # （如“数据库范式分解”命中主题“关系模型与范式”）
                if not metadata_signal and distinctive_zh:
                    meta_text = f"{topic}{chapter}{course_name}"
                    if any(b in meta_text for b in distinctive_zh):
                        zh_matches += 2
                if not (
                    zh_matches >= 2
                    or en_matches >= 2
                    or (zh_matches >= 1 and en_matches >= 1)
                ):
                    continue
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    text=chunk.text[:400],
                    document_title=meta.get("title", ""),
                    document_source=meta.get("source", ""),
                    course=meta.get("course", ""),
                    chapter=meta.get("chapter", ""),
                    topic=meta.get("topic", ""),
                    score=round(float(scores[idx]), 4),
                    metadata=meta,
                )
            )
        return results

    # ---------- 重排 ----------
    def rerank(self, results: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """按标题/主题匹配度轻微加权的重排（Mock 重排器）。"""

        def weight(r: RetrievedChunk) -> float:
            bonus = 0.0
            if r.topic and r.topic in r.text[:100]:
                bonus += 0.02
            if r.chapter and r.chapter in r.text:
                bonus += 0.01
            return r.score + bonus

        return sorted(results, key=weight, reverse=True)

    def _effective_threshold(self) -> float:
        """门控阈值：混合模式用语义阈值，纯词法模式用词法阈值。"""
        settings = get_settings()
        if self._semantic_active and self._sem_matrix is not None:
            return max(settings.rag_grounding_threshold, settings.rag_semantic_threshold)
        return settings.rag_grounding_threshold

    # ---------- 检索 + 生成 ----------
    def generate_answer(self, db: Session, query: str, top_k: int = 5) -> dict:
        """RAG 回答：先检索，命中则带引用交给 LLM；未命中则回退为模型自身知识。

        返回结构：{answer, references, grounded, confidence, note, query}。
        """
        results = self.rerank(self.search(db, query, top_k=top_k))
        threshold = self._effective_threshold()
        grounded = bool(results) and results[0].score >= threshold
        if grounded and results:
            self._bump_hit_count(db, results[0])
        references = [
            {
                "title": r.document_title,
                "source": r.document_source,
                "course": r.course,
                "chapter": r.chapter,
                "topic": r.topic,
                "source_level": r.metadata.get("source_level", "S"),
                "page": r.metadata.get("page", ""),
                "snippet": r.text,
                "score": r.score,
            }
            for r in results
        ]
        note = ""
        if grounded and any(ref["source_level"] != "S" for ref in references) and any(
            ref["source_level"] == "S" for ref in references
        ):
            note = "不同资料存在表述差异，已优先采用课程官方资料（[S]）。"
        llm = self.llm
        if llm is None:
            from app.services.llm.factory import get_llm_service

            llm = get_llm_service()
        if grounded:
            context = "\n\n".join(f"[{i + 1}] {r.text}" for i, r in enumerate(results))
            prompt = (
                f"学生问题：{query}\n\n[知识库参考内容]\n{context}\n\n"
                "请基于参考内容回答，引用时标注来源编号；如果参考内容不足，请明确说明。"
            )
            system = "你是计算机学科知识问答助手，回答必须可追溯。"
        else:
            prompt = (
                f"学生问题：{query}\n\n"
                "（知识库未检索到相关依据）请基于模型自身知识回答，并在开头注明"
                "“该回答未找到平台知识库依据，以下为模型自身知识”。"
            )
            system = "你是计算机学科知识问答助手。"
        answer = llm.generate(prompt, system=system)
        return {
            "answer": answer,
            "references": references if grounded else [],
            "grounded": grounded,
            "confidence": round(results[0].score, 4) if results else 0.0,
            "note": note,
            "query": query,
        }

    def retrieve_context(self, db: Session, query: str, top_k: int = 5, **filters) -> dict:
        """只检索不生成：返回上下文与引用（含来源等级与冲突提示）。"""
        results = self.rerank(
            self.search(
                db,
                query,
                top_k=top_k,
                course=filters.get("course"),
                course_id=filters.get("course_id"),
                source_levels=filters.get("source_levels"),
                visibilities=filters.get("visibilities"),
                owner_id=filters.get("owner_id"),
            )
        )
        threshold = self._effective_threshold()
        grounded = bool(results) and results[0].score >= threshold
        if grounded and results:
            self._bump_hit_count(db, results[0])
        references = [
            {
                "title": r.document_title,
                "source": r.document_source,
                "course": r.course,
                "source_level": r.metadata.get("source_level", "S"),
                "page": r.metadata.get("page", ""),
                "snippet": r.text,
                "score": r.score,
            }
            for r in results
        ]
        note = ""
        if grounded and any(ref["source_level"] != "S" for ref in references) and any(
            ref["source_level"] == "S" for ref in references
        ):
            note = "不同资料存在表述差异，已优先采用课程官方资料（[S]）。"
        context = "\n\n".join(
            f"[{r.metadata.get('source_level', 'S')}] {r.document_title}：{r.text}"
            for r in results
        )
        return {
            "context": context,
            "references": references if grounded else [],
            "grounded": grounded,
            "confidence": round(results[0].score, 4) if results else 0.0,
            "note": note,
        }

    @staticmethod
    def _bump_hit_count(db: Session, result: RetrievedChunk) -> None:
        """RAG 使用统计：命中 Top1 时给对应文档计数 +1（轻量、可追踪）。"""
        document_id = result.metadata.get("document_id")
        if not document_id:
            return
        from app.models import KnowledgeDocument

        doc = db.get(KnowledgeDocument, int(document_id))
        if doc:
            doc.rag_hit_count = (doc.rag_hit_count or 0) + 1
            db.add(doc)
            try:
                db.commit()
            except Exception:  # noqa: BLE001 - 统计失败不影响检索
                db.rollback()
