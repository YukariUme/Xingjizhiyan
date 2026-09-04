"""Demo Mode 服务：演示用户、场景数据、会话状态、一键重置与预置响应。

设计要点：
- Demo 使用独立账户（demo_teacher / demo_student / demo_researcher），
  复用现有《操作系统》课程，不污染真实用户数据；
- 重置 = 删除 Demo 用户产生的业务数据并重放初始快照（幂等）；
- 关键 AI 端点由 demo 中间件返回预置结果，现场演示不依赖真实 LLM。
"""

import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    ChatMessage,
    CodeSubmission,
    Course,
    CourseChapter,
    Enrollment,
    KnowledgePoint,
    LearningRecommendation,
    LearningTask,
    Paper,
    PaperReading,
    Question,
    StudentKnowledgeProfile,
    Submission,
    User,
)
from app.models.demo import DemoScenario, DemoSession
from app.services.demo.definitions import (
    DEMO_REFERENCES,
    SCENARIOS,
    get_scenario_def,
    preset_code_diagnosis,
    preset_diagnosis,
    preset_lecture,
    preset_paper_analysis,
    preset_tutor,
)


DEMO_USERNAMES = {
    "teacher": "demo_teacher",
    "student": "demo_student",
    "researcher": "demo_researcher",
}


def _hash(username: str, password: str) -> str:
    import hashlib

    return hashlib.sha256(f"{username}:{password}".encode()).hexdigest()


def ensure_demo_users(db: Session) -> dict[str, User]:
    """创建/获取 Demo 账户，并把 Demo 学生选入《操作系统》课程。"""
    specs = [
        ("demo_teacher", "王教授", "teacher", "teacher", "教师 · 计算机学院"),
        ("demo_student", "李明", "student", "undergraduate", "本科生 · 计算机科学与技术"),
        ("demo_researcher", "李明", "researcher", "graduate", "研究生 · 并发与操作系统方向"),
    ]
    users: dict[str, User] = {}
    for username, display_name, role, identity, title in specs:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                display_name=display_name,
                password_hash=_hash(username, "123456"),
                role=role,
                identity=identity,
                modes=["teaching", "learning", "research"] if role == "teacher" else ["learning", "research"],
                title=title,
            )
            db.add(user)
            db.flush()
        users[role] = user
    # 学生选入操作系统课程；演示教师拥有该课程，保证学情分析/教学诊断有内容可看
    os_course = db.query(Course).filter(Course.name == "操作系统").first()
    if os_course:
        if os_course.teacher_id != users["teacher"].id:
            os_course.teacher_id = users["teacher"].id
        if not db.query(Enrollment).filter_by(
            course_id=os_course.id, student_id=users["student"].id
        ).first():
            db.add(Enrollment(course_id=os_course.id, student_id=users["student"].id))
    db.commit()
    return users


def ensure_scenarios(db: Session) -> None:
    """把场景定义落库（幂等 upsert）。"""
    users = ensure_demo_users(db)
    os_course = db.query(Course).filter(Course.name == "操作系统").first()
    for sc in SCENARIOS:
        row = db.get(DemoScenario, sc["id"])
        if not row:
            row = DemoScenario(id=sc["id"])
            db.add(row)
        row.name = sc["name"]
        row.description = sc["description"]
        row.initial_role = sc.get("initial_role", "teacher")
        row.course_id = os_course.id if os_course else None
        row.teacher_user_id = users["teacher"].id
        row.student_user_id = users["student"].id
        row.research_user_id = users["researcher"].id
        row.steps = sc["steps"]
        row.seed_data_version = "v1"
    db.commit()


