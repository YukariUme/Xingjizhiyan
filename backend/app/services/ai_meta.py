"""AI 生成内容的统一元信息：来源引用、AI 标签、可追踪信息。"""


def references_from_hits(hits, top: int = 5) -> list[dict]:
    """把 RAG 检索结果转成统一引用结构（含来源等级 [S]/[A]/[P] 与页码）。"""
    return [
        {
            "title": h.document_title,
            "source": h.document_source,
            "course": h.course,
            "chapter": h.chapter,
            "topic": h.topic,
            "source_level": h.metadata.get("source_level", "S"),
            "page": h.metadata.get("page", ""),
            "snippet": h.text[:160],
            "score": round(h.score, 4),
        }
        for h in hits[:top]
    ]


def references_from_docs(docs, top: int = 5) -> list[dict]:
    return [
        {
            "title": d.title,
            "source": d.source,
            "course": d.course,
            "chapter": d.chapter,
            "topic": d.topic,
            "source_level": d.source_level,
            "page": d.page or "",
            "snippet": (d.content or "")[:160],
        }
        for d in docs[:top]
    ]


def ai_meta(provider: str, references: list[dict] | None = None, source: str = "ai") -> dict:
    """统一的 AI 生成元信息：AI 标签 + 提供方 + 引用。"""
    return {
        "ai_generated": True,
        "ai_label": "AI 生成",
        "provider": provider,
        "source_kind": source,
        "references": references or [],
    }

