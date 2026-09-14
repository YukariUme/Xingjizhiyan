"""学习规划服务：基于真实学习数据生成可解释的今日任务与个性化计划。"""

from sqlalchemy.orm import Session

from app.models import (
    Assignment,
    Course,
    KnowledgePoint,
    LearningPlan,
    LearningTask,
    User,
)
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.course_repo import CourseRepository
from app.repositories.learning_repo import LearningRepository
from app.services.analytics_service import AnalyticsService
from app.services.learning_state_service import LearningStateEngine


class PlannerService:
    @staticmethod
    def generate_tasks(db: Session, student: User) -> list[LearningTask]:
        """从作业表现、编程评测、错题与行为窗口生成今日任务。"""
        tasks: list[LearningTask] = []
        profiles = LearningRepository.list_profiles(db, student.id)
        states = {s.knowledge_point_id: s for s in LearningStateEngine.list_states(db, student.id)}
        behavior = AnalyticsService.recent_behavior_window(db, student.id, profiles)
        topic_counts = behavior["topic_counts"]
        wrong_points = behavior["recent_wrong_points"]
        wrong_streak = behavior["wrong_streak"]
        record_count_7d = behavior["record_count_7d"]
        active_days_7d = behavior["active_days_7d"]
        avg_session_sec = behavior["avg_session_sec"]
        short_sessions = behavior["short_sessions"]
        last_answer_duration_sec = behavior["last_answer_duration_sec"]
        recent_wrong_submissions = behavior["recent_wrong_submissions"]
        seen_titles: set[str] = set()

        def add_task(task: LearningTask) -> None:
            if task.title in seen_titles:
                return
            seen_titles.add(task.title)
            tasks.append(task)

        # 1) 薄弱知识点 → 复习任务
        weak_profiles = [p for p in sorted(profiles, key=lambda p: p.mastery) if (p.mastery or 0) < 60][:4]
        top_wrong = wrong_points[0] if wrong_points else None
        for profile in weak_profiles:
            kp = db.get(KnowledgePoint, profile.knowledge_point_id)
            if not kp:
                continue
            state = states.get(kp.id)
            course = db.query(Course).filter(Course.name == kp.subject).first()
            topic_hits = topic_counts.get(kp.name, 0)
            reason_parts = [
                f"最近 7 天有 {record_count_7d} 条学习记录，活跃 {active_days_7d} 天，平均每次 {avg_session_sec:.0f} 秒。",
                f"你在 {profile.attempts} 次相关练习中错 {profile.errors} 次，掌握度 {profile.mastery:.0f}%。",
            ]
            if state:
                reason_parts.append(f"当前状态：{state.state}。{state.state_reason}")
            if topic_hits:
                reason_parts.append(f"最近答疑/复盘中又提到这个点 {topic_hits} 次。")
            if top_wrong and top_wrong["name"] == kp.name and wrong_streak >= 2:
                reason_parts.append(f"最近连续错了 {wrong_streak} 次，先把这一点稳住。")
            if short_sessions >= 2:
                reason_parts.append("最近多次短时学习，建议放慢速度完整过一遍。")
            if last_answer_duration_sec:
                reason_parts.append(f"最近一次学习耗时 {last_answer_duration_sec} 秒。")
            add_task(
                LearningTask(
                    student_id=student.id,
                    course_id=course.id if course else None,
                    knowledge_point_id=kp.id,
                    title=f"复习「{kp.name}」",
                    reason=" ".join(reason_parts),
                    task_type="review",
                    status="todo",
                    evidence={
                        "type": "profile",
                        "state": state.state if state else "",
                        "state_reason": state.state_reason if state else "",
                        "attempts": profile.attempts,
                        "errors": profile.errors,
                        "mastery": profile.mastery,
                        "topic_hits": topic_hits,
                        "wrong_streak": wrong_streak,
                        "record_count_7d": record_count_7d,
                        "active_days_7d": active_days_7d,
                        "avg_session_sec": avg_session_sec,
                        "last_answer_duration_sec": last_answer_duration_sec,
                    },
                )
            )

        # 2) 待完成作业 → 任务
        course_ids = [c.id for c in CourseRepository.list_for_student(db, student.id)]
        assignments = AssignmentRepository.list_for_student(db, course_ids)
        for assignment in assignments[:3]:
            if not assignment.questions:
                continue
            add_task(
                LearningTask(
                    student_id=student.id,
                    course_id=assignment.course_id,
                    title=f"完成作业《{assignment.title}》",
                    reason=f"作业截止 {assignment.due_at.strftime('%m-%d %H:%M')}，共 {len(assignment.questions)} 道题。",
                    task_type="homework",
                    due_at=assignment.due_at,
                    status="todo",
                    evidence={"type": "assignment", "assignment_id": assignment.id},
                )
            )

        # 3) 错题重做
        for submission in recent_wrong_submissions[:3]:
            add_task(
                LearningTask(
                    student_id=student.id,
                    course_id=None,
                    title="重做/查看错题诊断",
                    reason=(
                        f"你最近在《{submission['question_title']}》上还在卡住，"
                        f"建议先看错因，再针对同类题重做。"
                    ),
                    task_type="retry",
                    status="todo",
                    evidence={"type": "submission", **submission},
                )
            )

        # 4) 行为驱动补课：最近反复提问或节奏偏快时，补一条“回看/自测”任务。
        if topic_counts:
            top_topic, top_count = topic_counts.most_common(1)[0]
            if top_count >= 2:
                add_task(
                    LearningTask(
                        student_id=student.id,
                        course_id=None,
                        title=f"回看最近高频问题「{top_topic}」",
                        reason=f"你最近在答疑/复盘里多次提到这个主题（{top_count} 次），先把它完整过一遍再继续下一步。",
                        task_type="review",
                        status="todo",
                        evidence={
                            "type": "behavior",
                            "state": "REVIEW" if top_count >= 2 else "",
                            "topic": top_topic,
                            "topic_hits": top_count,
                        },
                    )
                )
        if short_sessions >= 2:
            add_task(
                LearningTask(
                    student_id=student.id,
                    course_id=None,
                    title="补一次完整自学",
                    reason=f"最近有 {short_sessions} 次短时学习，建议先连续完整学完一个章节，再做一次测验检验掌握度。",
                    task_type="study",
                    status="todo",
                    evidence={
                        "type": "behavior",
                        "state": "REVIEW",
                        "short_sessions": short_sessions,
                        "record_count_7d": record_count_7d,
                    },
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
        """生成个性化学习计划：按行为优先级组织复习 → 自测 → 进阶。"""
        profiles = LearningRepository.list_profiles(db, student.id)
        states = {s.knowledge_point_id: s for s in LearningStateEngine.list_states(db, student.id)}
        behavior = AnalyticsService.recent_behavior_window(db, student.id, profiles)
        topic_counts = behavior["topic_counts"]
        wrong_points = behavior["recent_wrong_points"]
        wrong_streak = behavior["wrong_streak"]
        short_sessions = behavior["short_sessions"]
        avg_session_sec = behavior["avg_session_sec"]
        record_count_7d = behavior["record_count_7d"]
        active_days_7d = behavior["active_days_7d"]
        last_answer_duration_sec = behavior["last_answer_duration_sec"]
        weak = [p for p in sorted(profiles, key=lambda p: p.mastery) if (p.mastery or 0) < 60][:4]
        steps = []
        index = 1

        if wrong_streak >= 2 and wrong_points:
            top_wrong = wrong_points[0]
            steps.append(
                {
                    "order": index,
                    "title": f"先处理最近连续错题「{top_wrong['name']}」",
                    "detail": (
                        f"最近 7 天共有 {record_count_7d} 条学习记录，活跃 {active_days_7d} 天。"
                        f"你在这个点上连续错了 {wrong_streak} 次，先回看讲义、错因和同类题。"
                    ),
                    "evidence": {"topic": top_wrong["name"], "hits": top_wrong["count"], "wrong_streak": wrong_streak, "state": "STRUGGLING"},
                }
            )
            index += 1

        for profile in weak:
            kp = db.get(KnowledgePoint, profile.knowledge_point_id)
            if not kp:
                continue
            state = states.get(kp.id)
            topic_hits = topic_counts.get(kp.name, 0)
            steps.append(
                {
                    "order": index,
                    "title": f"复习「{kp.name}」",
                    "detail": (
                        f"掌握度 {profile.mastery:.0f}%，建议先读讲义核心概念与易错点。"
                        f"最近答疑相关提问 {topic_hits} 次。"
                        + (f" 当前状态：{state.state}。" if state else "")
                    ),
                    "evidence": {"mastery": profile.mastery, "errors": profile.errors, "topic_hits": topic_hits, "state": state.state if state else ""},
                }
            )
            index += 1

        if topic_counts:
            top_topic, top_count = topic_counts.most_common(1)[0]
            if top_count >= 2:
                steps.append(
                {
                    "order": index,
                    "title": f"回看高频主题「{top_topic}」",
                    "detail": (
                        f"最近在答疑和复盘里多次提到这个主题（{top_count} 次），"
                        "先把相关概念重新串起来，再进入练习。"
                    ),
                    "evidence": {"topic": top_topic, "hits": top_count, "state": "REVIEW"},
                }
            )
                index += 1

        if short_sessions >= 2:
            steps.append(
                {
                    "order": index,
                    "title": "做一次完整自测",
                    "detail": (
                        f"最近平均每次学习 {avg_session_sec:.0f} 秒，且有 {short_sessions} 次短时学习。"
                        "建议用一套完整测验检查是否真的吃透。"
                    ),
                    "evidence": {
                        "state": "REVIEW",
                        "short_sessions": short_sessions,
                        "avg_session_sec": avg_session_sec,
                        "last_answer_duration_sec": last_answer_duration_sec,
                    },
                }
            )
            index += 1

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
            reason="基于最近作业、评测、答疑记录与学习节奏生成",
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan
