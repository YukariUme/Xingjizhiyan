"""作业路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models import Assignment, Course, Question, User
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.course_repo import CourseRepository
from app.repositories.submission_repo import SubmissionRepository
from app.schemas.assignment import AssignmentIn, AssignmentOut

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


def _to_out(db: Session, assignment: Assignment) -> AssignmentOut:
    course = CourseRepository.get(db, assignment.course_id)
    return AssignmentOut(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        course_id=assignment.course_id,
        teacher_id=assignment.teacher_id,
        due_at=assignment.due_at,
        status=assignment.status,
        created_at=assignment.created_at,
        questions=assignment.questions,
        course_name=course.name if course else "",
        submitted_count=AssignmentRepository.submitted_count(db, assignment.id),
        student_count=AssignmentRepository.student_count(db, assignment.id),
    )


def _ensure_teacher_owns(user: User, db: Session, assignment_id: int) -> Assignment:
    assignment = AssignmentRepository.get(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能操作自己课程的作业")
    return assignment


@router.get("", response_model=list[AssignmentOut])
def list_assignments(
    course_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AssignmentOut]:
    if user.role == "teacher":
        assignments = AssignmentRepository.list_for_teacher(db, user.id)
        if course_id:
            assignments = [a for a in assignments if a.course_id == course_id]
    elif user.role == "student":
        course_ids = [c.id for c in CourseRepository.list_for_student(db, user.id)]
        assignments = AssignmentRepository.list_for_student(db, course_ids)
        if course_id:
            assignments = [a for a in assignments if a.course_id == course_id]
    else:
        assignments = db.query(Assignment).order_by(Assignment.created_at.desc()).all()
    return [_to_out(db, a) for a in assignments]


@router.post("", response_model=AssignmentOut)
def create_assignment(
    data: AssignmentIn,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> AssignmentOut:
    course = CourseRepository.get(db, data.course_id)
    if not course or course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能在自己课程下创建作业")
    assignment = Assignment(
        title=data.title,
        description=data.description,
        course_id=data.course_id,
        teacher_id=user.id,
        due_at=data.due_at,
        status="published",
    )
    questions = [
        Question(
            qtype=q.qtype,
            title=q.title,
            description=q.description,
            language=q.language,
            code_template=q.code_template,
            test_cases=q.test_cases,
            max_score=q.max_score,
            knowledge_point_ids=q.knowledge_point_ids,
        )
        for q in data.questions
    ]
    saved = AssignmentRepository.create(db, assignment, questions)
    return _to_out(db, saved)


@router.get("/{assignment_id}", response_model=AssignmentOut)
def get_assignment(
    assignment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssignmentOut:
    assignment = AssignmentRepository.get(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if user.role == "teacher" and assignment.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能查看自己课程的作业")
    return _to_out(db, assignment)


@router.get("/{assignment_id}/submissions")
def assignment_submissions(
    assignment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """教师查看作业的提交矩阵（学生 × 题目）。"""
    _ensure_teacher_owns(user, db, assignment_id)
    submissions = SubmissionRepository.list_by_assignment(db, assignment_id)
    student_ids = sorted({s.student_id for s in submissions})
    names = SubmissionRepository.student_names(db, student_ids)
    items = []
    for s in submissions:
        score = None
        if s.qtype == "programming" and s.code:
            score = s.code.passed_tests / max(1, s.code.total_tests) * (
                db.get(Question, s.question_id).max_score if db.get(Question, s.question_id) else 10
            )
            score = round(score, 1)
        elif s.subjective and s.subjective.teacher_score is not None:
            score = s.subjective.teacher_score
        items.append(
            {
                "submission_id": s.id,
                "assignment_id": s.assignment_id,
                "question_id": s.question_id,
                "student_id": s.student_id,
                "student_name": names.get(s.student_id, "未知学生"),
                "qtype": s.qtype,
                "status": s.status,
                "verdict": s.code.verdict if s.code else None,
                "passed_tests": s.code.passed_tests if s.code else None,
                "total_tests": s.code.total_tests if s.code else None,
                "ai_suggestion_score": s.subjective.ai_suggestion_score if s.subjective else None,
                "teacher_score": s.subjective.teacher_score if s.subjective else score,
                "created_at": s.created_at.isoformat(),
            }
        )
    return items


@router.delete("/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
):
    assignment = _ensure_teacher_owns(user, db, assignment_id)
    db.delete(assignment)
    db.commit()
    return {"ok": True}

