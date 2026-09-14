"""学情分析服务：班级统计、学生画像更新与个性化路径。"""

from collections import Counter
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import utcnow
from app.models import (
    Assignment,
    ChatMessage,
    KnowledgePoint,
    LearningRecord,
    Question,
    StudentKnowledgeProfile,
    Submission,
    User,
)
from app.repositories.course_repo import CourseRepository
from app.repositories.learning_repo import LearningRepository
from app.repositories.submission_repo import SubmissionRepository


class AnalyticsService:
    @staticmethod
    def _collect_texts(value) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (int, float, bool)):
            return [str(value)]
        if isinstance(value, list):
            texts: list[str] = []
            for item in value:
                texts.extend(AnalyticsService._collect_texts(item))
            return texts
        if isinstance(value, dict):
            texts: list[str] = []
            for item in value.values():
                texts.extend(AnalyticsService._collect_texts(item))
            return texts
        return [str(value)]

    @staticmethod
    def recent_behavior_window(
        db: Session,
        student_id: int,
        profiles,
        days: int = 7,
        record_limit: int = 24,
        message_limit: int = 16,
        submission_limit: int = 12,
    ) -> dict:
        """提取最近学习行为窗口：作答、错题、答疑主题与学习节奏。"""
        cutoff = utcnow() - timedelta(days=days)
        recent_records = (
            db.query(LearningRecord)
            .filter(
                LearningRecord.student_id == student_id,
                LearningRecord.created_at >= cutoff,
            )
            .order_by(LearningRecord.created_at.desc())
            .limit(record_limit)
            .all()
        )
        recent_messages = LearningRepository.list_messages(db, student_id, "learning", limit=message_limit)
        recent_submissions = (
            db.query(Submission)
            .filter(Submission.student_id == student_id)
            .order_by(Submission.updated_at.desc(), Submission.created_at.desc())
            .limit(submission_limit)
            .all()
        )

        kp_by_id = {
            p.knowledge_point_id: db.get(KnowledgePoint, p.knowledge_point_id)
            for p in profiles
        }
        kp_names = [kp.name for kp in kp_by_id.values() if kp]
        topic_counts: Counter[str] = Counter()
        chapter_counts: Counter[int] = Counter()
        action_counts: Counter[str] = Counter()
        wrong_point_counts: Counter[int] = Counter()
        wrong_submissions: list[dict] = []
        active_days: set[str] = set()
        timed_records = 0
        total_duration_sec = 0
        short_sessions = 0
        last_answer_duration_sec = 0
        last_answer_at = None

        for message in recent_messages:
            for topic in message.knowledge_points or []:
                topic_counts[str(topic)] += 2
            content = message.content or ""
            for topic in kp_names:
                if topic and topic in content:
                    topic_counts[topic] += 1

        for record in recent_records:
            if record.created_at:
                active_days.add(record.created_at.date().isoformat())
            action_counts[record.action] += 1
            if record.chapter_id:
                chapter_counts[int(record.chapter_id)] += 1
            record_text = " ".join(AnalyticsService._collect_texts(record.detail))
            for topic in kp_names:
                if topic and topic in record_text:
                    topic_counts[topic] += 1
            if record.duration_sec:
                total_duration_sec += record.duration_sec
                timed_records += 1
                last_answer_duration_sec = record.duration_sec
                last_answer_at = record.created_at
                if record.duration_sec < 120 and record.action in {"preview", "lecture", "review", "quiz", "homework", "exam"}:
                    short_sessions += 1

        for submission in recent_submissions:
            question = db.get(Question, submission.question_id)
            if not question or not question.knowledge_point_ids:
                continue
            correct = None
            score = 0.0
            if submission.qtype == "programming" and submission.code:
                correct = submission.code.verdict == "accepted"
                score = question.max_score if correct else 0.0
            elif submission.subjective and submission.subjective.teacher_score is not None:
                score = submission.subjective.teacher_score
                correct = score >= question.max_score * 0.6
            if correct is None:
                continue
            if correct:
                break
            wrong_submissions.append(
                {
                    "submission_id": submission.id,
                    "question_id": submission.question_id,
                    "question_title": question.title,
                    "knowledge_point_ids": list(question.knowledge_point_ids or []),
                    "updated_at": submission.updated_at.isoformat() if submission.updated_at else "",
                    "qtype": submission.qtype,
                    "score": score,
                }
            )
            for kp_id in question.knowledge_point_ids:
                wrong_point_counts[int(kp_id)] += 1

        recent_wrong_points = []
        for kp_id, count in wrong_point_counts.most_common():
            kp = db.get(KnowledgePoint, kp_id)
            recent_wrong_points.append(
                {
                    "knowledge_point_id": kp_id,
                    "name": kp.name if kp else f"知识点 {kp_id}",
                    "count": count,
                }
            )

        return {
            "recent_records": recent_records,
            "recent_messages": recent_messages,
            "recent_submissions": recent_submissions,
            "topic_counts": topic_counts,
            "chapter_counts": chapter_counts,
            "action_counts": action_counts,
            "short_sessions": short_sessions,
            "record_count_7d": len(recent_records),
            "active_days_7d": len(active_days),
            "avg_session_sec": round(total_duration_sec / max(1, timed_records), 1) if timed_records else 0.0,
            "last_answer_duration_sec": last_answer_duration_sec,
            "last_answer_at": last_answer_at,
            "wrong_streak": len(wrong_submissions),
            "recent_wrong_submissions": wrong_submissions,
            "recent_wrong_points": recent_wrong_points,
            "kp_by_id": kp_by_id,
        }

    @staticmethod
    def refresh_student_learning_state(db: Session, student_id: int) -> None:
        """重算学生的任务、计划和推荐，保持行为闭环。"""
        from app.services.learning_path_service import LearningPathService
        from app.services.planner_service import PlannerService
        from app.services.learning_state_service import LearningStateEngine

        student = db.get(User, student_id)
        if not student or student.role != "student":
            return
        LearningStateEngine.refresh(db, student_id)
        PlannerService.generate_tasks(db, student)
        PlannerService.generate_plan(db, student)
        LearningPathService.generate(db, student.id)

    # ---------- 画像更新 ----------
    @staticmethod
    def update_profile_from_result(
        db: Session,
        student_id: int,
        question: Question | None,
        correct: bool,
        score: float = 0.0,
    ) -> None:
        """根据一次提交结果更新学生知识点画像（教学研闭环的关键写入点）。"""
        if not question or not question.knowledge_point_ids:
            return
        for kp_id in question.knowledge_point_ids:
            profile = LearningRepository.get_profile(db, student_id, kp_id)
            if not profile:
                profile = StudentKnowledgeProfile(
                    student_id=student_id, knowledge_point_id=kp_id
                )
            profile.attempts = (profile.attempts or 0) + 1
            if not correct:
                profile.errors = (profile.errors or 0) + 1
            ratio = 1.0 if correct else max(0.0, min(1.0, score / question.max_score))
            old = profile.mastery or 0.0
            profile.mastery = round(min(100.0, old * 0.6 + ratio * 100 * 0.4), 1)
            LearningRepository.save_profile(db, profile)

    # ---------- 班级学情 ----------
    @staticmethod
    def class_analytics(db: Session, course_id: int) -> dict:
        course = CourseRepository.get(db, course_id)
        if not course:
            return {}
        students = CourseRepository.student_ids(db, course_id)
        assignments = CourseRepository.assignment_count(db, course_id)
        # 汇总该课程全部提交
        assignment_ids = list(
            db.scalars(select(Assignment.id).where(Assignment.course_id == course_id))
        )
        kp_map: dict[int, dict] = {}
        total_sub = 0
        graded = 0
        avg_acc_sum = 0.0
        submissions = (
            db.query(Submission)
            .filter(Submission.assignment_id.in_(assignment_ids))
            .all()
            if assignment_ids
            else []
        )
        for sub in submissions:
            total_sub += 1
            q = db.get(Question, sub.question_id)
            if not q:
                continue
            correct = False
            score = 0.0
            if sub.qtype == "programming" and sub.code:
                correct = sub.code.verdict == "accepted"
                score = q.max_score if correct else 0
                graded += 1
            elif sub.subjective and sub.subjective.teacher_score is not None:
                score = sub.subjective.teacher_score
                correct = score >= q.max_score * 0.6
                graded += 1
            elif sub.subjective and sub.subjective.ai_suggestion_score is not None:
                score = sub.subjective.ai_suggestion_score
                correct = score >= q.max_score * 0.6
            avg_acc_sum += 100.0 if correct else 0.0
            for kp_id in q.knowledge_point_ids:
                item = kp_map.setdefault(
                    kp_id,
                    {"knowledge_point_id": kp_id, "attempts": 0, "correct": 0},
                )
                item["attempts"] += 1
                if correct:
                    item["correct"] += 1

        kp_details = []
        for kp_id, item in sorted(kp_map.items(), key=lambda kv: -(
            (kv[1]["correct"] / max(1, kv[1]["attempts"]))
        )):
            kp = db.get(KnowledgePoint, kp_id)
            acc = round(100.0 * item["correct"] / max(1, item["attempts"]), 1)
            kp_details.append(
                {
                    "knowledge_point_id": kp_id,
                    "name": kp.name if kp else f"知识点 {kp_id}",
                    "subject": kp.subject if kp else "",
                    "attempts": item["attempts"],
                    "correct": item["correct"],
                    "accuracy": acc,
                }
            )
        # 高频错误 = 正确率最低且尝试数足够
        high_frequency = sorted(
            [k for k in kp_details if k["attempts"] >= 1],
            key=lambda k: (k["accuracy"], -k["attempts"]),
        )[:5]
        weak_points = [k["name"] for k in high_frequency if k["accuracy"] < 70]
        # 学生能力分布：基于各学生画像平均掌握度
        distribution = {"<60": 0, "60-69": 0, "70-79": 0, "80-89": 0, "90-100": 0}
        for sid in students:
            profiles = LearningRepository.list_profiles(db, sid)
            if not profiles:
                distribution["<60"] += 1
                continue
            avg = sum(p.mastery or 0 for p in profiles) / len(profiles)
            if avg < 60:
                distribution["<60"] += 1
            elif avg < 70:
                distribution["60-69"] += 1
            elif avg < 80:
                distribution["70-79"] += 1
            elif avg < 90:
                distribution["80-89"] += 1
            else:
                distribution["90-100"] += 1
        return {
            "course_id": course_id,
            "course_name": course.name,
            "total_students": len(students),
            "assignment_count": assignments,
            "submission_count": total_sub,
            "graded_count": graded,
            "avg_accuracy": round(avg_acc_sum / max(1, total_sub), 1),
            "knowledge_accuracy": kp_details,
            "high_frequency_errors": high_frequency,
            "ability_distribution": [
                {"band": k, "count": v} for k, v in distribution.items()
            ],
            "weak_points": weak_points,
        }

    # ---------- 学生画像 ----------
    @staticmethod
    def student_profile(db: Session, student_id: int) -> dict:
        profiles = LearningRepository.list_profiles(db, student_id)

        rows = []
        for p in profiles:
            kp = db.get(KnowledgePoint, p.knowledge_point_id)
            mastery = p.mastery or 0
            rows.append(
                {
                    "knowledge_point_id": p.knowledge_point_id,
                    "knowledge_point": kp.name if kp else f"知识点 {p.knowledge_point_id}",
                    "subject": kp.subject if kp else "",
                    "mastery": mastery,
                    "attempts": p.attempts,
                    "errors": p.errors,
                    "level": "掌握" if mastery >= 80 else "一般" if mastery >= 60 else "薄弱",
                }
            )
        rows.sort(key=lambda r: r["mastery"])
        weak = [r for r in rows if r["mastery"] < 60]
        strong = [r for r in rows if r["mastery"] >= 80]
        return {
            "student_id": student_id,
            "knowledge": rows,
            "weak_points": [r["knowledge_point"] for r in weak],
            "strong_points": [r["knowledge_point"] for r in strong],
            "avg_mastery": round(sum(r["mastery"] for r in rows) / max(1, len(rows)), 1),
        }
