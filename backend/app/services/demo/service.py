"""Demo Mode 服务：演示用户、场景数据、会话状态、一键重置与预置响应。

设计要点：
- Demo 使用独立账户（demo_teacher / demo_student / demo_researcher），
  复用现有《操作系统》课程，不污染真实用户数据；
- 重置 = 删除 Demo 用户产生的业务数据并重放初始快照（幂等）；
- 关键 AI 端点由 demo 中间件返回预置结果，现场演示不依赖真实 LLM。
"""

import json
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import utcnow
from app.models import (
    Activity,
    ChatMessage,
    CodeSubmission,
    Course,
    CourseChapter,
    Enrollment,
    Evaluation,
    Feedback,
    KnowledgeDocument,
    LessonPlan,
    KnowledgePoint,
    KnowledgeReview,
    LearningPlan,
    LearningRecord,
    LearningRecommendation,
    LearningTask,
    Paper,
    PaperReading,
    Question,
    Quiz,
    QuizQuestion,
    QuizResult,
    KnowledgeJob,
    ResearchDocument,
    ResearchTopic,
    StudentKnowledgeProfile,
    SubjectiveSubmission,
    Submission,
    User,
    WorkflowRun,
    WorkflowStepRun,
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
        course = db.query(Course).filter(Course.name == sc.get("course")).first()
        row = db.get(DemoScenario, sc["id"])
        if not row:
            row = DemoScenario(id=sc["id"])
            db.add(row)
        row.name = sc["name"]
        row.description = sc["description"]
        row.initial_role = sc.get("initial_role", "teacher")
        row.course_id = (course or os_course).id if (course or os_course) else None
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
    """?? Demo ???????????????????"""
    users = ensure_demo_users(db)
    ids = [u.id for u in users.values()]
    # ?????????? Submission ??????????????
    sub_ids = [r[0] for r in db.query(Submission.id).filter(Submission.student_id.in_(ids)).all()]
    if sub_ids:
        db.query(CodeSubmission).filter(CodeSubmission.submission_id.in_(sub_ids)).delete(
            synchronize_session=False
        )
        db.query(SubjectiveSubmission).filter(
            SubjectiveSubmission.submission_id.in_(sub_ids)
        ).delete(synchronize_session=False)
        db.query(Evaluation).filter(Evaluation.submission_id.in_(sub_ids)).delete(
            synchronize_session=False
        )
        db.query(Feedback).filter(Feedback.submission_id.in_(sub_ids)).delete(
            synchronize_session=False
        )
    db.query(Submission).filter(Submission.student_id.in_(ids)).delete(synchronize_session=False)
    db.query(ChatMessage).filter(ChatMessage.user_id.in_(ids)).delete(synchronize_session=False)
    db.query(PaperReading).filter(PaperReading.user_id.in_(ids)).delete(synchronize_session=False)
    db.query(LearningRecord).filter(LearningRecord.student_id.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(LearningPlan).filter(LearningPlan.student_id.in_(ids)).delete(synchronize_session=False)
    db.query(StudentKnowledgeProfile).filter(
        StudentKnowledgeProfile.student_id.in_(ids)
    ).delete(synchronize_session=False)
    db.query(LearningTask).filter(LearningTask.student_id.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(LearningRecommendation).filter(
        LearningRecommendation.student_id.in_(ids)
    ).delete(synchronize_session=False)
    db.query(Activity).filter(Activity.user_id.in_(ids)).delete(synchronize_session=False)
    db.query(ResearchTopic).filter(ResearchTopic.owner_id.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(ResearchDocument).filter(ResearchDocument.owner_id.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(KnowledgeReview).filter(
        or_(KnowledgeReview.requester_id.in_(ids), KnowledgeReview.reviewer_id.in_(ids))
    ).delete(synchronize_session=False)
    db.query(KnowledgeDocument).filter(KnowledgeDocument.owner_id.in_(ids)).delete(
        synchronize_session=False
    )
    quiz_ids = [r[0] for r in db.query(Quiz.id).filter(Quiz.created_by == users["teacher"].id).all()]
    if quiz_ids:
        db.query(QuizResult).filter(QuizResult.quiz_id.in_(quiz_ids)).delete(
            synchronize_session=False
        )
        db.query(QuizQuestion).filter(QuizQuestion.quiz_id.in_(quiz_ids)).delete(
            synchronize_session=False
        )
        db.query(Quiz).filter(Quiz.id.in_(quiz_ids)).delete(synchronize_session=False)
    run_ids = [r[0] for r in db.query(WorkflowRun.id).filter(WorkflowRun.owner_id.in_(ids)).all()]
    if run_ids:
        db.query(WorkflowStepRun).filter(WorkflowStepRun.run_id.in_(run_ids)).delete(
            synchronize_session=False
        )
        db.query(WorkflowRun).filter(WorkflowRun.id.in_(run_ids)).delete(synchronize_session=False)
    db.commit()
    seed_initial_state(db, users)


def seed_initial_state(db: Session, users: dict[str, User]) -> None:
    """? Demo ?????????????????????????"""
    teacher = users["teacher"]
    student = users["student"]
    researcher = users["researcher"]
    os_course = db.query(Course).filter(Course.name == "操作系统").first()
    if not os_course:
        return

    now = utcnow()
    knowledge_files_dir = Path(get_settings().knowledge_files_dir)
    knowledge_files_dir.mkdir(parents=True, exist_ok=True)
    sample_import_path = knowledge_files_dir / "os_sync_demo.txt"
    if not sample_import_path.exists():
        sample_import_path.write_text(
            "操作系统同步导入样例\n\n本文件用于演示知识库批量导入功能。\n\n主题：进程同步与互斥\n核心概念：信号量、P/V 操作、临界区、生产者-消费者、死锁\n\n评委可直接在知识库页面看到该文件被扫描到，并进入导入队列。\n",
            encoding="utf-8",
        )
    chapters = {ch.official_ref: ch for ch in db.query(CourseChapter).filter(CourseChapter.course_id == os_course.id).all()}
    kp_by_name = {
        kp.name: kp
        for kp in db.query(KnowledgePoint).filter(KnowledgePoint.subject == "操作系统").all()
    }

    # 1) ?????????? + ?????
    for name, mastery, errors, attempts in [
        ("???????", 42, 3, 6),
        ("???", 47, 2, 6),
        ("??", 51, 1, 5),
        ("?????", 68, 1, 5),
        ("????", 73, 1, 4),
    ]:
        kp = kp_by_name.get(name)
        if kp:
            db.add(
                StudentKnowledgeProfile(
                    student_id=student.id,
                    knowledge_point_id=kp.id,
                    mastery=mastery,
                    errors=errors,
                    attempts=attempts,
                    success_count=max(0, attempts - errors),
                    evidence_count=attempts,
                    confidence=0.72,
                )
            )

    # 2) ????????????????????
    shared_doc = KnowledgeDocument(
        title="?????????? 4 ? ????",
        source="???? PPT",
        course="????",
        topic="????????",
        chapter="? 4 ? ????",
        difficulty="?",
        type="??",
        year=2026,
        content="??????????????????????????",
        metadata_json={"demo": True, "scene": "teaching"},
        course_id=os_course.id,
        source_level="A",
        visibility="shared",
        owner_id=teacher.id,
        page="? 35-42 ?",
        document_type="??",
        approved_by=teacher.id,
        approved_at=now,
    )
    shared_doc.rag_hit_count = 12
    db.add(shared_doc)
    pending_doc = KnowledgeDocument(
        title="?????????????",
        source="????",
        course="????",
        topic="???????",
        chapter="? 4 ? ????",
        difficulty="?",
        type="??",
        year=2026,
        content="???????-??????????????????????",
        metadata_json={"demo": True, "scene": "review"},
        course_id=os_course.id,
        source_level="P",
        visibility="private",
        owner_id=student.id,
        page="? 1 ?",
        document_type="??",
    )
    db.add(pending_doc)
    db.flush()
    db.add(
        KnowledgeReview(
            document_id=pending_doc.id,
            course_id=os_course.id,
            requester_id=student.id,
            status="pending",
            comment="?????????????????",
        )
    )
    db.add(
        LessonPlan(
            teacher_id=teacher.id,
            course="操作系统",
            chapter="第 4 章 进程同步",
            topic="进程同步与信号量",
            grade="大二",
            objectives="1. 理解进程同步与互斥；2. 掌握信号量 P/V 操作；3. 理解生产者-消费者问题",
            knowledge_points=["进程同步与互斥", "信号量", "互斥"],
            key_points=["P/V 操作", "empty/full/mutex"],
            difficulties=["P/V 顺序", "死锁"],
            flow=[
                {"step": "导入", "content": "案例导入，引出进程同步"},
                {"step": "讲授", "content": "讲解信号量与互斥"},
                {"step": "演示", "content": "生产者-消费者问题"},
                {"step": "练习", "content": "现场演示 P/V 操作"},
            ],
            cases=["生产者-消费者完整案例"],
            exercises=[{"title": "基础题", "desc": "说明信号量的作用"}],
            homework=["编程实现生产者-消费者"],
        )
    )
    db.add(Activity(user_id=teacher.id, role="teacher", kind="lesson_plan", title="生成教案：操作系统 · 进程同步与信号量"))
    db.add(Activity(user_id=teacher.id, role="teacher", kind="grade_confirm", title="确认 6 份简答题成绩"))
    db.add(Activity(user_id=teacher.id, role="teacher", kind="knowledge_review", title="审核通过学生共享资料"))

    import_doc = KnowledgeDocument(
        title="操作系统同步导入样例",
        source="os_sync_demo.txt",
        course="操作系统",
        topic="进程同步与互斥",
        chapter="第 4 章 进程同步与互斥",
        difficulty="中",
        type="教材",
        year=2026,
        content="这是一份用于演示批量导入的文本样例，包含进程同步、信号量和生产者-消费者问题的核心说明。",
        metadata_json={"demo": True, "scene": "import"},
        course_id=os_course.id,
        source_level="S",
        visibility="official",
        owner_id=teacher.id,
        page="导入样例",
        document_type="教材",
        approved_by=teacher.id,
        approved_at=now,
    )
    import_doc.rag_hit_count = 6
    db.add(import_doc)
    db.flush()
    db.add(
        KnowledgeJob(
            owner_id=teacher.id,
            kind="import",
            status="success",
            filename="os_sync_demo.txt",
            course="操作系统",
            file_path=str(Path(get_settings().knowledge_files_dir)),
            progress=100,
            message="导入完成",
            result_json={
                "course": "操作系统",
                "files": ["os_sync_demo.txt"],
                "results": [
                    {
                        "filename": "os_sync_demo.txt",
                        "status": "imported",
                        "document_id": import_doc.id,
                        "title": import_doc.title,
                    }
                ],
            },
        )
    )
    # 3) ?????????????
    from app.models import Assignment
    assignments = db.query(Assignment).filter(Assignment.course_id == os_course.id).all()
    prog_q = next((q for a in assignments for q in a.questions if q.qtype == "programming"), None)
    subj_q = next((q for a in assignments for q in a.questions if q.qtype == "subjective"), None)
    report_q = next((q for a in assignments for q in a.questions if q.qtype == "report"), None)

    code_ok = """import threading
import queue
from queue import Queue

def producer(q, lock):
    for i in range(10):
        with lock:
            q.put(i)

def consumer(q, lock):
    while not q.empty():
        with lock:
            q.get()
"""
    code_bad = """import threading
from threading import Semaphore

empty = Semaphore(5)
full = Semaphore(0)
mutex = Semaphore(1)

def consumer():
    while True:
        P(mutex)
        P(full)
        item = buffer.pop(0)
        V(empty)
        V(mutex)
"""
    if prog_q:
        sub = Submission(assignment_id=prog_q.assignment_id, question_id=prog_q.id, student_id=student.id, qtype="programming", status="submitted")
        db.add(sub)
        db.flush()
        db.add(CodeSubmission(submission_id=sub.id, source_code=code_bad, language="python", verdict="wrong_answer", passed_tests=8, total_tests=12, runtime_ms=23, error_message="??????????????????????", judge_report=[{"test_id": i + 1, "name": f"case{i + 1}", "passed": i < 8, "message": "" if i < 8 else "?????????????"} for i in range(12)]))
    if subj_q:
        sub = Submission(assignment_id=subj_q.assignment_id, question_id=subj_q.id, student_id=student.id, qtype="subjective", status="submitted")
        db.add(sub)
        db.flush()
        subj = SubjectiveSubmission(
            submission_id=sub.id,
            content="?????????????????????????????????????????",
            ai_suggestion_score=8.5,
            ai_reasoning="?????????????????????????????????????",
            ai_knowledge_points=["?????"],
            ai_error_analysis="?????????????????",
            ai_improvement="??????????????????????",
        )
        db.add(subj)
    if report_q:
        sub = Submission(assignment_id=report_q.assignment_id, question_id=report_q.id, student_id=student.id, qtype="report", status="submitted")
        db.add(sub)
        db.flush()
        db.add(SubjectiveSubmission(submission_id=sub.id, content="?????BFS ??????????", ai_suggestion_score=9.0, ai_reasoning="?????", ai_knowledge_points=["?", "????"], ai_error_analysis="?????????", ai_improvement="?? BFS ? DFS ????"))

    # 4) ????????????
    for action, chapter_key, detail, mins in [
        ("preview", "?4? ????", {"topic": "????????", "step": "??"}, 18),
        ("lecture", "?4? ????", {"topic": "???-???", "step": "??"}, 36),
        ("homework", "?4? ????", {"assignment": "???????"}, 25),
        ("review", "?4? ????", {"topic": "????"}, 22),
        ("exam", "?4? ????", {"topic": "????"}, 30),
    ]:
        ch = next((c for c in chapters.values() if chapter_key in c.official_ref), None)
        db.add(
            LearningRecord(
                student_id=student.id,
                course_id=os_course.id,
                chapter_id=ch.id if ch else None,
                knowledge_point_id=kp_by_name.get("???").id if kp_by_name.get("???") else None,
                action=action,
                detail={**detail, "demo": True},
                duration_sec=mins * 60,
            )
        )
    db.add(LearningTask(student_id=student.id, course_id=os_course.id, knowledge_point_id=kp_by_name.get("???").id if kp_by_name.get("???") else None, title="???????", reason="????????????????????? P/V ???", task_type="review", due_at=now + timedelta(days=1), status="todo", evidence={"demo": True}))
    db.add(LearningTask(student_id=student.id, course_id=os_course.id, title="????????? ? ??????????", reason="????? 7 ??????????????", task_type="homework", due_at=now + timedelta(days=2), status="todo", evidence={"demo": True}))
    db.add(LearningTask(student_id=student.id, course_id=os_course.id, title="???????", reason="???????????? P/V ???", task_type="retry", status="todo", evidence={"demo": True}))

    plan = [
        {"order": 1, "title": "?????", "detail": "?? P/V ??????????-??????", "evidence": {"demo": True}},
        {"order": 2, "title": "??????", "detail": "?????????????", "evidence": {"demo": True}},
        {"order": 3, "title": "???????", "detail": "?????????????????", "evidence": {"demo": True}},
    ]
    db.add(LearningPlan(student_id=student.id, course_id=os_course.id, title="?????????", content=plan, reason="????????????????"))
    db.add(ChatMessage(user_id=student.id, agent_type="learning", role="user", content="????????????????????????", knowledge_points=[], references=[]))
    db.add(ChatMessage(user_id=student.id, agent_type="learning", role="assistant", content="??????????????????????????????????????????-?????mutex ????empty/full ??????", knowledge_points=["??", "??", "???"], references=[r["source"] for r in DEMO_REFERENCES]))
    db.add(ChatMessage(user_id=student.id, agent_type="learning", role="user", content="???-???????? P(empty) ? P(mutex)?", knowledge_points=[], references=[]))
    db.add(ChatMessage(user_id=student.id, agent_type="learning", role="assistant", content="?????????????????????????????????????????", knowledge_points=["???", "??"], references=[DEMO_REFERENCES[0]["source"], DEMO_REFERENCES[1]["source"]]))
    db.add(LearningRecommendation(student_id=student.id, knowledge_point_id=kp_by_name.get("???").id if kp_by_name.get("???") else None, reason="????????????????????? P/V?", resource_title="?????????????", resource_type="chapter", resource_ref={"course": "????", "chapter": "? 4 ? ????"}, priority=1))
    db.add(LearningRecommendation(student_id=student.id, knowledge_point_id=kp_by_name.get("?????").id if kp_by_name.get("?????") else None, reason="????????????????????", resource_title="????????", resource_type="chapter", resource_ref={"course": "????", "chapter": "? 3 ? ?????"}, priority=2))
    if paper := db.query(Paper).filter(or_(Paper.title.like("%??%"), Paper.title.like("%??%"))).first():
        db.add(PaperReading(user_id=student.id, paper_id=paper.id, status="favorite", progress=100))
    if paper2 := db.query(Paper).filter(Paper.title.like("%????%"), Paper.id != (paper.id if 'paper' in locals() and paper else -1)).first():
        db.add(PaperReading(user_id=student.id, paper_id=paper2.id, status="reading", progress=40))

    # 5) ???????????
    quiz = Quiz(course_id=os_course.id, chapter_id=next(iter(chapters.values())).id if chapters else None, title="???? ? ? 4 ?????", quiz_type="chapter", created_by=teacher.id, status="published")
    db.add(quiz)
    db.flush()
    q1 = QuizQuestion(quiz_id=quiz.id, qtype="single", title="??? P(S) ?????????", options=["S ? 1", "S ? 1???? 0 ???", "?????", "???"], answer={"index": 1}, analysis="P ?????????", knowledge_point_ids=[kp_by_name.get("???").id] if kp_by_name.get("???") else [], max_score=5, order=1)
    q2 = QuizQuestion(quiz_id=quiz.id, qtype="short", title="?????-???? empty?full?mutex ????", options=[], answer={}, analysis="empty ????full ??????mutex ???????", knowledge_point_ids=[kp_by_name.get("???").id, kp_by_name.get("???????").id] if kp_by_name.get("???") and kp_by_name.get("???????") else [], max_score=10, order=2)
    q3 = QuizQuestion(quiz_id=quiz.id, qtype="judge", title="P(mutex) ?? P(empty) ????????", options=[], answer={"value": False}, analysis="???????????", knowledge_point_ids=[kp_by_name.get("??").id] if kp_by_name.get("??") else [], max_score=5, order=3)
    db.add_all([q1, q2, q3])
    db.flush()
    db.add(QuizResult(quiz_id=quiz.id, student_id=student.id, score=9, max_score=20, answers=[{"question_id": q1.id, "answer": 1}, {"question_id": q2.id, "answer": "empty/full/mutex"}, {"question_id": q3.id, "answer": False}], details={"questions": [{"question_id": q1.id, "qtype": "single", "title": q1.title, "correct": True, "analysis": q1.analysis, "knowledge_point_ids": q1.knowledge_point_ids}, {"question_id": q2.id, "qtype": "short", "title": q2.title, "correct": False, "analysis": q2.analysis, "knowledge_point_ids": q2.knowledge_point_ids}, {"question_id": q3.id, "qtype": "judge", "title": q3.title, "correct": False, "analysis": q3.analysis, "knowledge_point_ids": q3.knowledge_point_ids}]}, started_at=now - timedelta(days=1), finished_at=now - timedelta(days=1, minutes=-20)))
    db.add(QuizResult(quiz_id=quiz.id, student_id=users["researcher"].id, score=17, max_score=20, answers=[{"question_id": q1.id, "answer": 1}, {"question_id": q2.id, "answer": "empty/full/mutex"}, {"question_id": q3.id, "answer": False}], details={"questions": [{"question_id": q1.id, "qtype": "single", "title": q1.title, "correct": True, "analysis": q1.analysis, "knowledge_point_ids": q1.knowledge_point_ids}, {"question_id": q2.id, "qtype": "short", "title": q2.title, "correct": True, "analysis": q2.analysis, "knowledge_point_ids": q2.knowledge_point_ids}, {"question_id": q3.id, "qtype": "judge", "title": q3.title, "correct": True, "analysis": q3.analysis, "knowledge_point_ids": q3.knowledge_point_ids}]}, started_at=now - timedelta(days=2), finished_at=now - timedelta(days=2, minutes=-18)))

    # 6) ?????
    db.add(ResearchTopic(owner_id=researcher.id, name="???????RAG?", description="?????????????????"))
    db.add(ResearchTopic(owner_id=researcher.id, name="??????????", description="??????????????"))
    db.add(ResearchTopic(owner_id=researcher.id, name="???????", description="?????PPT ???????"))
    papers = db.query(Paper).order_by(Paper.id).limit(5).all()
    for idx, paper in enumerate(papers[:5]):
        db.add(PaperReading(user_id=researcher.id, paper_id=paper.id, status="favorite" if idx == 0 else "read" if idx == 1 else "reading", progress=100 if idx < 2 else 40))
    db.add(ResearchDocument(owner_id=researcher.id, paper_id=papers[0].id if papers else None, title="RAG ????", file_path="demo://rag-summary", source="RAG ????", course_id=os_course.id, visibility="private", status="ok"))
    db.add(ResearchDocument(owner_id=researcher.id, paper_id=papers[1].id if len(papers) > 1 else None, title="???????????", file_path="demo://graph-path", source="????", course_id=os_course.id, visibility="private", status="ok"))
    db.add(Activity(user_id=researcher.id, role="researcher", kind="paper_analyze", title="AI 精读《Retrieval-Augmented Generation》"))
    db.add(Activity(user_id=researcher.id, role="researcher", kind="frontier", title="前沿探索：进程同步与并发"))

    # 7) ???????
    def make_run(def_id: str, name: str, owner_id: int, status: str, input_json: dict, output_json: dict, step_rows: list[dict]) -> None:
        run = WorkflowRun(definition_id=def_id, name=name, status=status, owner_id=owner_id, input_json=input_json, output_json=output_json, error="", created_at=now - timedelta(hours=len(step_rows) + 1), finished_at=now - timedelta(hours=len(step_rows)))
        db.add(run)
        db.flush()
        for step in step_rows:
            db.add(WorkflowStepRun(run_id=run.id, step_id=step["step_id"], label=step["label"], status=step["status"], input_json=step.get("input", {}), output_json=step.get("output", {}), error=step.get("error", ""), started_at=now - timedelta(hours=step.get("offset_start", 1)), finished_at=now - timedelta(hours=step.get("offset_end", 0))))

    make_run(
        "diagnose",
        "???????",
        teacher.id,
        "success",
        {"course_id": os_course.id},
        {"agent": {"diagnosis": {"findings": [{"issue": "??? P/V ??????", "evidence": "?????? 42%", "reason": "???????"}], "suggestions": [{"title": "?????-?????", "detail": "??????????"}], "next_lesson": ["??? P/V", "???-???"], "materials": ["?? PPT", "??? 4 ?"], "provider": "demo"}}},
        [
            {"step_id": "analytics", "label": "? ??????", "status": "success", "input": {"course_id": os_course.id}, "output": {"avg_accuracy": 52, "weak_points": ["???"]}, "offset_start": 4, "offset_end": 3},
            {"step_id": "agent", "label": "? ?? Agent ???????", "status": "success", "input": {"course_id": os_course.id}, "output": {"diagnosis": "???"}, "offset_start": 3, "offset_end": 2},
        ],
    )
    make_run(
        "preview",
        "???????",
        student.id,
        "success",
        {"course_id": os_course.id, "chapter_id": next(iter(chapters.values())).id if chapters else None},
        {"agent": preset_lecture()},
        [
            {"step_id": "retrieve", "label": "? ????????", "status": "success", "input": {"query": "???? ? 4 ?"}, "output": {"hits": 4}, "offset_start": 4, "offset_end": 3},
            {"step_id": "agent", "label": "? ?? Agent ?????", "status": "success", "input": {"chapter_id": next(iter(chapters.values())).id if chapters else None}, "output": {"objectives": ["?????"]}, "offset_start": 3, "offset_end": 2},
            {"step_id": "record", "label": "? ??????", "status": "success", "input": {"action": "preview"}, "output": {"record_id": 1}, "offset_start": 2, "offset_end": 1},
        ],
    )
    make_run(
        "lecture",
        "AI ???????",
        student.id,
        "success",
        {"course_id": os_course.id, "chapter_id": next(iter(chapters.values())).id if chapters else None, "depth": "deep"},
        {"agent": preset_lecture()},
        [
            {"step_id": "retrieve", "label": "? ???????S/A?", "status": "success", "input": {"query": "???? ? 4 ?"}, "output": {"hits": 5}, "offset_start": 4, "offset_end": 3},
            {"step_id": "branch", "label": "? ???????", "status": "success", "input": {"depth": "deep"}, "output": {"branch": "agent"}, "offset_start": 3, "offset_end": 2},
            {"step_id": "agent", "label": "? ?? Agent??????", "status": "success", "input": {"depth": "deep"}, "output": {"sections": 6}, "offset_start": 2, "offset_end": 1},
            {"step_id": "record", "label": "? ????????", "status": "success", "input": {"action": "lecture"}, "output": {"record_id": 2}, "offset_start": 1, "offset_end": 0},
        ],
    )
    make_run(
        "research_review",
        "???????",
        researcher.id,
        "success",
        {"topic": "RAG"},
        {"agent": {"summary": "???????"}},
        [
            {"step_id": "papers", "label": "? ?????", "status": "success", "input": {"topic": "RAG"}, "output": {"count": 5}, "offset_start": 3, "offset_end": 2},
            {"step_id": "branch", "label": "? ??????????", "status": "success", "input": {"papers.count": 5}, "output": {"branch": "summary"}, "offset_start": 2, "offset_end": 1},
            {"step_id": "summary", "label": "? ?? AI ?????", "status": "success", "input": {"papers": 5}, "output": {"topics": ["RAG"]}, "offset_start": 1, "offset_end": 0},
        ],
    )

    # 8) ???????????
    db.add(Activity(user_id=student.id, role="student", kind="code_submit", title="提交《生产者-消费者》：8/12 通过"))
    db.add(Activity(user_id=student.id, role="student", kind="quiz", title="第 4 章测验：9/20"))
    db.add(Activity(user_id=student.id, role="student", kind="qa", title="向 AI 导师提问：生产者-消费者问题"))
    db.add(Activity(user_id=researcher.id, role="researcher", kind="paper_analyze", title="AI 精读 RAG 论文"))
    db.add(Activity(user_id=researcher.id, role="researcher", kind="frontier", title="前沿探索：检索增强生成（RAG）"))

    db.commit()



