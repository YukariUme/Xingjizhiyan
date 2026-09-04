"""TeachingAgent：教师备课 Agent。"""

import json
import re

from sqlalchemy.orm import Session

from app.models import LessonPlan, User
from app.repositories.activity_repo import ActivityRepository
from app.repositories.course_repo import CourseRepository
from app.services.agent.base import AgentService


def _parse_json(raw: str) -> dict:
    """宽容解析 LLM 返回的 JSON。"""
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def _as_text(value, _depth: int = 0) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [_as_text(item, _depth + 1) for item in value]
        return "\n".join(f"- {p}" for p in parts if p)
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if item is None:
                continue
            text = _as_text(item, _depth + 1)
            if text:
                lines.append(f"{key}：{text}")
        return "；".join(lines)
    return str(value)


def _normalize_text_list(items) -> list[str]:
    out: list[str] = []
    for item in items or []:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            title = str(item.get("title") or item.get("name") or "").strip()
            desc = str(
                item.get("description") or item.get("desc") or item.get("content") or ""
            ).strip()
            out.append(f"{title}：{desc}" if title and desc else (title or desc))
        else:
            out.append(str(item))
    return [x for x in out if x]


def _normalize_exercises(items) -> list[dict]:
    out: list[dict] = []
    for item in items or []:
        if isinstance(item, str):
            out.append({"title": item, "desc": ""})
        elif isinstance(item, dict):
            out.append(
                {
                    "title": str(item.get("title") or item.get("name") or ""),
                    "desc": str(
                        item.get("desc") or item.get("description") or item.get("content") or ""
                    ),
                }
            )
        else:
            out.append({"title": str(item), "desc": ""})
    return out


def _normalize_flow(items) -> list[dict]:
    out: list[dict] = []
    for item in items or []:
        if isinstance(item, dict):
            out.append(
                {
                    "step": str(item.get("step") or item.get("name") or item.get("title") or ""),
                    "content": str(item.get("content") or item.get("desc") or item.get("description") or ""),
                }
            )
        elif isinstance(item, str):
            out.append({"step": "", "content": item})
    return out


class TeachingAgent(AgentService):
    name = "teaching"

    def run(self, db: Session, user: User, payload: dict) -> dict:
        course = payload.get("course", "")
        chapter = payload.get("chapter", "")
        topic = payload.get("topic", "")
        context = self._knowledge_context(db, course, topic)
        system, prompt = self.prompts.lesson_plan(payload, context)
        raw = self.llm.generate(prompt, system=system)
        parsed = _parse_json(raw)
        if not parsed:
            parsed = self._fallback(payload)

        plan = LessonPlan(
            teacher_id=user.id,
            course=course,
            chapter=chapter,
            topic=topic,
            grade=payload.get("grade", ""),
            objectives=_as_text(parsed.get("objectives", "")),
            knowledge_points=_normalize_text_list(parsed.get("knowledge_points")),
            key_points=_normalize_text_list(parsed.get("key_points")),
            difficulties=_normalize_text_list(parsed.get("difficulties")),
            flow=_normalize_flow(parsed.get("flow")),
            cases=_normalize_text_list(parsed.get("cases")),
            exercises=_normalize_exercises(parsed.get("exercises")),
            homework=_normalize_text_list(parsed.get("homework")),
        )
        saved = CourseRepository.save_lesson_plan(db, plan)
        ActivityRepository.add(
            db,
            _activity(
                user=user,
                kind="lesson_plan",
                title=f"生成教案：{course} · {topic}",
                detail={"course": course, "chapter": chapter, "topic": topic},
            ),
        )
        return {
            "id": saved.id,
            "teacher_id": saved.teacher_id,
            "course": saved.course,
            "chapter": saved.chapter,
            "topic": saved.topic,
            "grade": saved.grade,
            "objectives": saved.objectives,
            "knowledge_points": saved.knowledge_points,
            "key_points": saved.key_points,
            "difficulties": saved.difficulties,
            "flow": saved.flow,
            "cases": saved.cases,
            "exercises": saved.exercises,
            "homework": saved.homework,
            "created_at": saved.created_at.isoformat(),
            "provider": self.llm.name,
        }

    def _knowledge_context(self, db: Session, course: str, topic: str) -> str:
        results = self.rag.search(db, f"{course} {topic}", top_k=4, course=course)
        return "\n\n".join(f"- {r.document_title}：{r.text[:180]}" for r in results)

    @staticmethod
    def _fallback(payload: dict) -> dict:
        topic = payload.get("topic", "本主题")
        return {
            "objectives": f"理解并掌握「{topic}」的核心概念与应用方法。",
            "knowledge_points": [topic, f"{topic}的典型实现", f"{topic}的工程应用"],
            "key_points": [f"{topic}定义与性质"],
            "difficulties": [f"{topic}的综合运用"],
            "flow": [
                {"step": "导入", "content": "案例导入，引出主题"},
                {"step": "讲授", "content": f"讲解{topic}核心内容"},
                {"step": "练习", "content": "随堂练习与反馈"},
            ],
            "cases": [],
            "exercises": [],
            "homework": [],
        }


def _activity(user: User, kind: str, title: str, detail: dict):
    from app.models import Activity

    return Activity(user_id=user.id, role=user.role, kind=kind, title=title, detail=detail)
