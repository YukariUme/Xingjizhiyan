"""学习规划服务：基于真实学习数据生成可解释的今日任务与个性化计划。"""

from sqlalchemy.orm import Session

from app.models import (
    Assignment,
    Course,
    KnowledgePoint,
    LearningPlan,
    LearningTask,
    Submission,
    User,
)
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.course_repo import CourseRepository
from app.repositories.learning_repo import LearningRepository


class PlannerService:
    @staticmethod
    def generate_tasks(db: Session, student: User) -> list[LearningTask]:
        """从作业表现、编程评测、错题与画像生成今日任务（每项带原因与证据）。"""
        tasks: list[LearningTask] = []
        profiles = LearningRepository.list_profiles(db, student.id)
        # 1) 薄弱知识点 → 复习任务
        for profile in sorted(profiles, key=lambda p: p.mastery)[:4]:
            kp = db.get(KnowledgePoint, profile.knowledge_point_id)
            if not kp or (profile.mastery or 0) >= 60:
                continue
            course = db.query(Course).filter(Course.name == kp.subject).first()
            tasks.append(
                LearningTask(
                    student_id=student.id,
                    course_id=course.id if course else None,
                    knowledge_point_id=kp.id,
                    title=f"复习「{kp.name}」",
                    reason=(
                        f"你最近 {profile.attempts} 次相关练习中有 {profile.errors} 次错误，"
                        f"掌握度 {profile.mastery:.0f}%，建议先完成复习。"
                    ),
                    task_type="review",
                    status="todo",
                    evidence={
                        "type": "profile",
                        "attempts": profile.attempts,
                        "errors": profile.errors,
                        "mastery": profile.mastery,
                    },
                )
            )
        # 2) 待完成作业 → 任务
        course_ids = [c.id for c in CourseRepository.list_for_student(db, student.id)]
        assignments = AssignmentRepository.list_for_student(db, course_ids)
        for assignment in assignments[:3]:
            if not assignment.questions:
                continue
            tasks.append(
                LearningTask(
                    student_id=student.id,
                    course_id=assignment.course_id,
                    title=f"完成作业《{assignment.title}》",
                    reason=f"作业截止 {assignment.due_at.strftime('%m-%d %H:%M')}，共 {len(assignment.questions)} 道题",
                    task_type="homework",
                    due_at=assignment.due_at,
                    status="todo",
                    evidence={"type": "assignment", "assignment_id": assignment.id},
                )
            )
        # 3) 错题重做
        wrong = (
            db.query(Submission)
            .filter(Submission.student_id == student.id, Submission.status == "submitted")
            .order_by(Submission.updated_at.desc())
            .limit(3)
            .all()
        )
        for submission in wrong:
            assignment = db.get(Assignment, submission.assignment_id)
            tasks.append(
                LearningTask(
                    student_id=student.id,
                    course_id=assignment.course_id if assignment else None,
                    title="重做/查看错题诊断",
                    reason="你最近一次编程评测未全部通过，建议查看错误诊断并重做。",
                    task_type="retry",
                    status="todo",
                    evidence={"type": "submission", "submission_id": submission.id},
                )
            )
        # 替换旧的 todo 任务，保留完成记录
        old = db.query(LearningTask).filter(
            LearningTask.student_id == student.id, LearningTask.status == "todo"
        ).all()
        for item in old:
            db.delete(item)
        db.add_all(tasks)
        db.commit()
        return tasks

    @staticmethod
    def generate_plan(db: Session, student: User) -> LearningPlan:
        """生成个性化学习计划：按薄弱点 → 复习 → 练习 → 测验 → 进阶论文。"""
        profiles = LearningRepository.list_profiles(db, student.id)
        weak = [p for p in sorted(profiles, key=lambda p: p.mastery)[:4] if (p.mastery or 0) < 60]
        steps = []
        for index, profile in enumerate(weak, start=1):
            kp = db.get(KnowledgePoint, profile.knowledge_point_id)
            if not kp:
                continue
            steps.append(
                {
                    "order": index,
                    "title": f"复习「{kp.name}」",
                    "detail": f"掌握度 {profile.mastery:.0f}%，先读讲义核心概念与易错点。",
                    "evidence": {"mastery": profile.mastery, "errors": profile.errors},
                }
            )
        if not steps:
            steps.append(
                {
                    "order": 1,
                    "title": "进入科研探索",
                    "detail": "当前没有明显薄弱知识点，建议阅读本领域前沿论文。",
                    "evidence": {},
                }
            )
        old = db.query(LearningPlan).filter(LearningPlan.student_id == student.id).all()
        for item in old:
            db.delete(item)
        plan = LearningPlan(
            student_id=student.id,
            title="我的个性化学习计划",
            content=steps,
            reason="基于最近作业、评测与知识画像生成",
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan
