"""学情分析服务：班级统计、学生画像更新与个性化路径。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Assignment,
    KnowledgePoint,
    Question,
    StudentKnowledgeProfile,
    Submission,
)
from app.repositories.course_repo import CourseRepository
from app.repositories.learning_repo import LearningRepository
from app.repositories.submission_repo import SubmissionRepository


class AnalyticsService:
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
