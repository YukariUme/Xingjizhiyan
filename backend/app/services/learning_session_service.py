"""可重复自学链（LearningSession）生成与交互服务。

一条自学链围绕单个知识点，由 LLM 生成有序交互步骤（goal/warmup/explain/
visualize/code/practice/check/wrapup），学生逐步推进。生成内容要求自包含，
禁止出现“请阅读教材第 X 页”这类指向外部资料的动作，引用来源仅用于可追溯。

设计要点：
- 任意知识点复用：入参为 course/chapter/knowledge_point，不依赖具体课程结构。
- 可扩展：步骤类型是白名单，前端按 type 分发渲染，新增类型只需扩展 normalize
  与前端 renderer。
- 演示兜底：LLM 不可用或返回非法 JSON 时，用知识点描述 + RAG 片段构造最小链。
"""

import json
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    Course,
    CourseChapter,
    KnowledgePoint,
    LearningRecord,
    LearningSession,
    StudentKnowledgeProfile,
    User,
)
from app.repositories.learning_repo import LearningRepository
from app.services.ai_meta import ai_meta, references_from_hits
from app.services.llm.factory import get_llm_service
from app.services.rag.factory import get_rag_service


STEP_TYPES = {
    "goal",
    "warmup",
    "explain",
    "visualize",
    "code",
    "practice",
    "check",
    "wrapup",
}

# quick 深度只保留轻量步骤，保证快速热身；standard/deep 保留完整链。
QUICK_KEEP = {"goal", "warmup", "explain", "check", "wrapup"}


def _parse_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [_as_text(v) for v in value]
        return "\n".join(f"- {p}" for p in parts if p)
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            text = _as_text(v)
            if text:
                parts.append(f"{k}：{text}")
        return "；".join(parts)
    return str(value)


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    return [value]


def _as_str_list(value) -> list[str]:
    return [x for x in (_as_text(v) for v in _as_list(value)) if x]


def _normalize_step(raw) -> dict | None:
    """把 LLM 返回的单个步骤归一化成稳定的白名单结构。"""
    if not isinstance(raw, dict):
        return None
    step_type = str(raw.get("type") or raw.get("kind") or "").strip().lower()
    if step_type not in STEP_TYPES:
        # 未知类型兜底为讲解，保证不丢内容
        step_type = "explain"

    step: dict = {"type": step_type}

    if step_type == "goal":
        step["text"] = _as_text(raw.get("text") or raw.get("goal") or raw.get("content"))
    elif step_type == "warmup":
        step["question"] = _as_text(raw.get("question") or raw.get("text"))
        opts = raw.get("options") or raw.get("choices")
        if isinstance(opts, list):
            step["options"] = [_as_text(o) for o in opts if _as_text(o)]
    elif step_type == "explain":
        step["title"] = _as_text(raw.get("title") or raw.get("name"))
        step["content"] = _as_text(raw.get("content") or raw.get("text") or raw.get("explanation"))
        step["example"] = _as_text(raw.get("example") or raw.get("example_text"))
        step["anchor"] = _as_text(raw.get("anchor") or raw.get("highlight"))
    elif step_type == "visualize":
        step["kind"] = _as_text(raw.get("kind") or raw.get("viz_type") or "simulation")
        step["title"] = _as_text(raw.get("title") or raw.get("name"))
        payload = raw.get("payload") or raw.get("data") or {}
        step["payload"] = payload if isinstance(payload, dict) else {}
    elif step_type == "code":
        step["language"] = _as_text(raw.get("language") or raw.get("lang") or "python")
        step["code"] = _as_text(raw.get("code") or raw.get("source") or raw.get("content"))
        step["expected_output"] = _as_text(raw.get("expected_output") or raw.get("output"))
    elif step_type == "practice":
        step["question"] = _as_text(raw.get("question") or raw.get("text") or raw.get("title"))
        step["qtype"] = _as_text(raw.get("qtype") or raw.get("type") or "short")
        opts = raw.get("options")
        if isinstance(opts, list):
            step["options"] = [_as_text(o) for o in opts if _as_text(o)]
        step["answer"] = raw.get("answer")
        step["hint"] = _as_text(raw.get("hint") or raw.get("analysis") or raw.get("explanation"))
        step["analysis"] = _as_text(raw.get("analysis") or raw.get("explanation") or raw.get("reason"))
    elif step_type == "check":
        step["prompt"] = _as_text(raw.get("prompt") or raw.get("question") or raw.get("text"))
    elif step_type == "wrapup":
        step["summary"] = _as_text(raw.get("summary") or raw.get("content") or raw.get("text"))
        step["weak_points"] = _as_str_list(raw.get("weak_points") or raw.get("weak"))
        step["suggestion"] = _as_text(raw.get("suggestion") or raw.get("next"))

    return step


