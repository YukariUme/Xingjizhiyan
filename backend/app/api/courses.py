"""课程路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.database import utcnow
from app.models import (
    Assignment,
    CodeSubmission,
    Course,
    CourseInvitation,
    Enrollment,
    Evaluation,
    Feedback,
    Question,
    Submission,
    SubjectiveSubmission,
    User,
    WorkflowRun,
)
from app.repositories.course_repo import CourseRepository
from app.repositories.user_repo import UserRepository
from app.schemas.course import CourseIn, CourseInvitationOut, CourseOut
from app.schemas.user import UserOut
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _to_out(db: Session, course: Course) -> CourseOut:
    return CourseOut(
        id=course.id,
        name=course.name,
        code=course.code,
        description=course.description,
        semester=course.semester,
        teacher_id=course.teacher_id,
        created_at=course.created_at,
        student_count=CourseRepository.student_count(db, course.id),
        assignment_count=CourseRepository.assignment_count(db, course.id),
        pending_count=(
            db.query(CourseInvitation)
            .filter(
                CourseInvitation.course_id == course.id,
                CourseInvitation.status == "pending",
            )
            .count()
        ),
    )


@router.get("", response_model=list[CourseOut])
def list_courses(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CourseOut]:
    """按角色返回课程：教师看自己课程，学生看已选课程，科研用户看全部公开课程。"""
    if user.role == "teacher":
        courses = CourseRepository.list_for_teacher(db, user.id)
    elif user.role == "student":
        courses = CourseRepository.list_for_student(db, user.id)
    else:
        courses = db.query(Course).order_by(Course.id).all()
    return [_to_out(db, c) for c in courses]


@router.post("", response_model=CourseOut)
def create_course(
    data: CourseIn,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> CourseOut:
    course = Course(
        name=data.name,
        code=data.code,
        description=data.description,
        semester=data.semester,
        teacher_id=user.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return _to_out(db, course)


@router.get("/{course_id}", response_model=CourseOut)
def get_course(
    course_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CourseOut:
    course = CourseRepository.get(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if user.role == "teacher" and course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能查看自己课程的详情")
    return _to_out(db, course)


@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    """删除课程（连同选课、作业、题目与提交数据；仅限课程创建教师）。"""
    course = CourseRepository.get(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能删除自己创建的课程")

    assignment_ids = [
        aid for (aid,) in db.query(Assignment.id).filter(Assignment.course_id == course_id)
    ]
    question_ids = (
        [qid for (qid,) in db.query(Question.id).filter(Question.assignment_id.in_(assignment_ids))]
        if assignment_ids
        else []
    )
    submission_ids = (
        [sid for (sid,) in db.query(Submission.id).filter(Submission.question_id.in_(question_ids))]
        if question_ids
        else []
    )
    if submission_ids:
        db.query(CodeSubmission).filter(CodeSubmission.submission_id.in_(submission_ids)).delete()
        db.query(SubjectiveSubmission).filter(
            SubjectiveSubmission.submission_id.in_(submission_ids)
        ).delete()
        db.query(Evaluation).filter(Evaluation.submission_id.in_(submission_ids)).delete()
        db.query(Feedback).filter(Feedback.submission_id.in_(submission_ids)).delete()
        db.query(WorkflowRun).filter(WorkflowRun.submission_id.in_(submission_ids)).delete()
        db.query(Submission).filter(Submission.id.in_(submission_ids)).delete()
    if question_ids:
        db.query(Question).filter(Question.id.in_(question_ids)).delete()
    if assignment_ids:
        db.query(Assignment).filter(Assignment.id.in_(assignment_ids)).delete()
    db.query(Enrollment).filter(Enrollment.course_id == course_id).delete()
    db.query(CourseInvitation).filter(CourseInvitation.course_id == course_id).delete()
    db.delete(course)
    db.commit()
    ActivityService.log(db, user, "course_delete", f"删除课程：{course.name}")
    return {"ok": True, "deleted_course_id": course_id}


@router.get("/{course_id}/students", response_model=list[UserOut])
def course_students(
    course_id: int,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    """查看课程已选学生。"""
    course = CourseRepository.get(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能查看自己课程的学生")
    student_ids = CourseRepository.student_ids(db, course_id)
    students = db.query(User).filter(User.id.in_(student_ids)).all() if student_ids else []
    return [UserOut.model_validate(s) for s in students]


@router.post("/{course_id}/invite")
def invite_student(
    course_id: int,
    data: dict,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    """教师按用户名邀请已注册学生：生成待接受邀请，学生接受后才算选课。"""
    course = CourseRepository.get(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能管理自己课程的学生")
    username = (data.get("student_username") or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="请输入学生用户名")
    student = UserRepository.get_by_username(db, username)
    if not student or student.role != "student":
        raise HTTPException(status_code=404, detail=f"未找到学生账号：{username}")
    enrolled = (
        db.query(Enrollment)
        .filter(Enrollment.course_id == course_id, Enrollment.student_id == student.id)
        .first()
    )
    if enrolled:
        raise HTTPException(status_code=400, detail=f"学生 {student.display_name} 已在课程中")
    invitation = (
        db.query(CourseInvitation)
        .filter(
            CourseInvitation.course_id == course_id,
            CourseInvitation.student_id == student.id,
        )
        .first()
    )
    if invitation and invitation.status == "pending":
        raise HTTPException(
            status_code=400, detail=f"已向 {student.display_name} 发出邀请，等待接受"
        )
    if invitation:
        invitation.status = "pending"
        invitation.responded_at = None
        db.add(invitation)
    else:
        invitation = CourseInvitation(course_id=course_id, student_id=student.id, status="pending")
        db.add(invitation)
    db.commit()
    ActivityService.log(
        db,
        user,
        "course_invite",
        f"邀请 {student.display_name} 加入课程《{course.name}》（待接受）",
        {"course_id": course_id, "student_id": student.id},
    )
    db.refresh(invitation)
    return {
        "ok": True,
        "student": UserOut.model_validate(student),
        "invitation": {
            "id": invitation.id,
            "course_id": invitation.course_id,
            "student_id": invitation.student_id,
            "status": invitation.status,
        },
    }


@router.get("/{course_id}/invitations", response_model=list[CourseInvitationOut])
def course_invitations(
    course_id: int,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> list[CourseInvitationOut]:
    """教师查看课程的邀请记录（含学生信息）。"""
    course = CourseRepository.get(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能查看自己课程的邀请")
    rows = (
        db.query(CourseInvitation, User)
        .join(User, User.id == CourseInvitation.student_id)
        .filter(CourseInvitation.course_id == course_id)
        .order_by(CourseInvitation.created_at.desc())
        .all()
    )
    return [
        CourseInvitationOut(
            id=inv.id,
            course_id=inv.course_id,
            course_name=course.name,
            course_code=course.code,
            semester=course.semester,
            teacher_name=user.display_name,
            student_id=inv.student_id,
            student_name=stu.display_name,
            student_username=stu.username,
            status=inv.status,
            created_at=inv.created_at,
        )
        for inv, stu in rows
    ]
