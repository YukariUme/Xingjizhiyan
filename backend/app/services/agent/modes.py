"""分模式 Agent：预习 / 讲堂 / 复习 / 模拟考试 / 教学诊断（配合工作流编排）。"""

from sqlalchemy.orm import Session

from app.models import Course, CourseChapter, User
from app.services.ai_meta import ai_meta, references_from_hits
from app.services.agent.base import AgentService
from app.services.curriculum_service import CurriculumService
from app.services.quiz_service import build_quiz, submit_quiz
from app.services.rag.factory import get_rag_service
from app.services.teaching_content_service import (
    generate_lecture,
    generate_preview,
    generate_review,
)


class PreviewAgent(AgentService):
    name = "preview"

    def run(self, db: Session, user: User, payload: dict) -> dict:
        course = db.get(Course, int(payload["course_id"]))
        chapter = db.get(CourseChapter, int(payload["chapter_id"]))
        content = generate_preview(db, course, chapter, user)
        CurriculumService.record(
            db, user.id, "preview", course_id=course.id, chapter_id=chapter.id,
            detail={"title": chapter.title},
        )
        return content


class LectureAgent(AgentService):
    name = "lecture"

    def run(self, db: Session, user: User, payload: dict) -> dict:
        chapter = db.get(CourseChapter, int(payload["chapter_id"]))
        course = db.get(Course, chapter.course_id)
        depth = payload.get("depth", "standard")
        content = generate_lecture(db, course, chapter, depth, user)
        CurriculumService.record(
            db, user.id, "lecture", course_id=course.id, chapter_id=chapter.id,
            detail={"title": chapter.title, "depth": depth},
        )
        return content


class ReviewAgent(AgentService):
    name = "review"

    def run(self, db: Session, user: User, payload: dict) -> dict:
        chapter = db.get(CourseChapter, int(payload["chapter_id"]))
        course = db.get(Course, chapter.course_id)
        content = generate_review(db, course, chapter, user)
        CurriculumService.record(
            db, user.id, "review", course_id=course.id, chapter_id=chapter.id,
            detail={"title": chapter.title},
        )
        return content


class ExamAgent(AgentService):
    """模拟考试 Agent：build（生成试卷）与 grade（评分+画像+建议）两个任务。"""

    name = "exam"

    def run(self, db: Session, user: User, payload: dict) -> dict:
        task = payload.get("task", "build")
        if task == "grade":
            return self.grade(db, user, payload)
        return self.build(db, user, payload)

    def build(self, db: Session, user: User, payload: dict) -> dict:
        course_id = int(payload["course_id"])
        course = db.get(Course, course_id)
        chapter_id = int(payload["chapter_id"]) if payload.get("chapter_id") else None
        quiz = build_quiz(
            db,
            course_id,
            user,
            quiz_type=payload.get("quiz_type", "chapter"),
            chapter_id=chapter_id,
            scope_kp_ids=payload.get("scope_kp_ids"),
        )
        chapter = db.get(CourseChapter, chapter_id) if chapter_id else None
        hits = get_rag_service().search(
            db,
            f"{course.name if course else ''} {chapter.title if chapter else ''} 测验",
            top_k=4,
            course_id=course_id,
            source_levels=["S", "A"],
        )
        from app.models import QuizQuestion

        questions = (
            db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.order).all()
        )
        result = {
            "quiz_id": quiz.id,
            "title": quiz.title,
            "quiz_type": quiz.quiz_type,
            "questions": [
                {
                    "question_id": q.id,
                    "qtype": q.qtype,
                    "title": q.title,
                    "options": q.options,
                    "max_score": q.max_score,
                }
                for q in questions
            ],
        }
        result.update(ai_meta("quiz-engine", references_from_hits(hits), source="quiz"))
        return result

    def grade(self, db: Session, user: User, payload: dict) -> dict:
        result = submit_quiz(db, int(payload["quiz_id"]), user, payload.get("answers", []))
        quiz = db.get(__import__("app.models", fromlist=["Quiz"]).Quiz, int(payload["quiz_id"]))
        hits = (
            get_rag_service().search(
                db,
                f"{quiz.title} 复习建议",
                top_k=4,
                course_id=quiz.course_id,
                source_levels=["S", "A"],
            )
            if quiz
            else []
        )
        result.update(ai_meta("quiz-engine", references_from_hits(hits), source="quiz"))
        CurriculumService.record(
            db, user.id, "exam", course_id=quiz.course_id if quiz else None,
            chapter_id=quiz.chapter_id if quiz else None,
            detail={"quiz_id": payload.get("quiz_id"), "score": result.get("score")},
        )
        return result


