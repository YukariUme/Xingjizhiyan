"""提交路由：编程题评测提交、主观题提交、学生/教师查看。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import (
    CodeSubmission,
    Question,
    Submission,
    SubjectiveSubmission,
    User,
)
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.course_repo import CourseRepository
from app.repositories.submission_repo import SubmissionRepository
from app.services.workflow.service import WorkflowService

router = APIRouter(prefix="/api", tags=["submissions"])


def _question_of(db: Session, question_id: int) -> Question:
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")
    return q


def _ensure_enrolled(db: Session, assignment_id: int, student: User) -> None:
    assignment = AssignmentRepository.get(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if student.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可以提交作业")
    enrolled = CourseRepository.student_ids(db, assignment.course_id)
    if student.id not in enrolled:
        raise HTTPException(status_code=403, detail="未选课，无法提交该作业")


def _get_or_create_submission(
    db: Session, assignment_id: int, question_id: int, student_id: int, qtype: str
) -> Submission:
    existing = SubmissionRepository.get_for_student_question(db, question_id, student_id)
    if existing:
        return existing
    return Submission(
        assignment_id=assignment_id,
        question_id=question_id,
        student_id=student_id,
        qtype=qtype,
        status="submitted",
    )


@router.post("/assignments/{assignment_id}/questions/{question_id}/submit")
def submit_answer(
    assignment_id: int,
    question_id: int,
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """提交作业。编程题自动评测；简答题自动触发 AI 建议批改（等待教师审核）。"""
    _ensure_enrolled(db, assignment_id, user)
    question = _question_of(db, question_id)
    if question.assignment_id != assignment_id:
        raise HTTPException(status_code=400, detail="题目不属于该作业")

    if question.qtype == "programming":
        if not payload.get("source_code"):
            raise HTTPException(status_code=400, detail="编程题需要提交源代码")
        source = payload["source_code"]
        language = payload.get("language", "python")
        if len(source) > 200_000:
            raise HTTPException(status_code=413, detail="代码超过 200KB 限制")
        submission = _get_or_create_submission(
            db, assignment_id, question_id, user.id, "programming"
        )
        if not submission.code:
            submission.code = CodeSubmission(submission_id=submission.id)
        submission.qtype = "programming"
        submission.code.source_code = source
        submission.code.language = language
        db.add(submission.code)
        db.add(submission)
        db.commit()
        # 交给作业闭环工作流：评测 → 保存结果 → 分支诊断 → 画像更新 → 活动记录
        run = WorkflowService.run(
            db,
            "assignment_loop",
            {
                "submission_id": submission.id,
                "qtype": "programming",
                "assignment_id": assignment_id,
                "question_id": question_id,
                "source_code": source,
                "language": language,
                "test_cases": question.test_cases,
                "question_title": question.title,
                "question_description": question.description,
            },
            user,
        )
        if run.status == "failed":
            raise HTTPException(status_code=500, detail=run.error)
        judge_out = run.output_json.get("judge", {})
        return {
            "submission_id": submission.id,
            "verdict": judge_out.get("verdict"),
            "passed_tests": judge_out.get("passed_tests"),
            "total_tests": judge_out.get("total_tests"),
            "runtime_ms": judge_out.get("runtime_ms"),
            "error_message": judge_out.get("error_message", ""),
            "judge_report": judge_out.get("judge_report", []),
            "status": judge_out.get("verdict") == "accepted" and "graded" or "submitted",
            "workflow_run_id": run.id,
            "diagnosis": run.output_json.get("diagnose", {}),
        }

    # 简答题 / 实验报告
    if not payload.get("content"):
        raise HTTPException(status_code=400, detail="简答题需要提交文本内容")
    content = payload["content"].strip()
    if not content:
        raise HTTPException(status_code=400, detail="答案内容不能为空")
    submission = _get_or_create_submission(
        db, assignment_id, question_id, user.id, question.qtype
    )
    if not submission.subjective:
        submission.subjective = SubjectiveSubmission(submission_id=submission.id)
    submission.qtype = question.qtype
    submission.subjective.content = content
    submission.status = "submitted"
    db.add(submission.subjective)
    db.add(submission)
    db.commit()
    # 交给作业闭环工作流：AI 建议批改 → 活动记录 → 等待教师审批
    run = WorkflowService.run(
        db,
        "assignment_loop",
        {
            "submission_id": submission.id,
            "qtype": question.qtype,
            "assignment_id": assignment_id,
            "question_id": question_id,
            "source_code": "",
            "language": question.language,
            "test_cases": [],
            "question_title": question.title,
            "question_description": question.description,
        },
        user,
    )
    if run.status == "failed":
        raise HTTPException(status_code=500, detail=run.error)
    return {
        "submission_id": submission.id,
        "status": submission.status,
        "ai_suggestion_score": submission.subjective.ai_suggestion_score,
        "workflow_run_id": run.id,
    }


@router.get("/me/submissions")
def my_submissions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """学生查看自己的全部提交（含成绩，仅教师确认后的成绩可见）。"""
    submissions = SubmissionRepository.list_for_student(db, user.id)
    question_ids = {s.question_id for s in submissions}
    titles = SubmissionRepository.question_titles(db, list(question_ids))
    items = []
    for s in submissions:
        score = None
        if s.qtype == "programming" and s.code:
            q = db.get(Question, s.question_id)
            score = (
                round(s.code.passed_tests / max(1, s.code.total_tests) * (q.max_score if q else 10), 1)
                if s.code.total_tests
                else None
            )
        elif s.subjective and s.subjective.teacher_score is not None:
            score = s.subjective.teacher_score
        items.append(
            {
                "submission_id": s.id,
                "assignment_id": s.assignment_id,
                "question_id": s.question_id,
                "question_title": titles.get(s.question_id, ""),
                "qtype": s.qtype,
                "status": s.status,
                "score": score,
                "verdict": s.code.verdict if s.code else None,
                "passed_tests": s.code.passed_tests if s.code else None,
                "total_tests": s.code.total_tests if s.code else None,
                "error_message": s.code.error_message if s.code else "",
                "ai_reviewed": bool(s.subjective and s.subjective.ai_suggestion_score is not None),
                "teacher_reviewed": bool(s.subjective and s.subjective.teacher_score is not None),
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
        )
    return items


@router.get("/submissions/{submission_id}")
def get_submission(
    submission_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """查看提交详情：学生只能看自己的，教师只能看自己课程的。"""
    submission = SubmissionRepository.get_detailed(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")
    assignment = AssignmentRepository.get(db, submission.assignment_id)
    question = db.get(Question, submission.question_id)
    if user.role == "student" and submission.student_id != user.id:
        raise HTTPException(status_code=403, detail="不能查看其他学生的提交")
    if user.role == "teacher" and (not assignment or assignment.teacher_id != user.id):
        raise HTTPException(status_code=403, detail="只能查看自己课程的学生提交")
    student = db.get(User, submission.student_id)
    return {
        "submission_id": submission.id,
        "assignment_id": submission.assignment_id,
        "assignment_title": assignment.title if assignment else "",
        "question_id": submission.question_id,
        "question_title": question.title if question else "",
        "question_description": question.description if question else "",
        "max_score": question.max_score if question else 10,
        "test_cases": question.test_cases if question else [],
        "qtype": submission.qtype,
        "status": submission.status,
        "student_id": submission.student_id,
        "student_name": student.display_name if student else "",
        "created_at": submission.created_at.isoformat(),
        "code": (
            {
                "source_code": submission.code.source_code,
                "language": submission.code.language,
                "verdict": submission.code.verdict,
                "passed_tests": submission.code.passed_tests,
                "total_tests": submission.code.total_tests,
                "runtime_ms": submission.code.runtime_ms,
                "error_message": submission.code.error_message,
                "judge_report": submission.code.judge_report,
            }
            if submission.code
            else None
        ),
        "subjective": (
            {
                "content": submission.subjective.content,
                "ai_suggestion_score": submission.subjective.ai_suggestion_score,
                "ai_reasoning": submission.subjective.ai_reasoning,
                "ai_knowledge_points": submission.subjective.ai_knowledge_points,
                "ai_error_analysis": submission.subjective.ai_error_analysis,
                "ai_improvement": submission.subjective.ai_improvement,
                "teacher_score": submission.subjective.teacher_score,
                "teacher_comment": submission.subjective.teacher_comment,
            }
            if submission.subjective
            else None
        ),
        "score": (
            submission.subjective.teacher_score
            if submission.subjective and submission.subjective.teacher_score is not None
            else (
                round(
                    submission.code.passed_tests / max(1, submission.code.total_tests)
                    * (question.max_score if question else 10),
                    1,
                )
                if submission.code and submission.code.total_tests
                else None
            )
        ),
    }