def start_demo(db: Session, scenario_id: str, owner_user_id: int | None = None) -> dict:
    """启动演示：校验场景 → 重置数据 → 创建会话 → 返回会话与初始角色。"""
    ensure_scenarios(db)
    scenario = db.get(DemoScenario, scenario_id)
    if not scenario:
        raise ValueError("演示场景不存在")
    reset_demo_data(db)
    session = DemoSession(
        id=uuid.uuid4().hex[:16],
        scenario_id=scenario_id,
        current_step=scenario.steps[0]["id"] if scenario.steps else "",
        current_role="teacher",
        state_version=1,
        owner_user_id=owner_user_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session_out(db, session)


def session_out(db: Session, session: DemoSession) -> dict:
    scenario = db.get(DemoScenario, session.scenario_id)
    role_user = demo_user_for_role(db, session.current_role)
    course = db.get(Course, scenario.course_id) if scenario and scenario.course_id else None
    return {
        "session_id": session.id,
        "scenario": {
            "id": scenario.id if scenario else "",
            "name": scenario.name if scenario else "",
            "description": scenario.description if scenario else "",
            "course": course.id if course else 0,
            "course_name": course.name if course else "操作系统",
            "steps": scenario.steps if scenario else [],
        },
        "current_step": session.current_step,
        "current_role": session.current_role,
        "role_user": {
            "id": role_user.id if role_user else None,
            "display_name": role_user.display_name if role_user else "",
            "title": role_user.title if role_user else "",
        },
        "state_version": session.state_version,
        "demo_mode": True,
    }


def demo_user_for_role(db: Session, role: str) -> User | None:
    username = DEMO_USERNAMES.get(role)
    return db.query(User).filter(User.username == username).first() if username else None


def get_session(db: Session, session_id: str) -> DemoSession | None:
    return db.get(DemoSession, session_id)


def set_step(db: Session, session_id: str, step_id: str | None, direction: str = "next") -> dict:
    session = get_session(db, session_id)
    if not session:
        raise ValueError("演示会话不存在")
    scenario = db.get(DemoScenario, session.scenario_id)
    steps = scenario.steps if scenario else []
    if not steps:
        raise ValueError("场景步骤为空")
    if step_id:
        session.current_step = step_id
    else:
        idx = next((i for i, s in enumerate(steps) if s["id"] == session.current_step), 0)
        idx = min(len(steps) - 1, idx + 1) if direction == "next" else max(0, idx - 1)
        session.current_step = steps[idx]["id"]
    db.commit()
    db.refresh(session)
    return session_out(db, session)


def set_role(db: Session, session_id: str, role: str) -> dict:
    if role not in DEMO_USERNAMES:
        raise ValueError("不支持的演示角色")
    session = get_session(db, session_id)
    if not session:
        raise ValueError("演示会话不存在")
    session.current_role = role
    db.commit()
    db.refresh(session)
    return session_out(db, session)


def reset_demo(db: Session, session_id: str) -> dict:
    session = get_session(db, session_id)
    if not session:
        raise ValueError("演示会话不存在")
    reset_demo_data(db)
    session.state_version = (session.state_version or 1) + 1
    scenario = db.get(DemoScenario, session.scenario_id)
    session.current_step = scenario.steps[0]["id"] if scenario and scenario.steps else ""
    session.current_role = scenario.initial_role if scenario else "teacher"
    db.commit()
    db.refresh(session)
    return session_out(db, session)


def exit_demo(db: Session, session_id: str) -> None:
    session = get_session(db, session_id)
    if session:
        db.delete(session)
        db.commit()


def reset_demo_data(db: Session) -> None:
    """清空 Demo 用户产生的数据并重放初始快照（幂等）。"""
    users = ensure_demo_users(db)
    ids = [u.id for u in users.values()]
    # 按依赖顺序删除：先删 Submission 关联的评测，再删各类业务数据
    sub_ids = [r[0] for r in db.query(Submission.id).filter(Submission.student_id.in_(ids)).all()]
    if sub_ids:
        db.query(CodeSubmission).filter(CodeSubmission.submission_id.in_(sub_ids)).delete(
            synchronize_session=False
        )
    db.query(Submission).filter(Submission.student_id.in_(ids)).delete(synchronize_session=False)
    db.query(ChatMessage).filter(ChatMessage.user_id.in_(ids)).delete(synchronize_session=False)
    db.query(PaperReading).filter(PaperReading.user_id.in_(ids)).delete(synchronize_session=False)
    db.query(StudentKnowledgeProfile).filter(
        StudentKnowledgeProfile.student_id.in_(ids)
    ).delete(synchronize_session=False)
    db.query(LearningTask).filter(LearningTask.student_id.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(LearningRecommendation).filter(
        LearningRecommendation.student_id.in_(ids)
    ).delete(synchronize_session=False)
    db.commit()
    seed_initial_state(db, users)


def seed_initial_state(db: Session, users: dict[str, User]) -> None:
    """为 Demo 学生写入初始画像、失败代码提交、对话、任务与论文阅读。"""
    student = users["student"]
    os_course = db.query(Course).filter(Course.name == "操作系统").first()
    if not os_course:
        return

    # 1) 学习画像（进程同步/信号量/死锁偏弱）
    kp_by_name: dict[str, KnowledgePoint] = {}
    for kp in db.query(KnowledgePoint).filter(KnowledgePoint.subject == "操作系统").all():
        kp_by_name[kp.name] = kp
    for name, mastery, errors in [
        ("进程同步与互斥", 42, 3),
        ("信号量", 47, 2),
        ("死锁", 51, 1),
        ("进程与线程", 68, 1),
    ]:
        kp = kp_by_name.get(name)
        if kp:
            db.add(
                StudentKnowledgeProfile(
                    student_id=student.id,
                    knowledge_point_id=kp.id,
                    mastery=mastery,
                    errors=errors,
                    attempts=6,
                    success_count=5,
                    evidence_count=6,
                    confidence=0.7,
                )
            )

    # 2) 一次失败的生产者-消费者代码提交（8/12，Wrong Answer）
    from app.models import Assignment

    question = (
        db.query(Question)
        .join(Assignment, Assignment.id == Question.assignment_id)
        .filter(
            Assignment.course_id == os_course.id,
            Question.qtype == "programming",
        )
        .first()
    )
    if question:
        submission = Submission(
            assignment_id=question.assignment_id if hasattr(question, "assignment_id") else 0,
            question_id=question.id,
            student_id=student.id,
            qtype="programming",
            status="submitted",
        )
        db.add(submission)
        db.flush()
        db.add(
            CodeSubmission(
                submission_id=submission.id,
                source_code=(
                    "import threading\nfrom threading import Semaphore\n"
                    "empty = Semaphore(5)\nfull = Semaphore(0)\nmutex = Semaphore(1)\n\n"
                    "def consumer():\n    while True:\n        P(mutex)\n        P(full)\n"
                    "        item = buffer.pop(0)\n        V(empty)\n        V(mutex)\n"
                ),
                language="python",
                verdict="wrong_answer",
                passed_tests=8,
                total_tests=12,
                runtime_ms=23,
                error_message="部分测试中消费者可能在缓冲区为空时继续执行。",
                judge_report=[
                    {"test_id": i + 1, "name": f"case{i + 1}", "passed": i < 8, "message": "" if i < 8 else "消费者在缓冲区为空时被唤醒"}
                    for i in range(12)
                ],
            )
        )

    # 3) 对话历史 + 学习任务
    db.add(
        ChatMessage(
            user_id=student.id,
            agent_type="learning",
            role="assistant",
            content="为什么生产者和消费者都需要使用信号量？——empty 管“能不能放”，full 管“能不能取”，mutex 保护缓冲区互斥访问…",
            knowledge_points=["信号量", "同步"],
            references=[r["source"] for r in DEMO_REFERENCES],
        )
    )
    for title, reason in [
        ("复习信号量与 P/V 操作", "你在信号量相关练习中最近 3 次有 2 次错误（掌握度 47%）"),
        ("学习生产者—消费者问题", "代码实验未通过：消费者在缓冲区为空时继续执行"),
        ("重做同步代码题", "进程同步知识点正确率 42%，低于班级平均"),
    ]:
        db.add(
            LearningTask(
                student_id=student.id,
                course_id=os_course.id,
                title=title,
                reason=reason,
                task_type="study",
                status="todo",
            )
        )

    # 4) 论文阅读记录（进程同步相关论文）
    paper = db.query(Paper).filter(Paper.title.like("%并发%") | Paper.title.like("%同步%")).first() or (
        db.query(Paper).first()
    )
    if paper:
        db.add(PaperReading(user_id=student.id, paper_id=paper.id, status="reading", progress=60))
    db.commit()
