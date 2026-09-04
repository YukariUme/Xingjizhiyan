"""批改路由：AI 建议批改 + 教师确认最终成绩。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models import Assignment, Question, Submission, User
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.submission_repo import SubmissionRepository
from app.schemas.submission import TeacherReviewIn
from app.services.activity_service import ActivityService
from app.services.grading_service import GradingService
from app.services.llm.factory import get_llm_service
from app.services.prompt import PromptService
from app.services.rag.factory import get_rag_service
from app.services.workflow.service import WorkflowService

router = APIRouter(prefix="/api", tags=["grading"])


def _teacher_submission(db: Session, user: User, submission_id: int) -> Submission:
    submission = SubmissionRepository.get_detailed(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")
    assignment = AssignmentRepository.get(db, submission.assignment_id)
    if not assignment or assignment.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能批改自己课程的学生提交")
    return submission


@router.get("/grading/worklist")
def grading_worklist(
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> list[dict]:
    """教师批改工作台：自己课程下所有待批改主观题提交。"""
    assignments = AssignmentRepository.list_for_teacher(db, user.id)
    items = []
    student_ids: set[int] = set()
    question_ids: set[int] = set()
    submissions = []
    for a in assignments:
        submissions.extend(SubmissionRepository.list_by_assignment(db, a.id))
    for s in submissions:
        if s.qtype == "programming" or not s.subjective:
            continue
        student_ids.add(s.student_id)
        question_ids.add(s.question_id)
    names = SubmissionRepository.student_names(db, list(student_ids))
    titles = SubmissionRepository.question_titles(db, list(question_ids))
    for s in submissions:
        if s.qtype == "programming" or not s.subjective:
            continue
        a = AssignmentRepository.get(db, s.assignment_id)
        items.append(
            {
                "submission_id": s.id,
                "assignment_id": s.assignment_id,
                "assignment_title": a.title if a else "",
                "question_title": titles.get(s.question_id, ""),
                "qtype": s.qtype,
                "student_id": s.student_id,
                "student_name": names.get(s.student_id, "未知学生"),
                "status": s.status,
                "submitted_at": s.created_at.isoformat(),
                "ai_suggestion_score": s.subjective.ai_suggestion_score,
                "teacher_score": s.subjective.teacher_score,
                "ai_reviewed": s.subjective.ai_suggestion_score is not None,
            }
        )
    items.sort(key=lambda x: (x["status"] != "submitted", x["submitted_at"]))
    return items


@router.post("/submissions/{submission_id}/ai-review")
def ai_review_submission(
    submission_id: int,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    """触发/刷新 AI 建议批改（建议分仅供参考，需教师确认）。"""
    submission = _teacher_submission(db, user, submission_id)
    if submission.qtype == "programming":
        raise HTTPException(status_code=400, detail="编程题为自动评测，无需 AI 建议批改")
    grading = GradingService(llm=get_llm_service(), rag=get_rag_service(), prompts=PromptService())
    subj = grading.ai_review(db, submission)
    if not subj:
        raise HTTPException(status_code=400, detail="该提交没有文本内容")
    ActivityService.log(
        db,
        user,
        "ai_review",
        f"AI 建议批改《{db.get(Question, submission.question_id).title if db.get(Question, submission.question_id) else ''}》：建议 {subj.ai_suggestion_score} 分",
        {"submission_id": submission.id},
    )
    return {
        "suggestion_score": subj.ai_suggestion_score,
        "reasoning": subj.ai_reasoning,
        "knowledge_points": subj.ai_knowledge_points,
        "errors": subj.ai_error_analysis,
        "improvement": subj.ai_improvement,
        "status": submission.status,
    }


@router.post("/submissions/{submission_id}/grade")
def teacher_grade(
    submission_id: int,
    data: TeacherReviewIn,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    """教师确认最终分数与评语（学生之后才能看到正式成绩）。"""
    submission = _teacher_submission(db, user, submission_id)
    question = db.get(Question, submission.question_id)
    max_score = question.max_score if question else 10
    final_score = min(max_score, max(0.0, data.final_score))
    grading = GradingService(llm=get_llm_service(), rag=get_rag_service(), prompts=PromptService())
    grading.teacher_review(db, submission, final_score, data.comment, user)
    # 完成作业闭环工作流的人工审批节点
    run = WorkflowService.find_run_for_submission(db, submission.id)
    if run and run.status == "awaiting_approval":
        WorkflowService.approve(
            db, run.id, user, {"final_score": final_score, "comment": data.comment}
        )
    return {
        "submission_id": submission.id,
        "status": "graded",
        "final_score": final_score,
        "comment": data.comment,
        "workflow_run_id": run.id if run else None,
    }
