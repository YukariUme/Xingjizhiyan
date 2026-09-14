"""AI 辅助批改服务：AI 建议 → 教师审核 → 正式成绩。"""

from sqlalchemy.orm import Session

from app.models import (
    Activity,
    Evaluation,
    Question,
    Submission,
    SubjectiveSubmission,
    User,
)
from app.repositories.learning_repo import LearningRepository
from app.services.analytics_service import AnalyticsService
from app.database import utcnow


class GradingService:
    def __init__(self, llm, rag, prompts) -> None:
        self.llm = llm
        self.rag = rag
        self.prompts = prompts

    def ai_review(self, db: Session, submission: Submission) -> SubjectiveSubmission | None:
        """AI 分析主观题：生成建议分、理由、知识点、错误与改进建议。"""
        if submission.qtype == "programming":
            return None
        subj = submission.subjective
        if not subj:
            return None
        question = db.get(Question, submission.question_id)
        rubric = self._rubric_for(question)
        context = self.rag_search_context(db, question)
        system, prompt = self.prompts.grade_subjective(
            {
                "title": question.title if question else "",
                "description": question.description if question else "",
                "max_score": question.max_score if question else 10,
            },
            subj.content,
            rubric,
            context,
        )
        raw = self.llm.generate(prompt, system=system)
        parsed = self._parse_review(raw, question.max_score if question else 10)
        subj.ai_suggestion_score = parsed["suggestion_score"]
        subj.ai_reasoning = parsed["reasoning"]
        subj.ai_knowledge_points = parsed["knowledge_points"]
        subj.ai_error_analysis = _errors_to_text(parsed["errors"])
        subj.ai_improvement = parsed["improvement"]
        submission.status = "under_review"
        db.add(subj)
        db.add(submission)
        db.commit()
        return subj

    def teacher_review(
        self,
        db: Session,
        submission: Submission,
        final_score: float,
        comment: str,
        teacher: User,
    ) -> Submission:
        """教师确认最终分数与评语，成绩对学生可见。"""
        subj = submission.subjective
        if subj:
            subj.teacher_score = final_score
            subj.teacher_comment = comment
            subj.graded_at = utcnow()
            db.add(subj)
        submission.status = "graded"
        db.add(submission)
        db.add(
            Evaluation(
                submission_id=submission.id,
                source="teacher",
                score=final_score,
                comment=comment,
            )
        )
        db.commit()
        question = db.get(Question, submission.question_id)
        # 回写学习画像：批改结果进入学情分析
        AnalyticsService.update_profile_from_result(
            db,
            student_id=submission.student_id,
            question=question,
            correct=final_score >= (question.max_score * 0.6 if question else 0),
            score=final_score,
        )
        db.add(
            Activity(
                user_id=teacher.id,
                role=teacher.role,
                kind="grade_confirm",
                title=f"确认作业成绩：{final_score} 分",
                detail={"submission_id": submission.id},
            )
        )
        db.commit()
        AnalyticsService.refresh_student_learning_state(db, submission.student_id)
        return submission

    def rag_search_context(self, db: Session, question: Question | None) -> str:
        if not question:
            return ""
        results = self.rag.search(db, f"{question.title} {question.description}", top_k=3)
        return "\n\n".join(f"- {r.document_title}：{r.text[:180]}" for r in results)

    @staticmethod
    def _rubric_for(question: Question | None) -> list[str]:
        if not question:
            return []
        return [
            "概念定义准确",
            "要点覆盖完整",
            "论述有例证支持",
            "结论清晰",
        ]

    @staticmethod
    def _parse_review(raw: str, max_score: float) -> dict:
        import json
        import re

        from app.services.agent.teaching import _as_text, _normalize_text_list

        m = re.search(r"\{.*\}", raw, re.S)
        parsed = {}
        if m:
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                parsed = {}
        try:
            score = min(max_score, float(parsed.get("suggestion_score", max_score * 0.7)))
        except (TypeError, ValueError):
            score = max_score * 0.7
        return {
            "suggestion_score": round(score, 1),
            "reasoning": _as_text(parsed.get("reasoning")) or "AI 已分析作答内容。",
            "knowledge_points": _normalize_text_list(parsed.get("knowledge_points")),
            "errors": parsed.get("errors", []),
            "improvement": _as_text(parsed.get("improvement")),
        }


def _errors_to_text(errors: list | str) -> str:
    """错误列表转文本（兼容文本列存储）。"""
    if isinstance(errors, str):
        return errors
    if not errors:
        return ""
    from app.services.agent.teaching import _as_text

    return "\n".join(f"{i + 1}. {_as_text(e)}" for i, e in enumerate(errors) if _as_text(e))
