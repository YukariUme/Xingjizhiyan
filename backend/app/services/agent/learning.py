"""LearningAgent：学生 AI 学科导师 + 代码错误诊断 Agent。"""

from sqlalchemy.orm import Session

from app.models import ChatMessage, User
from app.config import get_settings
from app.repositories.learning_repo import LearningRepository
from app.services.agent.base import AgentService
from app.services.agent.teaching import _as_text, _normalize_text_list, _parse_json
from app.services.judge.base import JudgeResult, TestCaseResult


class LearningAgent(AgentService):
    name = "learning"

    def run(self, db: Session, user: User, payload: dict) -> dict:
        task = payload.get("task", "tutor")
        if task == "diagnose":
            return self.diagnose_code(db, user, payload)
        return self.tutor_chat(db, user, payload)

    # ---------- 学科导师 ----------
    def tutor_chat(self, db: Session, user: User, payload: dict) -> dict:
        message = payload.get("message", "")
        image_base64 = payload.get("image_base64") or ""
        if image_base64:
            # 多模态：图片先经 VisionService 转文字，再进入 RAG + LLM 流程
            from app.services.vision import VisionError, get_vision_service

            try:
                image_bytes = self._decode_image(image_base64)
                vision = get_vision_service()
                vision_text = vision.analyze_image(
                    image_bytes,
                    prompt=f"学生提问：{message}",
                )
                message = f"{message}\n[学生上传的图片]\n{vision_text}".strip()
            except (VisionError, ValueError) as exc:
                message = f"{message}\n[图片解析失败：{exc}]".strip()
        mode = payload.get("mode", "hint")
        teaching = bool(payload.get("teaching")) or mode in ("teaching", "quick", "deep")
        answer_style = "deep" if mode in ("deep", "teaching") else ("quick" if mode == "quick" else "detail")
        history = payload.get("history", [])
        course_id = payload.get("course_id")
        chapter_id = payload.get("chapter_id")
        scope = payload.get("scope", "official")
        primary_ids = [int(x) for x in (payload.get("primary_document_ids") or [])]
        secondary_ids = [int(x) for x in (payload.get("secondary_document_ids") or [])]
        document_ids = primary_ids + secondary_ids
        primary_set = set(primary_ids)
        primary_titles = self._document_titles(db, primary_ids)
        query = message
        if primary_titles:
            query = f"{message} {primary_titles[0]}"
        source_levels, visibilities, owner_id = self._scope_filters(scope, user.id)
        if document_ids:
            # 用户显式选择资料：直接从这些文档检索，不受通用门控影响
            hits = self._retrieve_from_documents(db, query, document_ids, top_k=6)
        else:
            hits = self.rag.search(
                db,
                query,
                top_k=4,
                course_id=int(course_id) if course_id else None,
                source_levels=source_levels,
                visibilities=visibilities,
                owner_id=owner_id,
            )
        if primary_set:
            hits = sorted(
                hits,
                key=lambda h: (
                    0 if int(h.metadata.get("document_id") or 0) in primary_set else 1,
                    -h.score,
                ),
            )
        threshold = get_settings().rag_grounding_threshold
        grounded = bool(hits) and (hits[0].score >= threshold or bool(document_ids))
        context_scope = ""
        if course_id:
            from app.models import Course

            course = db.get(Course, int(course_id))
            context_scope = f"当前课程：{course.name if course else ''}；"
        if chapter_id:
            from app.models import CourseChapter

            chapter = db.get(CourseChapter, int(chapter_id))
            context_scope += f"当前章节：{chapter.title if chapter else ''}；"
        context_scope += f"资料范围：{scope}"
        context = (
            "\n\n".join(
                f"- [{'主资料' if int(r.metadata.get('document_id') or 0) in primary_set else '背景资料'}] "
                f"{r.document_title}（{r.document_source}）：{r.text[:160]}"
                for r in hits
            )
            if grounded
            else ""
        )
        system, prompt = self.prompts.tutor(
            message, history, context, mode, grounded, context_scope,
            teaching=teaching,
            primary_title=primary_titles[0] if primary_titles else "",
            answer_style=answer_style,
        )
        raw = self.llm.generate(prompt, system=system)
        parsed = _parse_json(raw)
        answer = _as_text(parsed.get("answer")) or self._fallback_answer(message, mode, hits, grounded)
        knowledge_points = _normalize_text_list(parsed.get("knowledge_points")) or [
            r.topic for r in hits if r.topic
        ]
        # 来源引用只允许来自实际命中的知识库文档，不信任模型自报的引用
        references = [r.document_title for r in hits] if grounded else []

        # 保存对话历史（用户 + 助手）
        LearningRepository.add_message(
            db,
            ChatMessage(
                user_id=user.id,
                agent_type="learning",
                role="user",
                content=message,
            ),
        )
        assistant = LearningRepository.add_message(
            db,
            ChatMessage(
                user_id=user.id,
                agent_type="learning",
                role="assistant",
                content=answer,
                knowledge_points=knowledge_points,
                references=references,
            ),
        )
        return {
            "answer": answer,
            "mode": mode,
            "knowledge_points": knowledge_points,
            "references": references,
            "conversation_id": assistant.id,
            "grounded": grounded,
            "confidence": round(hits[0].score, 4) if hits else 0.0,
        }

    @staticmethod
    def _fallback_answer(message: str, mode: str, hits, grounded: bool) -> str:
        if mode == "hint":
            return (
                f"关于「{message}」，先思考三个问题：它解决什么问题？核心步骤是什么？"
                f"边界情况如何处理？"
                + (f"\n参考：{hits[0].document_title}" if grounded and hits else "")
                + ("" if grounded else "\n（知识库未检索到相关依据，以下为模型自身知识）")
            )
        return f"关于「{message}」的解析：" + (
            f"\n{hits[0].text[:240]}" if grounded and hits else "知识库未检索到直接依据，以下基于模型自身知识回答。"
        )

    def _retrieve_from_documents(self, db: Session, query: str, doc_ids: list[int], top_k: int = 6):
        """用户显式选择资料时：直接从这些文档的切片中检索，按向量/词法相似度排序。"""
        from app.models import KnowledgeChunk
        from app.services.rag.base import RetrievedChunk

        chunks = (
            db.query(KnowledgeChunk)
            .filter(KnowledgeChunk.document_id.in_(doc_ids))
            .order_by(KnowledgeChunk.document_id, KnowledgeChunk.chunk_index)
            .limit(200)
            .all()
        )
        if not chunks:
            return []
        q_vec = self.rag.embed(query) or []
        q_set = set(query.replace(" ", ""))
        scored = []
        for c in chunks:
            c_vec = c.embedding or []
            if q_vec and c_vec and len(q_vec) == len(c_vec):
                score = sum(a * b for a, b in zip(q_vec, c_vec))
            else:
                c_set = set((c.text or "")[:300].replace(" ", ""))
                score = len(q_set & c_set) / max(1, len(q_set)) * 0.5
            meta = dict(c.metadata_json or {})
            meta["document_id"] = c.document_id
            scored.append(
                RetrievedChunk(
                    chunk_id=c.id,
                    text=(c.text or "")[:400],
                    document_title=meta.get("title", ""),
                    document_source=meta.get("source", ""),
                    course=meta.get("course", ""),
                    chapter=meta.get("chapter", ""),
                    topic=meta.get("topic", ""),
                    score=round(float(score), 4),
                    metadata=meta,
                )
            )
        scored.sort(key=lambda r: -r.score)
        return scored[:top_k]

    @staticmethod
    def _document_titles(db: Session, doc_ids: list[int]) -> list[str]:
        if not doc_ids:
            return []
        from app.models import KnowledgeDocument

        rows = db.query(KnowledgeDocument).filter(KnowledgeDocument.id.in_(doc_ids)).all()
        by_id = {d.id: d.title for d in rows}
        return [by_id[i] for i in doc_ids if i in by_id]

    @staticmethod
    def _scope_filters(scope: str, user_id: int):
        """按资料范围返回 RAG 过滤条件：S 官方 > A 审核共享 > P 个人。"""
        if scope == "official":
            return ["S"], ["official"], None
        if scope == "shared":
            return ["S", "A"], ["official", "shared"], None
        if scope == "personal":
            return None, None, user_id  # 官方+共享+自己的私有
        return None, None, None  # extended：全部 + 允许模型扩展知识

    @staticmethod
    def _decode_image(image_base64: str) -> bytes:
        """把 base64 / data URL 图片解码为字节。"""
        import base64

        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",", 1)[-1]
        return base64.b64decode(image_base64)

    # ---------- 代码错误诊断 ----------
    def diagnose_code(self, db: Session, user: User, payload: dict) -> dict:
        mode = payload.get("mode", "hint")
        source_code = payload.get("source_code", "")
        language = payload.get("language", "python")
        question_title = payload.get("question_title", "")
        question_desc = payload.get("question_description", "")
        report_raw = payload.get("judge_report", [])
        error_message = payload.get("error_message", "")
        report = [
            TestCaseResult(
                test_id=int(r.get("test_id", 0)),
                name=r.get("name", ""),
                passed=bool(r.get("passed", False)),
                message=r.get("message", ""),
                expected=r.get("expected", ""),
                actual=r.get("actual", ""),
                time_ms=int(r.get("time_ms", 0)),
            )
            for r in report_raw
            if isinstance(r, dict)
        ]
        judge = JudgeResult(
            verdict="wrong_answer",
            passed_tests=0,
            total_tests=0,
            error_message=error_message,
            report=report,
        )
        system, prompt = self.prompts.code_diagnosis(
            question_title, question_desc, source_code, judge, mode
        )
        raw = self.llm.generate(prompt, system=system)
        parsed = _parse_json(raw)
        return {
            "error_reason": _as_text(parsed.get("error_reason")) or "评测未通过，请结合测试点信息排查。",
            "knowledge_points": _normalize_text_list(parsed.get("knowledge_points")),
            "thinking": _normalize_text_list(parsed.get("thinking")),
            "advice": _normalize_text_list(parsed.get("advice")),
            "suggestion": _as_text(parsed.get("suggestion")),
            "mode": mode,
        }
