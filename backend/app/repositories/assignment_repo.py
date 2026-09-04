"""作业数据访问。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Assignment, Course, Enrollment, Question, Submission, User


class AssignmentRepository:
    @staticmethod
    def get(db: Session, assignment_id: int) -> Assignment | None:
        return db.get(Assignment, assignment_id)

    @staticmethod
    def list_by_course(db: Session, course_id: int) -> list[Assignment]:
        return list(
            db.scalars(
                select(Assignment).where(Assignment.course_id == course_id).order_by(Assignment.id)
            )
        )

    @staticmethod
    def list_for_student(db: Session, course_ids: list[int]) -> list[Assignment]:
        if not course_ids:
            return []
        return list(
            db.scalars(
                select(Assignment)
                .where(Assignment.course_id.in_(course_ids))
                .order_by(Assignment.due_at)
            )
        )

    @staticmethod
    def list_for_teacher(db: Session, teacher_id: int) -> list[Assignment]:
        return list(
            db.scalars(
                select(Assignment)
                .where(Assignment.teacher_id == teacher_id)
                .order_by(Assignment.created_at.desc())
            )
        )

    @staticmethod
    def create(db: Session, assignment: Assignment, questions: list[Question]) -> Assignment:
        db.add(assignment)
        db.flush()
        for q in questions:
            q.assignment_id = assignment.id
            db.add(q)
        db.commit()
        db.refresh(assignment)
        return assignment

    @staticmethod
    def submitted_count(db: Session, assignment_id: int) -> int:
        return (
            db.scalar(
                select(func.count(func.distinct(Submission.student_id))).where(
                    Submission.assignment_id == assignment_id
                )
            )
            or 0
        )

    @staticmethod
    def student_count(db: Session, assignment_id: int) -> int:
        """作业对应课程的学生人数。"""
        course_id = db.scalar(select(Assignment.course_id).where(Assignment.id == assignment_id))
        if not course_id:
            return 0
        return db.scalar(
            select(func.count(Enrollment.id)).where(Enrollment.course_id == course_id)
        ) or 0

    @staticmethod
    def question_ids(db: Session, assignment_id: int) -> list[int]:
        return list(
            db.scalars(select(Question.id).where(Question.assignment_id == assignment_id))
        )
