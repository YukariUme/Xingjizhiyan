"""课程数据访问。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Assignment, Course, Enrollment, LessonPlan, User


class CourseRepository:
    @staticmethod
    def get(db: Session, course_id: int) -> Course | None:
        return db.get(Course, course_id)

    @staticmethod
    def list_for_teacher(db: Session, teacher_id: int) -> list[Course]:
        return list(
            db.scalars(
                select(Course).where(Course.teacher_id == teacher_id).order_by(Course.id)
            )
        )

    @staticmethod
    def list_for_student(db: Session, student_id: int) -> list[Course]:
        return list(
            db.scalars(
                select(Course)
                .join(Enrollment, Enrollment.course_id == Course.id)
                .where(Enrollment.student_id == student_id)
                .order_by(Course.id)
            )
        )

    @staticmethod
    def student_ids(db: Session, course_id: int) -> list[int]:
        return list(
            db.scalars(select(Enrollment.student_id).where(Enrollment.course_id == course_id))
        )

    @staticmethod
    def student_count(db: Session, course_id: int) -> int:
        return db.scalar(
            select(func.count(Enrollment.id)).where(Enrollment.course_id == course_id)
        ) or 0

    @staticmethod
    def assignment_count(db: Session, course_id: int) -> int:
        return db.scalar(
            select(func.count(Assignment.id)).where(Assignment.course_id == course_id)
        ) or 0

    @staticmethod
    def save_lesson_plan(db: Session, plan: LessonPlan) -> LessonPlan:
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan

    @staticmethod
    def list_lesson_plans(db: Session, teacher_id: int) -> list[LessonPlan]:
        return list(
            db.scalars(
                select(LessonPlan)
                .where(LessonPlan.teacher_id == teacher_id)
                .order_by(LessonPlan.created_at.desc())
            )
        )

