"""课程学习内容生成：课前预习、AI 课程讲堂（快速/标准/深度）。"""

import json
import re

from sqlalchemy.orm import Session

from app.models import Course, CourseChapter, KnowledgePoint, User
from app.services.curriculum_service import CurriculumService
from app.services.llm.factory import get_llm_service
from app.services.rag.factory import get_rag_service
from app.services.ai_meta import ai_meta, references_from_hits
from app.services.curriculum_service import CurriculumService


def _parse_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _kp_payload(kps: list[KnowledgePoint]) -> str:
    return "\n".join(
        f"- {kp.name}（{kp.chapter}）：{kp.description}" for kp in kps
    )


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        title = str(value.get("title") or value.get("name") or value.get("question") or "").strip()
        desc = str(
            value.get("description")
            or value.get("desc")
            or value.get("content")
            or value.get("answer")
            or value.get("answer_hint")
            or ""
        ).strip()
        return f"{title}：{desc}" if title and desc else (title or desc)
    return str(value)


def _normalize_text_list(items) -> list[str]:
    return [x for x in (_as_text(it) for it in (items or [])) if x]


def _normalize_qa_list(items) -> list[dict]:
    """预习题/练习统一为 {question, answer_hint}（兼容 question/answer 等键）。"""
    out = []
    for item in items or []:
        if isinstance(item, str):
            out.append({"question": item, "answer_hint": ""})
        elif isinstance(item, dict):
            out.append(
                {
                    "question": str(item.get("question") or item.get("title") or item.get("name") or ""),
                    "answer_hint": str(
                        item.get("answer_hint")
                        or item.get("answer")
                        or item.get("hint")
                        or item.get("desc")
                        or ""
                    ),
                }
            )
    return out


def generate_preview(db: Session, course: Course, chapter: CourseChapter, student: User) -> dict:
    kps = (
        db.query(KnowledgePoint).filter(KnowledgePoint.chapter_id == chapter.id).all()
    )
    rag = get_rag_service()
    hits = rag.search(
        db,
        f"{course.name} {chapter.title}",
        top_k=4,
        course_id=course.id,
        source_levels=["S"],
    )
    context = "\n".join(f"- {h.document_title}：{h.text[:150]}" for h in hits)
    prompt = (
        f"为课程《{course.name}》第{chapter.order}章「{chapter.title}」生成课前预习内容。\n"
        f"章节概述：{chapter.summary}\n知识点：\n{_kp_payload(kps)}\n"
        f"官方资料参考：\n{context}\n"
        "请输出 JSON，字段：objectives（学习目标数组）、prerequisites（预备知识数组）、"
        "core_concepts（核心概念数组）、materials（预习材料数组）、pre_questions（1-3 道预习题，每项含 question 与 answer_hint）、"
        "check（学习检查：3 个自测问题数组）。"
    )
    raw = get_llm_service().generate(prompt, system="你是高校计算机学科课前预习生成助手，输出 JSON。")
    parsed = _parse_json(raw)
    fallback = {
        "objectives": [f"理解「{chapter.title}」的核心概念" for _ in kps[:3]] or [f"理解{chapter.title}"],
        "prerequisites": [p for kp in kps for p in (kp.prerequisites or [])][:4],
        "core_concepts": [kp.name for kp in kps],
        "materials": [h.document_title for h in hits] or ["课程讲义"],
        "pre_questions": [{"question": f"「{kp.name}」主要解决什么问题？", "answer_hint": kp.description[:60]} for kp in kps[:3]],
        "check": [f"能否用自己的话解释「{kp.name}」？" for kp in kps[:3]],
    }
    for key in fallback:
        if not parsed.get(key):
            parsed[key] = fallback[key]
    parsed["objectives"] = _normalize_text_list(parsed.get("objectives"))
    parsed["prerequisites"] = _normalize_text_list(parsed.get("prerequisites"))
    parsed["core_concepts"] = _normalize_text_list(parsed.get("core_concepts"))
    parsed["materials"] = _normalize_text_list(parsed.get("materials"))
    parsed["check"] = _normalize_text_list(parsed.get("check"))
    parsed["pre_questions"] = _normalize_qa_list(parsed.get("pre_questions"))
    parsed.update(ai_meta(get_llm_service().name, references_from_hits(hits)))
    return parsed


