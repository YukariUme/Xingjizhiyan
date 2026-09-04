"""课程邀请路由：学生查看/接受/拒绝邀请，教师可撤销。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.database import get_db, utcnow
from app.models import Course, CourseInvitation, Enrollment, User
from app.repositories.course_repo import CourseRepository
from app.schemas.course import CourseInvitationOut
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/api/course-invitations", tags=["course-invitations"])


def _get_invitation(db: Session, invitation_id: int) -> CourseInvitation:
    invitation = db.get(CourseInvitation, invitation_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="邀请不存在")
    return invitation


def _to_out(db: Session, invitation: CourseInvitation) -> CourseInvitationOut:
    course = db.get(Course, invitation.course_id)
    student = db.get(User, invitation.student_id)
    teacher = db.get(User, course.teacher_id) if course else None
    return CourseInvitationOut(
        id=invitation.id,
        course_id=invitation.course_id,
        course_name=course.name if course else "",
        course_code=course.code if course else "",
        semester=course.semester if course else "",
        teacher_name=teacher.display_name if teacher else "",
        student_id=invitation.student_id,
        student_name=student.display_name if student else "",
        student_username=student.username if student else "",
        status=invitation.status,
        created_at=invitation.created_at,
    )


@router.get("", response_model=list[CourseInvitationOut])
def my_invitations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CourseInvitationOut]:
    """学生查看自己待处理的课程邀请。"""
    invitations = (
        db.query(CourseInvitation)
        .filter(
            CourseInvitation.student_id == user.id,
            CourseInvitation.status == "pending",
        )
        .order_by(CourseInvitation.created_at.desc())
        .all()
    )
    return [_to_out(db, inv) for inv in invitations]


@router.post("/{invitation_id}/accept")
def accept_invitation(
    invitation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """学生接受邀请：状态置为 accepted 并创建正式选课。"""
    invitation = _get_invitation(db, invitation_id)
    if invitation.student_id != user.id:
        raise HTTPException(status_code=403, detail="只能处理自己的邀请")
    if invitation.status != "pending":
        raise HTTPException(status_code=400, detail=f"邀请已{invitation.status}，无需重复操作")
    invitation.status = "accepted"
    invitation.responded_at = utcnow()
    db.add(invitation)
    db.add(Enrollment(course_id=invitation.course_id, student_id=user.id))
    db.commit()
    course = db.get(Course, invitation.course_id)
    ActivityService.log(
        db,
        user,
        "course_accept",
        f"接受课程邀请：《{course.name if course else ''}》",
        {"course_id": invitation.course_id},
    )
    return {"ok": True, "course_id": invitation.course_id}


@router.post("/{invitation_id}/decline")
def decline_invitation(
    invitation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    invitation = _get_invitation(db, invitation_id)
    if invitation.student_id != user.id:
        raise HTTPException(status_code=403, detail="只能处理自己的邀请")
    if invitation.status != "pending":
        raise HTTPException(status_code=400, detail=f"邀请已{invitation.status}")
    invitation.status = "declined"
    invitation.responded_at = utcnow()
    db.add(invitation)
    db.commit()
    return {"ok": True}


@router.post("/{invitation_id}/cancel")
def cancel_invitation(
    invitation_id: int,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    """教师撤销待接受邀请。"""
    invitation = _get_invitation(db, invitation_id)
    course = db.get(Course, invitation.course_id)
    if not course or course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能撤销自己课程的邀请")
    if invitation.status != "pending":
        raise HTTPException(status_code=400, detail="仅待接受状态的邀请可以撤销")
    invitation.status = "cancelled"
    invitation.responded_at = utcnow()
    db.add(invitation)
    db.commit()
    return {"ok": True}
