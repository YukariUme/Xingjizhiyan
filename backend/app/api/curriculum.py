"""课程学习空间路由：学生端课程总览、预习/讲堂/复习/测验、任务/计划/记录、资料。"""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import (
    Course,
    CourseChapter,
    KnowledgeDocument,
    KnowledgePoint,
    KnowledgeReview,
    Quiz,
    QuizQuestion,
    QuizResult,
    StudentKnowledgeProfile,
    User,
)
from app.api.deps import require_roles
from app.repositories.course_repo import CourseRepository
from app.repositories.submission_repo import SubmissionRepository
from app.services.curriculum_service import CurriculumService
from app.services.knowledge_service import extract_text_file
from app.services.knowledge_service import validate_upload_header
from app.services.planner_service import PlannerService
from app.services.quiz_service import build_quiz, submit_quiz
from app.services.teaching_content_service import generate_lecture, generate_preview
from app.services.ai_meta import ai_meta, references_from_hits
from app.services.rag.factory import get_rag_service
from app.services.workflow.service import WorkflowService

router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])


def _course_or_404(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return course


def _enrolled_or_403(db: Session, user: User, course_id: int) -> None:
    if user.role == "teacher":
        course = db.get(Course, course_id)
        if course and course.teacher_id == user.id:
            return
    if user.id in CourseRepository.student_ids(db, course_id):
        return
    raise HTTPException(status_code=403, detail="未选课，无法访问该课程空间")


def _run_mode_workflow(db: Session, user: User, definition_id: str, payload: dict) -> dict:
    """运行分模式工作流，返回 Agent 输出并附工作流运行号（可追踪）。"""
    run = WorkflowService.run(db, definition_id, payload, user)
    if run.status == "failed":
        raise HTTPException(status_code=500, detail=run.error)
    content = dict(run.output_json.get("agent") or run.output_json.get("agent_standard") or {})
    content["workflow_run_id"] = run.id
    return content


@router.get("/courses")
def learning_courses(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """学生端“我的课程”卡片：进度、掌握度、当前章节、待办。"""
    courses = CourseRepository.list_for_student(db, user.id)
    items = []
    for course in courses:
        overview = CurriculumService.course_overview(db, user.id, course.id)
        items.append(
            {
                "id": course.id,
                "name": course.name,
                "code": course.code,
                "semester": course.semester,
                "description": course.description,
                "progress": overview["progress"],
                "mastery": overview["mastery"],
                "current_chapter": overview["current_chapter"],
                "pending_tasks": len(overview["pending_tasks"]),
                "weak_points": [w["name"] for w in overview["weak_points"]][:3],
                "last_study": (
                    overview["recent_records"][0]["created_at"]
                    if overview["recent_records"]
                    else None
                ),
            }
        )
    return items


@router.get("/courses/{course_id}/overview")
def course_overview(
    course_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    course = _course_or_404(db, course_id)
    _enrolled_or_403(db, user, course_id)
    return CurriculumService.course_overview(db, user.id, course_id)


@router.get("/courses/{course_id}/chapters")
def course_chapters(
    course_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    _course_or_404(db, course_id)
    _enrolled_or_403(db, user, course_id)
    return [
        {
            "id": ch.id,
            "order": ch.order,
            "key": ch.key,
            "title": ch.title,
            "official_ref": ch.official_ref,
            "summary": ch.summary,
        }
        for ch in CurriculumService.chapters(db, course_id)
    ]


@router.get("/courses/{course_id}/graph")
def knowledge_graph(
    course_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """课程知识图谱：课程 → 章节 → 知识点（含 related_points 边）→ 论文计数。"""
    course = _course_or_404(db, course_id)
    chapters = CurriculumService.chapters(db, course_id)
    points = (
        db.query(KnowledgePoint)
        .filter(KnowledgePoint.subject == course.name)
        .all()
    )
    from app.models import Paper

    paper_ids_by_kp: dict[int, list[int]] = {}
    for paper in db.query(Paper).all():
        for kp_id in paper.knowledge_point_ids or []:
            paper_ids_by_kp.setdefault(int(kp_id), []).append(paper.id)
    name_to_id = {kp.name: kp.id for kp in points}
    from app.mock.knowledge_graph import default_sub_points
    from app.models import KnowledgeDocument

    textbooks = [
        {"id": d.id, "title": d.title, "source": d.source}
        for d in db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.course == course.name)
        .all()
        if d.type == "教材" or "教材" in (d.source or "") or "教材" in (d.title or "")
    ]
    return {
        "course": {"id": course.id, "name": course.name},
        "chapters": [
            {
                "id": ch.id,
                "order": ch.order,
                "title": ch.title,
                "official_ref": ch.official_ref,
            }
            for ch in chapters
        ],
        "textbooks": textbooks,
        "points": [
            {
                "id": kp.id,
                "name": kp.name,
                "chapter_id": kp.chapter_id,
                "description": kp.description,
                "difficulty": kp.difficulty or "中",
                "prerequisites": kp.prerequisites or [],
                "prereq_ids": [name_to_id[n] for n in (kp.prerequisites or []) if n in name_to_id],
                "related_ids": [name_to_id[n] for n in (kp.related_points or []) if n in name_to_id],
                "paper_count": len(paper_ids_by_kp.get(kp.id, [])),
                "sub_points": (kp.sub_points or []) or default_sub_points(kp.name),
            }
            for kp in points
        ],
    }


@router.get("/chapters/{chapter_id}/view")
def chapter_review_view(
    chapter_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    chapter = db.get(CourseChapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return CurriculumService.chapter_view(db, user.id, chapter_id)


@router.post("/courses/{course_id}/chapters/{chapter_id}/preview")
def start_preview(
    course_id: int,
    chapter_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    course = _course_or_404(db, course_id)
    _enrolled_or_403(db, user, course_id)
    chapter = db.get(CourseChapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return _run_mode_workflow(
        db,
        user,
        "preview",
        {"course_id": course_id, "chapter_id": chapter_id, "course": course.name, "chapter": chapter.title},
    )


@router.post("/chapters/{chapter_id}/lecture")
def start_lecture(
    chapter_id: int,
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    chapter = db.get(CourseChapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    course = db.get(Course, chapter.course_id)
    depth = data.get("depth", "standard")
    return _run_mode_workflow(
        db,
        user,
        "lecture",
        {"course_id": chapter.course_id, "chapter_id": chapter_id, "depth": depth,
         "course": course.name if course else "", "chapter": chapter.title},
    )


@router.post("/chapters/{chapter_id}/review")
def start_review(
    chapter_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    chapter = db.get(CourseChapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    course = db.get(Course, chapter.course_id)
    return _run_mode_workflow(
        db,
        user,
        "review",
        {"course_id": chapter.course_id, "chapter_id": chapter_id,
         "course": course.name if course else "", "chapter": chapter.title},
    )


@router.post("/quizzes")
def create_quiz(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    course_id = int(data.get("course_id", 0))
    course = _course_or_404(db, course_id)
    _enrolled_or_403(db, user, course_id)
    return _run_mode_workflow(
        db,
        user,
        "exam_build",
        {
            "course_id": course_id,
            "chapter_id": data.get("chapter_id"),
            "quiz_type": data.get("quiz_type", "chapter"),
            "scope_kp_ids": data.get("scope_kp_ids"),
            "course": course.name,
        },
    )


@router.post("/quizzes/{quiz_id}/submit")
def submit_quiz_endpoint(
    quiz_id: int,
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    quiz = db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="测验不存在")
    return _run_mode_workflow(
        db,
        user,
        "exam_grade",
        {
            "quiz_id": quiz_id,
            "answers": data.get("answers", []),
            "course_id": quiz.course_id,
            "chapter_id": quiz.chapter_id,
        },
    )


@router.get("/tasks")
def list_tasks(
    course_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    tasks = CurriculumService.list_tasks(db, user.id, course_id)
    return [
        {
            "id": t.id,
            "title": t.title,
            "reason": t.reason,
            "task_type": t.task_type,
            "course_id": t.course_id,
            "knowledge_point_id": t.knowledge_point_id,
            "due_at": t.due_at.isoformat() if t.due_at else None,
            "status": t.status,
        }
        for t in tasks
    ]


@router.post("/tasks/generate")
def generate_tasks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    tasks = PlannerService.generate_tasks(db, user)
    return {"ok": True, "count": len(tasks)}


@router.post("/tasks/{task_id}/complete")
def complete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ok = CurriculumService.complete_task(db, user.id, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"ok": True}


@router.get("/plan")
def get_plan(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.models import LearningPlan

    plan = db.query(LearningPlan).filter(LearningPlan.student_id == user.id).order_by(LearningPlan.updated_at.desc()).first()
    if not plan:
        plan = PlannerService.generate_plan(db, user)
    return {
        "id": plan.id,
        "title": plan.title,
        "reason": plan.reason,
        "content": plan.content,
        "created_at": plan.created_at.isoformat(),
    }


@router.post("/plan/generate")
def regenerate_plan(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    plan = PlannerService.generate_plan(db, user)
    return {"ok": True, "id": plan.id}


@router.post("/records")
def add_record(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    record = CurriculumService.record(
        db,
        user.id,
        data.get("action", "study"),
        course_id=data.get("course_id"),
        chapter_id=data.get("chapter_id"),
        knowledge_point_id=data.get("knowledge_point_id"),
        detail=data.get("detail"),
        duration_sec=int(data.get("duration_sec", 0)),
    )
    return {"ok": True, "record_id": record.id}


@router.get("/courses/{course_id}/materials")
def course_materials(
    course_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """学生可见课程资料：官方(S) + 审核共享(A) + 自己的私有(P)。"""
    _course_or_404(db, course_id)
    _enrolled_or_403(db, user, course_id)
    docs = (
        db.query(KnowledgeDocument)
        .filter(
            KnowledgeDocument.course_id == course_id,
            KnowledgeDocument.visibility.in_(["official", "shared"]),
        )
        .order_by(KnowledgeDocument.created_at.desc())
        .all()
    )
    own = (
        db.query(KnowledgeDocument)
        .filter(
            KnowledgeDocument.course_id == course_id,
            KnowledgeDocument.owner_id == user.id,
            KnowledgeDocument.visibility == "private",
        )
        .all()
    )
    rows = docs + own
    return [
        {
            "id": d.id,
            "title": d.title,
            "source": d.source,
            "source_level": d.source_level,
            "visibility": d.visibility,
            "type": d.type,
            "topic": d.topic,
            "chapter": d.chapter,
            "owner_me": d.owner_id == user.id,
        }
        for d in rows
    ]


@router.post("/courses/{course_id}/materials/upload")
async def upload_course_material(
    course_id: int,
    file: UploadFile = File(...),
    scope: str = Form("private"),  # private | shared
    title: str = Form(""),
    topic: str = Form(""),
    chapter: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """学生上传课程资料：默认仅自己可见；选择“申请加入课程共享”进入教师审核。"""
    course = _course_or_404(db, course_id)
    _enrolled_or_403(db, user, course_id)
    filename = file.filename or "未命名资料"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {"txt", "md", "markdown", "pdf", "epub", "ppt", "pptx", "doc", "docx"}:
        raise HTTPException(
            status_code=400,
            detail="仅支持 txt / md / pdf / epub / pptx / docx 文件",
        )
    jobs_dir = Path(get_settings().knowledge_files_dir) / "_jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = jobs_dir / f"{uuid.uuid4().hex}.{ext}"
    head = await file.read(16)
    await file.seek(0)
    try:
        validate_upload_header(filename, head)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    total = 0
    with tmp_path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > 50 * 1024 * 1024:
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="资料超过 50MB 限制")
            out.write(chunk)
    try:
        content = extract_text_file(tmp_path)
    except Exception as exc:  # noqa: BLE001
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"文件解析失败：{exc}") from exc
    tmp_path.unlink(missing_ok=True)
    if not content.strip():
        raise HTTPException(status_code=400, detail="未能从文件中提取到文本内容")
    from app.services.knowledge_service import KnowledgeService
    from app.services.rag.factory import get_rag_service

    doc = KnowledgeService(get_rag_service()).create_document(
        db,
        {
            "title": title or filename,
            "course": course.name,
            "content": content,
            "source": filename,
            "topic": topic,
            "chapter": chapter,
            "difficulty": "中",
            "type": "共享资料" if scope == "shared" else "个人资料",
            "year": 2026,
        },
        actor_id=user.id,
        actor_role=user.role,
        source_level="P",
        visibility="private",
        owner_id=user.id,
    )
    if scope == "shared":
        review = KnowledgeReview(
            document_id=doc.id,
            course_id=course_id,
            requester_id=user.id,
            status="pending",
        )
        db.add(review)
        db.commit()
    return {
        "ok": True,
        "document_id": doc.id,
        "scope": scope,
        "review_pending": scope == "shared",
    }


# ---------- P1-2 题库管理（多题型，教师建题，章节测验/模拟/错题重测共用） ----------

QUESTION_TYPES = {"single", "multiple", "judge", "short", "code", "sql", "analysis"}


def _bank_quiz(db: Session, course_id: int) -> Quiz:
    """获取/创建课程的“题库”容器（quiz_type=bank）。"""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.course_id == course_id, Quiz.quiz_type == "bank")
        .first()
    )
    if not quiz:
        quiz = Quiz(
            course_id=course_id,
            title="课程题库",
            quiz_type="bank",
            created_by=1,
        )
        db.add(quiz)
        db.commit()
        db.refresh(quiz)
    return quiz


@router.get("/question-bank")
def list_question_bank(
    course_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """查看课程题库（教师/学生通用）。"""
    _course_or_404(db, course_id)
    bank = _bank_quiz(db, course_id)
    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == bank.id)
        .order_by(QuizQuestion.order)
        .all()
    )
    return [
        {
            "id": q.id,
            "qtype": q.qtype,
            "title": q.title,
            "options": q.options,
            "answer": q.answer,
            "analysis": q.analysis,
            "knowledge_point_ids": q.knowledge_point_ids,
            "max_score": q.max_score,
        }
        for q in questions
    ]


@router.post("/question-bank")
def create_bank_question(
    data: dict,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    """教师建题：{course_id, qtype, title, options, answer, analysis, knowledge_point_ids, max_score}。"""
    course_id = int(data.get("course_id", 0))
    _course_or_404(db, course_id)
    qtype = data.get("qtype", "single")
    if qtype not in QUESTION_TYPES:
        raise HTTPException(status_code=400, detail=f"题型不支持：{qtype}")
    bank = _bank_quiz(db, course_id)
    count = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == bank.id).count()
    question = QuizQuestion(
        quiz_id=bank.id,
        qtype=qtype,
        title=str(data.get("title", "")).strip(),
        options=data.get("options") or [],
        answer=data.get("answer") or {},
        analysis=str(data.get("analysis", "")).strip(),
        knowledge_point_ids=[int(x) for x in (data.get("knowledge_point_ids") or [])],
        max_score=float(data.get("max_score", 5)),
        order=count + 1,
    )
    if not question.title:
        raise HTTPException(status_code=400, detail="题目不能为空")
    db.add(question)
    db.commit()
    db.refresh(question)
    return {"ok": True, "id": question.id}


@router.put("/question-bank/{question_id}")
def update_bank_question(
    question_id: int,
    data: dict,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    question = db.get(QuizQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    if data.get("title") is not None:
        question.title = str(data["title"]).strip()
    if data.get("qtype") is not None:
        question.qtype = data["qtype"]
    if data.get("options") is not None:
        question.options = data["options"]
    if data.get("answer") is not None:
        question.answer = data["answer"]
    if data.get("analysis") is not None:
        question.analysis = str(data["analysis"]).strip()
    if data.get("knowledge_point_ids") is not None:
        question.knowledge_point_ids = [int(x) for x in data["knowledge_point_ids"]]
    if data.get("max_score") is not None:
        question.max_score = float(data["max_score"])
    db.add(question)
    db.commit()
    return {"ok": True}


@router.delete("/question-bank/{question_id}")
def delete_bank_question(
    question_id: int,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    question = db.get(QuizQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    db.delete(question)
    db.commit()
    return {"ok": True}


# ---------- P1-2 错题本 + 考前冲刺计划 ----------


@router.get("/wrongbook")
def wrong_book(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """按知识点聚合学生错题与错误模式（来自测验题目级记录）。"""
    results = (
        db.query(QuizResult)
        .filter(QuizResult.student_id == user.id)
        .order_by(QuizResult.finished_at.desc())
        .limit(50)
        .all()
    )
    kp_agg: dict[int, dict] = {}
    samples: list[dict] = []
    for result in results:
        details = (result.details or {}).get("questions", [])
        for q in details:
            if q.get("correct"):
                continue
            samples.append(
                {
                    "quiz_id": result.quiz_id,
                    "question_id": q.get("question_id"),
                    "qtype": q.get("qtype"),
                    "title": q.get("title", "")[:120],
                    "analysis": q.get("analysis", "")[:200],
                    "knowledge_point_ids": q.get("knowledge_point_ids", []),
                }
            )
            for kp_id in q.get("knowledge_point_ids", []):
                item = kp_agg.setdefault(
                    int(kp_id),
                    {"knowledge_point_id": int(kp_id), "name": f"知识点 {kp_id}", "count": 0, "qtypes": set()},
                )
                item["count"] += 1
                if q.get("qtype"):
                    item["qtypes"].add(q["qtype"])
    # 补充知识点名称
    for kp_id, item in kp_agg.items():
        kp = db.get(KnowledgePoint, kp_id)
        if kp:
            item["name"] = kp.name
        item["qtypes"] = sorted(item["qtypes"])
    ordered = sorted(kp_agg.values(), key=lambda x: -x["count"])
    return {
        "total_wrong": len(samples),
        "by_knowledge_point": ordered,
        "samples": samples[:30],
    }


@router.get("/sprint")
def sprint_plan(
    exam_date: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """考前冲刺计划：基于薄弱画像生成倒计时任务（可解释）。"""
    from datetime import date, datetime

    days_left = None
    if exam_date:
        try:
            days_left = max(1, (date.fromisoformat(exam_date) - date.today()).days)
        except ValueError:
            days_left = None
    profiles = (
        db.query(StudentKnowledgeProfile)
        .filter(StudentKnowledgeProfile.student_id == user.id)
        .order_by(StudentKnowledgeProfile.mastery.asc())
        .limit(10)
        .all()
    )
    weak = []
    for p in profiles:
        if (p.mastery or 0) >= 60:
            continue
        kp = db.get(KnowledgePoint, p.knowledge_point_id)
        weak.append(
            {
                "knowledge_point_id": p.knowledge_point_id,
                "name": kp.name if kp else f"知识点 {p.knowledge_point_id}",
                "mastery": p.mastery,
                "errors": p.errors,
                "reason": f"掌握度 {p.mastery:.0f}%，错误 {p.errors or 0} 次，置信度 {p.confidence:.0%}",
            }
        )
    plan = []
    for i, item in enumerate(weak, 1):
        plan.append(
            {
                "day": i,
                "task": f"复习「{item['name']}」并完成强化练习",
                "detail": item["reason"],
                "action": "章节复习 → 随堂练习 → 错题重测",
            }
        )
    return {
        "exam_date": exam_date or None,
        "days_left": days_left,
        "weak_points": weak,
        "plan": plan,
        "total_days": max(1, len(plan)),
    }