def generate_lecture(db: Session, course: Course, chapter: CourseChapter, depth: str, student: User) -> dict:
    kps = db.query(KnowledgePoint).filter(KnowledgePoint.chapter_id == chapter.id).all()
    rag = get_rag_service()
    hits = rag.search(
        db,
        f"{course.name} {chapter.title}",
        top_k=5,
        course_id=course.id,
        source_levels=["S", "A"],
    )
    context = "\n".join(
        f"[{h.metadata.get('source_level', 'S')}] {h.document_title}：{h.text[:200]}"
        for h in hits
    )
    depth_desc = {
        "quick": "快速讲解：要点式，控制在 8 个节内",
        "standard": "标准课程：结构化分节，每节含讲解与举例",
        "deep": "深度讲解：接近完整授课，含推导、易错点与互动练习",
    }.get(depth, "标准课程")
    prompt = (
        f"为《{course.name}》第{chapter.order}章「{chapter.title}」生成{depth_desc}。\n"
        f"知识点：\n{_kp_payload(kps)}\n官方资料参考：\n{context}\n"
        "请输出 JSON，字段：learning_goals（学习目标数组）、sections（章节内容数组，每项含 title 与 content，"
        "以及可选的 example/code 字段）、common_errors（常见错误数组）、exercises（随堂练习数组，每项含 question 与 answer_hint）、"
        "check（理解检查问题数组）。"
    )
    raw = get_llm_service().generate(prompt, system="你是高校计算机学科 AI 课程讲堂讲师，输出 JSON。")
    parsed = _parse_json(raw)
    if not parsed.get("sections"):
        parsed["sections"] = [
            {
                "title": f"认识「{kp.name}」",
                "content": kp.description,
                "example": f"以「{kp.name}」为例说明其应用场景",
            }
            for kp in kps
        ]
    if not parsed.get("learning_goals"):
        parsed["learning_goals"] = [f"掌握「{kp.name}」" for kp in kps]
    if not parsed.get("common_errors"):
        parsed["common_errors"] = [f"混淆「{kp.name}」的适用条件与边界" for kp in kps[:3]]
    if not parsed.get("exercises"):
        parsed["exercises"] = [{"question": f"用一句话说明「{kp.name}」的核心思想", "answer_hint": kp.description[:50]} for kp in kps[:3]]
    if not parsed.get("check"):
        parsed["check"] = [f"「{kp.name}」为什么重要？" for kp in kps[:3]]
    parsed["learning_goals"] = _normalize_text_list(parsed.get("learning_goals"))
    parsed["common_errors"] = _normalize_text_list(parsed.get("common_errors"))
    parsed["check"] = _normalize_text_list(parsed.get("check"))
    parsed["exercises"] = _normalize_qa_list(parsed.get("exercises"))
    parsed["sections"] = [
        {
            "title": _as_text(s.get("title") if isinstance(s, dict) else s),
            "content": _as_text(s.get("content") if isinstance(s, dict) else s),
            "example": _as_text(s.get("example")) if isinstance(s, dict) else "",
            "code": _as_text(s.get("code")) if isinstance(s, dict) else "",
        }
        for s in (parsed.get("sections") or [])
    ]
    parsed["depth"] = depth
    parsed.update(ai_meta(get_llm_service().name, references_from_hits(hits)))
    return parsed


def generate_review(db: Session, course: Course, chapter: CourseChapter, student: User) -> dict:
    """课后复习包：本章总结、知识结构、薄弱点诊断与强化练习（带引用与 AI 标签）。"""
    view = CurriculumService.chapter_view(db, student.id, chapter.id)
    kps = view.get("knowledge_points", [])
    weak = view.get("weak_points", [])
    errors = view.get("errors", [])
    rag = get_rag_service()
    hits = rag.search(
        db,
        f"{course.name} {chapter.title} 复习",
        top_k=4,
        course_id=course.id,
        source_levels=["S", "A"],
    )
    context = "\n".join(
        f"[{h.metadata.get('source_level', 'S')}] {h.document_title}：{h.text[:200]}"
        for h in hits
    )
    weak_text = "\n".join(f"- {w['name']}（掌握度 {w['mastery']}%）" for w in weak[:5]) or "（无）"
    errors_text = "\n".join(f"- {e['knowledge_point']}（错误 {e['errors']} 次）" for e in errors[:5]) or "（无）"
    prompt = (
        f"为《{course.name}》第{chapter.order}章「{chapter.title}」生成课后复习包。\n"
        f"本章知识点：{_kp_payload(kps)}\n我的薄弱点：\n{weak_text}\n我的错题：\n{errors_text}\n"
        f"官方资料参考：\n{context}\n"
        "请输出 JSON，字段：summary（本章总结段落）、key_points（复习要点数组）、"
        "weak_plan（薄弱点复习计划数组，每项含 kp/reason/action）、"
        "exercises（强化练习数组，每项含 question/answer_hint）、next_steps（下一步建议数组）。"
    )
    raw = get_llm_service().generate(prompt, system="你是高校计算机学科课后复习辅导助手，输出 JSON。")
    parsed = _parse_json(raw)
    fallback = {
        "summary": chapter.summary,
        "key_points": [kp["name"] for kp in kps],
        "weak_plan": [
            {"kp": w["name"], "reason": f"掌握度 {w['mastery']}%", "action": "重读讲义对应小节并完成强化练习"}
            for w in weak[:4]
        ],
        "exercises": [
            {"question": f"用自己的话解释「{kp['name']}」并给出一个例子", "answer_hint": kp.get("description", "")}
            for kp in kps[:3]
        ],
        "next_steps": ["完成章节测验", "重做错题", "预习下一章节"],
    }
    for key in fallback:
        if not parsed.get(key):
            parsed[key] = fallback[key]
    parsed["summary"] = _as_text(parsed.get("summary"))
    parsed["key_points"] = _normalize_text_list(parsed.get("key_points"))
    parsed["next_steps"] = _normalize_text_list(parsed.get("next_steps"))
    parsed["weak_plan"] = [
        {
            "kp": _as_text(item.get("kp") if isinstance(item, dict) else item),
            "reason": _as_text(item.get("reason") if isinstance(item, dict) else ""),
            "action": _as_text(item.get("action") if isinstance(item, dict) else ""),
        }
        for item in (parsed.get("weak_plan") or [])
    ]
    parsed["exercises"] = _normalize_qa_list(parsed.get("exercises"))
    parsed["knowledge_points"] = kps
    parsed["weak_points"] = weak
    parsed["errors"] = errors
    parsed.update(ai_meta(get_llm_service().name, references_from_hits(hits), source="review"))
    return parsed