def _fallback_steps(course_name: str, chapter_title: str, kp_name: str, kp_desc: str, context: str) -> list[dict]:
    """LLM 不可用时的最小可用链（保证演示离线可用）。"""
    body = kp_desc or context or f"围绕「{kp_name}」掌握其核心概念、典型方法与边界条件。"
    return [
        {"type": "goal", "text": f"能用自己的话说明「{kp_name}」是什么、怎么用，并给出一个例子。"},
        {"type": "warmup", "question": f"在 {chapter_title or course_name} 中，「{kp_name}」主要用来解决什么问题？"},
        {
            "type": "explain",
            "title": f"认识「{kp_name}」",
            "content": body,
            "example": f"用一个最小规模的例子走一遍「{kp_name}」的完整流程。",
        },
        {
            "type": "visualize",
            "title": "动图演示",
            "kind": "sorting",
            "payload": {"ds": "sorting"},
        },
        {
            "type": "practice",
            "question": f"用一句话说明「{kp_name}」的核心思想，并指出一个常见边界情况。",
            "qtype": "short",
            "hint": "先回答“解决什么问题”，再补充“注意什么边界”。",
        },
        {"type": "check", "prompt": f"不看笔记，用自己的话复述「{kp_name}」的定义与一个易错点。"},
        {
            "type": "wrapup",
            "summary": f"本次自学了「{kp_name}」的核心概念与一个边界情况。",
            "weak_points": [],
            "suggestion": "可换一个深度重新学习，或进入「作业与实验」做一道相关编程题。",
        },
    ]


def _depth_filter(steps: list[dict], depth: str) -> list[dict]:
    if depth != "quick":
        return steps
    return [s for s in steps if s.get("type") in QUICK_KEEP]


def _ensure_bookends(steps: list[dict], course_name: str, chapter_title: str, kp_name: str, kp_desc: str, context: str) -> list[dict]:
    """确保链以 goal 开头、以 wrapup 结尾。"""
    if not steps:
        steps = _fallback_steps(course_name, chapter_title, kp_name, kp_desc, context)
    if steps[0].get("type") != "goal":
        steps.insert(0, {"type": "goal", "text": f"掌握「{kp_name}」的核心概念与典型应用。"})
    if steps[-1].get("type") != "wrapup":
        steps.append(
            {
                "type": "wrapup",
                "summary": f"本次自学了「{kp_name}」。",
                "weak_points": [],
                "suggestion": "可换一个知识点继续，或完成相关练习巩固。",
            }
        )
    return steps


