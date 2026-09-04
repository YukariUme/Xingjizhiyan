"""ResearchAgent：论文阅读助手 + 科研前沿探索 Agent。"""

from sqlalchemy.orm import Session

from app.models import User
from app.repositories.research_repo import ResearchRepository
from app.services.agent.base import AgentService
from app.services.agent.teaching import _as_text, _normalize_text_list, _parse_json


class ResearchAgent(AgentService):
    name = "research"

    def run(self, db: Session, user: User, payload: dict) -> dict:
        task = payload.get("task", "analyze")
        if task == "explore":
            return self.explore(db, payload.get("topic", ""))
        return self.analyze_paper(db, int(payload.get("paper_id", 0)))

    # ---------- 论文阅读 ----------
    def analyze_paper(self, db: Session, paper_id: int) -> dict:
        paper = ResearchRepository.get_paper(db, paper_id)
        if not paper:
            return {}
        system, prompt = self.prompts.paper_analysis(
            {
                "title": paper.title,
                "authors": paper.authors,
                "venue": paper.venue,
                "year": paper.year,
                "content": paper.content,
            }
        )
        raw = self.llm.generate(prompt, system=system)
        parsed = _parse_json(raw)
        # 关联知识库，保证“论文 → 知识点 → 基础讲义”可跳转
        knowledge = self.rag.search(db, " ".join(paper.topics), top_k=3)
        # LLM 可能把“实验”等字段返回成对象/表格（如 {组别,人数,…}），
        # 统一归一化为文本，避免前端把对象当 React 子节点渲染而崩溃
        return {
            "paper_id": paper.id,
            "title": paper.title,
            "summary": _as_text(parsed.get("summary")) or paper.abstract,
            "research_question": _as_text(parsed.get("research_question")),
            "method": _as_text(parsed.get("method")),
            "experiments": _as_text(parsed.get("experiments")),
            "conclusion": _as_text(parsed.get("conclusion")),
            "limitations": _as_text(parsed.get("limitations")),
            "future": _as_text(parsed.get("future")),
            "references": [
                {
                    "title": r.document_title,
                    "source": r.document_source,
                    "course": r.course,
                    "chapter": r.chapter,
                    "snippet": r.text[:180],
                }
                for r in knowledge
            ],
            "knowledge_points": _normalize_text_list(parsed.get("knowledge_points")) or paper.topics,
            "provider": self.llm.name,
        }

    # ---------- 前沿探索 ----------
    def explore(self, db: Session, topic: str) -> dict:
        topic = (topic or "").strip()
        papers = ResearchRepository.search_papers(db, topic, limit=15)
        paper_data = [
            {"title": p.title, "year": p.year, "venue": p.venue} for p in papers
        ]
        context = self._knowledge_context(db, topic)
        system, prompt = self.prompts.frontier(topic, paper_data, context)
        raw = self.llm.generate(prompt, system=system)
        parsed = _parse_json(raw)
        raw_trend = parsed.get("trend")
        # 空列表/非列表都回退到基于论文库统计的趋势，保证图表有数据
        trend = (
            raw_trend
            if isinstance(raw_trend, list) and raw_trend
            else self._build_trend(paper_data)
        )
        # 统一归一化：LLM 返回的字段可能是对象，前端必须拿到可渲染的字符串/简单结构
        parsed["topic"] = topic
        parsed["directions"] = _normalize_text_list(parsed.get("directions"))
        parsed["hot_topics"] = _normalize_text_list(parsed.get("hot_topics"))
        parsed["papers"] = self._normalize_papers(parsed.get("papers")) or paper_data
        raw_methods = parsed.get("methods")
        parsed["methods"] = [
            {"name": _as_text(m.get("name") if isinstance(m, dict) else m), "count": int(m.get("count", 0) if isinstance(m, dict) else 0)}
            for m in (raw_methods if isinstance(raw_methods, list) else [])
            if _as_text(m.get("name") if isinstance(m, dict) else m)
        ]
        parsed["trend"] = [
            {"year": int(t.get("year", 0) if isinstance(t, dict) else 0), "count": int(t.get("count", 0) if isinstance(t, dict) else 0)}
            for t in trend
            if isinstance(t, dict) and t.get("year") is not None
        ]
        parsed["references"] = [
            {
                "title": r.document_title,
                "source": r.document_source,
                "course": r.course,
                "snippet": r.text[:160],
            }
            for r in self.rag.search(db, topic, top_k=3)
        ]
        return parsed

    @staticmethod
    def _normalize_papers(items) -> list[dict]:
        """论文列表归一化为 {title, year, venue}，兼容字符串/对象两种返回。"""
        out: list[dict] = []
        for item in items or []:
            if isinstance(item, str):
                out.append({"title": item, "year": 0, "venue": ""})
            elif isinstance(item, dict):
                title = _as_text(item.get("title") or item.get("name"))
                if not title:
                    continue
                year = item.get("year")
                out.append(
                    {
                        "title": title,
                        "year": int(year) if isinstance(year, (int, float)) else 0,
                        "venue": _as_text(item.get("venue")),
                    }
                )
        return out

    def _knowledge_context(self, db: Session, topic: str) -> str:
        results = self.rag.search(db, topic, top_k=3)
        return "\n\n".join(f"- {r.document_title}：{r.text[:160]}" for r in results)

    @staticmethod
    def _build_trend(papers: list[dict]) -> list[dict]:
        counts: dict[int, int] = {}
        for p in papers:
            counts[int(p.get("year", 2025))] = counts.get(int(p.get("year", 2025)), 0) + 1
        return [{"year": y, "count": c} for y, c in sorted(counts.items())]