class DiagnoseAgent(AgentService):
    name = "diagnose"

    def run(self, db: Session, user: User, payload: dict) -> dict:
        import json
        import re

        from app.services.analytics_service import AnalyticsService

        course_id = int(payload["course_id"])
        course = db.get(Course, course_id)
        data = AnalyticsService.class_analytics(db, course_id)
        high_freq = "\n".join(
            f"- {k['name']}（正确率 {k['accuracy']}%）" for k in data.get("high_frequency_errors", [])[:5]
        )
        weak = "\n".join(f"- {w}" for w in data.get("weak_points", [])[:5])
        prompt = (
            f"[教学诊断任务]\n课程：{data.get('course_name', '')}\n"
            f"平均正确率：{data.get('avg_accuracy', 0)}%\n高频错误：\n{high_freq or '（无）'}\n薄弱知识点：\n{weak or '（无）'}\n"
            "请输出 JSON，字段：findings（每项 issue/evidence/reason）、suggestions（每项 title/detail）、"
            "next_lesson（数组）、materials（数组）。"
        )
        raw = self.llm.generate(prompt, system="你是高校计算机学科教学诊断专家，输出 JSON。")
        match = re.search(r"\{.*\}", raw, re.S)
        parsed = {}
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                parsed = {}
        if not parsed.get("suggestions"):
            parsed = {
                "findings": [
                    {
                        "issue": f"高频错误：{data['high_frequency_errors'][0]['name'] if data.get('high_frequency_errors') else '无'}",
                        "evidence": "来自作业/评测数据",
                        "reason": "建议重点讲解",
                    }
                ],
                "suggestions": [{"title": "针对薄弱知识点补充讲解与练习", "detail": "下一节课增加概念对比与代码实验。"}],
                "next_lesson": data.get("weak_points", []),
                "materials": ["章节讲义", "典型例题"],
            }
        # 归一化：LLM 可能把 issue/detail 等返回成对象，统一转字符串
        from app.services.agent.teaching import _as_text, _normalize_text_list

        parsed["findings"] = [
            {
                "issue": _as_text(f.get("issue") if isinstance(f, dict) else f),
                "evidence": _as_text(f.get("evidence") if isinstance(f, dict) else ""),
                "reason": _as_text(f.get("reason") if isinstance(f, dict) else ""),
            }
            for f in parsed.get("findings") or []
            if isinstance(f, dict) and _as_text(f.get("issue"))
        ]
        parsed["suggestions"] = [
            {
                "title": _as_text(s.get("title") if isinstance(s, dict) else s),
                "detail": _as_text(s.get("detail") if isinstance(s, dict) else ""),
            }
            for s in parsed.get("suggestions") or []
            if _as_text(s.get("title") if isinstance(s, dict) else s)
        ]
        parsed["next_lesson"] = _normalize_text_list(parsed.get("next_lesson"))
        parsed["materials"] = _normalize_text_list(parsed.get("materials"))
        hits = get_rag_service().search(
            db, f"{data.get('course_name', '')} 教学诊断", top_k=4, course_id=course_id, source_levels=["S"]
        )
        parsed.update(ai_meta(self.llm.name, references_from_hits(hits), source="diagnose"))
        return {"analytics": data, "diagnosis": parsed}