class LearningSessionService:
    @staticmethod
    def generate_session(
        db: Session,
        user: User,
        course_id: int,
        chapter_id: int | None,
        knowledge_point_id: int | None,
        depth: str = "standard",
        mode: str = "learn",
    ) -> LearningSession:
        course = db.get(Course, course_id)
        if not course:
            raise ValueError("课程不存在")
        chapter = db.get(CourseChapter, chapter_id) if chapter_id else None
        kp = db.get(KnowledgePoint, knowledge_point_id) if knowledge_point_id else None

        # 未指定知识点时，取该章第一个知识点，保证“任意知识点”也有一个可锚定的对象
        if kp is None and chapter_id:
            kp = (
                db.query(KnowledgePoint)
                .filter(KnowledgePoint.chapter_id == chapter_id)
                .order_by(KnowledgePoint.id)
                .first()
            )

        kp_name = kp.name if kp else (chapter.title if chapter else course.name)
        kp_desc = kp.description if kp else (chapter.summary if chapter else "")
        chapter_title = chapter.title if chapter else ""

        rag = get_rag_service()
        query = f"{course.name} {chapter_title} {kp_name}".strip()
        hits = rag.search(
            db,
            query,
            top_k=5,
            course_id=course_id,
            source_levels=["S", "A"],
        )
        context = "\n".join(
            f"[{h.metadata.get('source_level', 'S')}] {h.document_title}：{h.text[:200]}"
            for h in hits
        )

        llm = get_llm_service()
        system = (
            "你是高校计算机学科的 AI 授课助教。你必须把知识点讲透、讲完整，"
            "输出 JSON，不要输出 Markdown 或解释性文字。"
        )
        prompt = (
            f"为知识点「{kp_name}」生成一条可交互的自学链。\n"
            f"课程：{course.name}\n章节：{chapter_title}\n"
            f"知识点描述：{kp_desc}\n"
            f"讲解深度：{depth}（quick=要点热身，standard=完整讲解+代码/演示+练习，deep=更细推导+多例子）\n"
            f"知识库参考：\n{context}\n\n"
            "要求：内容必须自包含，学生读完就能理解，禁止出现“请阅读教材第 X 页”这类动作；"
            "引用来源只用于追溯，不作为必读材料。\n"
            '请输出 JSON，仅含一个 "steps" 数组，每项是一个步骤，步骤类型与字段如下：\n'
            '- goal: {"type":"goal","text":"一句话目标"}\n'
            '- warmup: {"type":"warmup","question":"引入问题","options":["A","B"]}\n'
            '- explain: {"type":"explain","title":"小节标题","content":"200-400字讲解，定义→直觉→性质→边界","example":"一个例子","anchor":"可高亮的关键词"}\n'
            '- visualize: {"type":"visualize","kind":"algorithm|data_structure|simulation","title":"演示标题","payload":{}}\n'
            '- code: {"type":"code","language":"python","code":"可运行片段","expected_output":"预期输出"}\n'
            '- practice: {"type":"practice","question":"题目","qtype":"single|multiple|judge|short","options":["A"],"answer":"参考答案","hint":"提示","analysis":"解析"}\n'
            '- check: {"type":"check","prompt":"让学生用自己的话复述"}\n'
            '- wrapup: {"type":"wrapup","summary":"小结","weak_points":["易错点"],"suggestion":"下一步建议"}\n'
            "按顺序：先 goal，再 warmup，然后 explain（可多段），中间按知识点类型插入 visualize/code，"
            "再 practice、check，最后 wrapup。"
        )
        raw = llm.generate(prompt, system=system)
        parsed = _parse_json(raw)
        raw_steps = parsed.get("steps") if isinstance(parsed.get("steps"), list) else []
        steps = [s for s in (_normalize_step(item) for item in raw_steps) if s]
        steps = _ensure_bookends(steps, course.name, chapter_title, kp_name, kp_desc, context)
        steps = _depth_filter(steps, depth)
        # 深度过滤后仍要保证 wrapup 收尾
        if steps[-1].get("type") != "wrapup":
            steps.append(
                {
                    "type": "wrapup",
                    "summary": f"本次自学了「{kp_name}」。",
                    "weak_points": [],
                    "suggestion": "可换一个知识点继续。",
                }
            )

        session = LearningSession(
            student_id=user.id,
            course_id=course_id,
            chapter_id=chapter_id,
            knowledge_point_id=kp.id if kp else None,
            title=kp_name,
            depth=depth,
            mode=mode,
            steps=steps,
            meta=ai_meta(llm.name, references_from_hits(hits), source="learning_session"),
            current_index=0,
            status="active",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        db.add(
            LearningRecord(
                student_id=user.id,
                course_id=course_id,
                chapter_id=chapter_id,
                knowledge_point_id=session.knowledge_point_id,
                action="session",
                detail={
                    "session_id": session.id,
                    "depth": depth,
                    "mode": mode,
                    "title": session.title,
                },
            )
        )
        db.commit()
        return session

    @staticmethod
    def serialize(db: Session, session: LearningSession) -> dict:
        meta = session.meta or {}
        return {
            "id": session.id,
            "title": session.title,
            "depth": session.depth,
            "mode": session.mode,
            "course_id": session.course_id,
            "chapter_id": session.chapter_id,
            "knowledge_point_id": session.knowledge_point_id,
            "current_index": session.current_index,
            "status": session.status,
            "steps": session.steps,
            "provider": meta.get("provider"),
            "ai_generated": meta.get("ai_generated", True),
            "references": meta.get("references", []),
            "created_at": session.created_at.isoformat(),
        }

    @staticmethod
    def _answer_display(value) -> str:
        """把参考答案（str/dict/list）转成可读文本。"""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for key in ("value", "text", "answer", "index", "content"):
                if value.get(key) is not None:
                    return _as_text(value.get(key))
            return _as_text(value)
        if isinstance(value, list):
            return "、".join(_as_text(v) for v in value if _as_text(v))
        return str(value)

    @staticmethod
    def _correct_option_text(step: dict) -> str:
        """把客观题参考答案解析成“正确选项文本”，兼容 index/文本/布尔。"""
        options = [str(o) for o in (step.get("options") or [])]
        ans = step.get("answer")
        if ans is None:
            return ""
        # int / 数值字符串 → 选项下标
        if isinstance(ans, bool):
            return "正确" if ans else "错误"
        if isinstance(ans, (int, float)):
            i = int(ans)
            return options[i] if options and 0 <= i < len(options) else str(ans)
        if isinstance(ans, str):
            s = ans.strip()
            if s.isdigit() and options and 0 <= int(s) < len(options):
                return options[int(s)]
            low = s.lower()
            if low in {"true", "t", "yes"}:
                return "正确"
            if low in {"false", "f", "no"}:
                return "错误"
            return s
        if isinstance(ans, dict):
            for key in ("index", "value", "answer", "text", "content"):
                if key not in ans or ans[key] is None:
                    continue
                v = ans[key]
                if isinstance(v, bool):
                    return "正确" if v else "错误"
                if isinstance(v, (int, float)):
                    i = int(v)
                    return options[i] if options and 0 <= i < len(options) else str(v)
                return str(v)
        return _as_text(ans)

    @staticmethod
    def _judge_short_answer(question: str, reference: str, student: str) -> tuple[bool, str]:
        """简答题判对错：优先 LLM，失败时回退关键词重叠启发式。"""
        student_text = (student or "").strip()
        if not student_text:
            return False, "答案为空。"
        if reference and (student_text in reference or reference in student_text):
            return True, "与参考答案一致。"

        llm = get_llm_service()
        prompt = (
            f"请判断学生答案是否正确。\n题目：{question}\n参考答案：{reference or '（无）'}\n"
            f"学生答案：{student_text}\n"
            '请输出 JSON：{"correct": true/false, "reason": "一句话说明对错原因"}'
        )
        try:
            raw = llm.generate(prompt, system="你是严格但友善的计算机学科助教。")
            parsed = _parse_json(raw)
            if "correct" in parsed:
                return bool(parsed.get("correct")), _as_text(
                    parsed.get("reason") or parsed.get("analysis")
                ) or ("回答正确。" if parsed.get("correct") else "与参考答案不一致。")
        except Exception:  # noqa: BLE001 - 判分失败走启发式
            pass

        ref_terms = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z][a-zA-Z0-9_]{1,}", reference.lower()))
        stu_terms = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z][a-zA-Z0-9_]{1,}", student_text.lower()))
        if ref_terms and stu_terms:
            overlap = len(ref_terms & stu_terms) / max(1, len(ref_terms))
            if overlap >= 0.5:
                return True, f"覆盖参考答案关键点（约 {overlap:.0%}）。"
        return False, "与参考答案关键点不一致，可对照解析再思考。"

    @staticmethod
    def _update_profile(db: Session, student_id: int, kp_id: int | None, correct: bool) -> None:
        """把一次练习结果写入学生知识点画像（薄弱点回流）。"""
        if not kp_id:
            return
        profile = LearningRepository.get_profile(db, student_id, kp_id)
        if not profile:
            profile = StudentKnowledgeProfile(student_id=student_id, knowledge_point_id=kp_id)
        profile.attempts = (profile.attempts or 0) + 1
        if not correct:
            profile.errors = (profile.errors or 0) + 1
        ratio = 1.0 if correct else 0.4
        old = profile.mastery or 0.0
        profile.mastery = round(min(100.0, old * 0.6 + ratio * 100 * 0.4), 1)
        profile.last_assessed_at = datetime.now()
        LearningRepository.save_profile(db, profile)

    @staticmethod
    def _refresh_state(db: Session, student_id: int) -> None:
        """刷新统一学习状态（薄弱点 → 状态/前后对比快照）。"""
        try:
            from app.services.learning_state_service import LearningStateEngine

            LearningStateEngine.refresh(db, student_id)
        except Exception:  # noqa: BLE001 - 状态刷新失败不阻塞练习反馈
            pass

    @staticmethod
    def record_step_action(
        db: Session,
        user: User,
        session: LearningSession,
        step_index: int,
        payload: dict,
    ) -> dict:
        """记录某一步的交互并返回即时反馈（不额外调用 LLM，保证离线可用）。"""
        if session.student_id != user.id:
            raise PermissionError("无权操作该会话")
        steps = session.steps or []
        if step_index < 0 or step_index >= len(steps):
            raise ValueError("步骤序号超出范围")

        step = steps[step_index]
        action = str(payload.get("action") or "view")
        answer = payload.get("answer")

        feedback: dict = {"ok": True, "step_index": step_index, "action": action}

        # 练习：答完立即给答案 + 解析 + 对错 + 错因，并回流画像/学习状态
        if action in ("answer", "submit") and step.get("type") == "practice":
            qtype = str(step.get("qtype") or "").lower()
            reference = LearningSessionService._answer_display(step.get("answer"))
            if qtype in {"single", "multiple", "judge"}:
                correct_text = LearningSessionService._correct_option_text(step)
                correct = str(answer).strip().lower() == str(correct_text).strip().lower()
                error_analysis = "" if correct else (step.get("hint") or "再对照题干与选项思考。")
            else:
                correct, error_analysis = LearningSessionService._judge_short_answer(
                    step.get("question") or "", reference, _as_text(answer)
                )
            feedback["correct"] = correct
            feedback["answer"] = reference
            feedback["analysis"] = _as_text(step.get("analysis") or step.get("hint"))
            feedback["error_analysis"] = error_analysis
            feedback["knowledge_points"] = [session.title] if session.title else []
            feedback["message"] = "回答正确" if correct else "回答不正确"
            LearningSessionService._update_profile(db, user.id, session.knowledge_point_id, correct)
            LearningSessionService._refresh_state(db, user.id)
        elif action in ("answer", "submit") and step.get("type") == "check":
            answered = bool(_as_text(answer))
            feedback["message"] = "已记录你的自述。" + (
                "尝试补一个具体例子会更好。" if answered else "先试着写一句，哪怕不完整。"
            )
            feedback["hint"] = "用自己的话复述，能暴露没真正理解的地方。"
        else:
            feedback["message"] = "已记录这一步。"

        session.current_index = max(session.current_index, step_index)
        session.updated_at = datetime.now()
        db.add(session)
        db.add(
            LearningRecord(
                student_id=user.id,
                course_id=session.course_id,
                chapter_id=session.chapter_id,
                knowledge_point_id=session.knowledge_point_id,
                action="session_step",
                detail={
                    "session_id": session.id,
                    "step_index": step_index,
                    "step_type": step.get("type"),
                    "action": action,
                    "answer": answer,
                    "correct": feedback.get("correct"),
                },
            )
        )
        db.commit()
        return feedback

    @staticmethod
    def list_sessions(db: Session, user: User, limit: int = 20) -> list[LearningSession]:
        return (
            db.query(LearningSession)
            .filter(LearningSession.student_id == user.id)
            .order_by(LearningSession.updated_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def complete(db: Session, user: User, session: LearningSession) -> dict:
        if session.student_id != user.id:
            raise PermissionError("无权操作该会话")
        session.status = "completed"
        session.updated_at = datetime.now()
        db.add(session)
        db.commit()
        return {"ok": True, "status": session.status}
