"""统一学习状态引擎：把画像、行为、答疑、测验和作业信号收敛成可读状态。"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Course,
    KnowledgePoint,
    LearningProgressComparison,
    LearningRecord,
    Question,
    StudentKnowledgeProfile,
    StudentLearningState,
    Submission,
)
from app.repositories.learning_repo import LearningRepository


class LearningStateEngine:
    """规则型学习状态机。"""

    STATE_ORDER = {
        "STRUGGLING": 0,
        "REVIEW": 1,
        "STABLE": 2,
        "STRONG": 3,
    }

    @staticmethod
    def refresh(db: Session, student_id: int) -> list[StudentLearningState]:
        """重算并落库学生学习状态，同时写入前后对比快照。"""
        from app.services.analytics_service import AnalyticsService

        profiles = LearningRepository.list_profiles(db, student_id)
        if not profiles:
            return []

        behavior = AnalyticsService.recent_behavior_window(db, student_id, profiles)
        recent_records = behavior["recent_records"]
        recent_messages = behavior["recent_messages"]
        recent_wrong_submissions = behavior["recent_wrong_submissions"]

        topic_counter: Counter[str] = Counter()
        for msg in recent_messages:
            for topic in msg.knowledge_points or []:
                topic_counter[str(topic)] += 2

        states: list[StudentLearningState] = []
        comparisons: list[LearningProgressComparison] = []

        for profile in profiles:
            kp = db.get(KnowledgePoint, profile.knowledge_point_id)
            if not kp:
                continue
            course = db.query(Course).filter(Course.name == kp.subject).first()
            if not course:
                continue

            state = db.scalar(
                select(StudentLearningState).where(
                    StudentLearningState.student_id == student_id,
                    StudentLearningState.course_id == course.id,
                    StudentLearningState.knowledge_point_id == profile.knowledge_point_id,
                )
            )
            if not state:
                state = StudentLearningState(
                    student_id=student_id,
                    course_id=course.id,
                    knowledge_point_id=profile.knowledge_point_id,
                )

            before_mastery = float(state.mastery_score or 0.0)
            before_state = state.state or ""

            recent_question_count = int(topic_counter.get(kp.name, 0))
            related_kp_ids = {int(profile.knowledge_point_id)}
            recent_error_count = 0
            consecutive_error_count = 0
            for item in recent_wrong_submissions:
                ids = [int(x) for x in item.get("knowledge_point_ids", [])]
                if related_kp_ids.intersection(ids):
                    recent_error_count += 1
                    consecutive_error_count += 1
                elif consecutive_error_count > 0:
                    break

            last_learning_at = LearningStateEngine._latest_record_time(
                recent_records, profile.knowledge_point_id
            )
            last_assessment_at = LearningStateEngine._latest_submission_time(
                db, student_id, profile.knowledge_point_id
            )

            mastery = float(profile.mastery or 0.0)
            attempts = max(1, int(profile.attempts or 0))
            errors = int(profile.errors or 0)
            success_count = int(profile.success_count or max(0, attempts - errors))
            confidence = round(
                min(
                    0.98,
                    max(
                        0.05,
                        0.35
                        + mastery / 100 * 0.35
                        + (success_count / attempts) * 0.2
                        + max(0, 3 - consecutive_error_count) / 3 * 0.1,
                    ),
                ),
                3,
            )
            stability = round(
                max(
                    0.0,
                    min(
                        1.0,
                        mastery / 100 * 0.5
                        + (success_count / attempts) * 0.25
                        + max(0, 3 - consecutive_error_count) / 3 * 0.15
                        + max(0, 2 - recent_error_count) / 2 * 0.1,
                    ),
                ),
                3,
            )
            state_name, state_reason = LearningStateEngine._resolve_state(
                kp.name,
                mastery,
                recent_question_count,
                recent_error_count,
                consecutive_error_count,
                behavior["short_sessions"],
                behavior["avg_session_sec"],
                behavior["last_answer_duration_sec"],
                behavior["wrong_streak"],
            )

            state.mastery_score = mastery
            state.confidence = confidence
            state.error_count = errors
            state.recent_error_count = recent_error_count
            state.consecutive_error_count = consecutive_error_count
            state.success_count = success_count
            state.last_learning_at = last_learning_at
            state.last_assessment_at = last_assessment_at
            state.recent_question_count = recent_question_count
            state.learning_stability = stability
            state.state = state_name
            state.state_reason = state_reason
            db.add(state)
            states.append(state)

            if before_state or before_mastery:
                changed = (
                    before_state != state_name
                    or abs(before_mastery - mastery) >= 0.1
                    or state.recent_error_count != recent_error_count
                    or state.consecutive_error_count != consecutive_error_count
                )
                if changed:
                    comparisons.append(
                        LearningProgressComparison(
                            student_id=student_id,
                            course_id=course.id,
                            knowledge_point_id=profile.knowledge_point_id,
                            before_mastery=before_mastery,
                            after_mastery=mastery,
                            before_state=before_state,
                            after_state=state_name,
                            interventions=[
                                state_reason,
                                f"最近连续错题 {consecutive_error_count} 次",
                                f"最近 7 天学习记录 {behavior['record_count_7d']} 条",
                            ],
                            evidence={
                                "reason": state_reason,
                                "recent_question_count": recent_question_count,
                                "recent_error_count": recent_error_count,
                                "consecutive_error_count": consecutive_error_count,
                                "avg_session_sec": behavior["avg_session_sec"],
                                "short_sessions": behavior["short_sessions"],
                                "record_count_7d": behavior["record_count_7d"],
                            },
                        )
                    )

        db.flush()
        if comparisons:
            db.add_all(comparisons)
        db.commit()
        return sorted(
            states,
            key=lambda s: (LearningStateEngine.STATE_ORDER.get(s.state, 99), -(s.mastery_score or 0)),
        )

    @staticmethod
    def list_states(db: Session, student_id: int) -> list[StudentLearningState]:
        return list(
            db.scalars(
                select(StudentLearningState)
                .where(StudentLearningState.student_id == student_id)
                .order_by(StudentLearningState.mastery_score.asc(), StudentLearningState.updated_at.desc())
            )
        )

    @staticmethod
    def list_comparisons(db: Session, student_id: int, limit: int = 20) -> list[LearningProgressComparison]:
        return list(
            db.scalars(
                select(LearningProgressComparison)
                .where(LearningProgressComparison.student_id == student_id)
                .order_by(LearningProgressComparison.created_at.desc())
                .limit(limit)
            )
        )

    @staticmethod
    def serialize_state(db: Session, state: StudentLearningState) -> dict:
        kp = db.get(KnowledgePoint, state.knowledge_point_id)
        return {
            "id": state.id,
            "student_id": state.student_id,
            "course_id": state.course_id,
            "knowledge_point_id": state.knowledge_point_id,
            "knowledge_point": kp.name if kp else f"知识点 {state.knowledge_point_id}",
            "subject": kp.subject if kp else "",
            "mastery_score": state.mastery_score,
            "confidence": state.confidence,
            "error_count": state.error_count,
            "recent_error_count": state.recent_error_count,
            "consecutive_error_count": state.consecutive_error_count,
            "success_count": state.success_count,
            "last_learning_at": state.last_learning_at.isoformat() if state.last_learning_at else None,
            "last_assessment_at": state.last_assessment_at.isoformat() if state.last_assessment_at else None,
            "recent_question_count": state.recent_question_count,
            "learning_stability": state.learning_stability,
            "state": state.state,
            "state_reason": state.state_reason,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        }

    @staticmethod
    def serialize_comparison(db: Session, item: LearningProgressComparison) -> dict:
        kp = db.get(KnowledgePoint, item.knowledge_point_id) if item.knowledge_point_id else None
        return {
            "id": item.id,
            "student_id": item.student_id,
            "course_id": item.course_id,
            "knowledge_point_id": item.knowledge_point_id,
            "knowledge_point": kp.name if kp else "",
            "before_mastery": item.before_mastery,
            "after_mastery": item.after_mastery,
            "before_state": item.before_state,
            "after_state": item.after_state,
            "interventions": item.interventions or [],
            "evidence": item.evidence or {},
            "is_demo": item.is_demo,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }

    @staticmethod
    def _resolve_state(
        kp_name: str,
        mastery: float,
        recent_question_count: int,
        recent_error_count: int,
        consecutive_error_count: int,
        short_sessions: int,
        avg_session_sec: float,
        last_answer_duration_sec: int,
        wrong_streak: int,
    ) -> tuple[str, str]:
        if consecutive_error_count >= 3 or wrong_streak >= 3:
            return (
                "STRUGGLING",
                f"「{kp_name}」最近连续错题较多，建议先回看讲义与错因，再做同类题。",
            )
        if mastery < 45 or (mastery < 60 and recent_error_count >= 2):
            reason = f"「{kp_name}」当前掌握度 {mastery:.0f}%，最近仍有错题，建议进入复习模式。"
            if recent_question_count >= 2:
                reason += f" 该知识点最近被提问 {recent_question_count} 次。"
            return "REVIEW", reason
        if recent_question_count >= 2 or short_sessions >= 2 or last_answer_duration_sec < 120:
            return (
                "REVIEW",
                f"「{kp_name}」最近被频繁提问或多次短时学习，建议趁热复盘并补一次完整练习。",
            )
        if mastery >= 85 and recent_error_count == 0:
            return (
                "STRONG",
                f"「{kp_name}」掌握度较高，最近无明显错误，可以进入进阶阅读或扩展练习。",
            )
        return (
            "STABLE",
            f"「{kp_name}」当前处于稳定学习状态，平均每次学习 {avg_session_sec:.0f} 秒，适合按计划继续推进。",
        )

    @staticmethod
    def _latest_record_time(recent_records: list[LearningRecord], kp_id: int) -> datetime | None:
        times = [r.created_at for r in recent_records if r.knowledge_point_id == kp_id and r.created_at]
        return max(times) if times else None

    @staticmethod
    def _latest_submission_time(db: Session, student_id: int, kp_id: int) -> datetime | None:
        submissions = (
            db.query(Submission)
            .filter(Submission.student_id == student_id)
            .order_by(Submission.updated_at.desc(), Submission.created_at.desc())
            .limit(30)
            .all()
        )
        latest: datetime | None = None
        for sub in submissions:
            question = db.get(Question, sub.question_id)
            if not question or kp_id not in (question.knowledge_point_ids or []):
                continue
            moment = sub.updated_at or sub.created_at
            if moment and (latest is None or moment > latest):
                latest = moment
        return latest
