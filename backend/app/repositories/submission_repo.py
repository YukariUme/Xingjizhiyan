"""提交数据访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    CodeSubmission,
    Question,
    Submission,
    SubjectiveSubmission,
    User,
)


class SubmissionRepository:
    @staticmethod
    def get(db: Session, submission_id: int) -> Submission | None:
        return db.get(Submission, submission_id)

    @staticmethod
    def get_detailed(db: Session, submission_id: int) -> Submission | None:
        return db.scalar(
            select(Submission)
            .options(selectinload(Submission.code), selectinload(Submission.subjective))
            .where(Submission.id == submission_id)
        )

    @staticmethod
    def get_for_student_question(
        db: Session, question_id: int, student_id: int
    ) -> Submission | None:
        return db.scalar(
            select(Submission).where(
                Submission.question_id == question_id,
                Submission.student_id == student_id,
            )
        )

    @staticmethod
    def list_by_assignment(db: Session, assignment_id: int) -> list[Submission]:
        return list(
            db.scalars(
                select(Submission)
                .options(selectinload(Submission.code), selectinload(Submission.subjective))
                .where(Submission.assignment_id == assignment_id)
                .order_by(Submission.student_id, Submission.question_id)
            )
        )

    @staticmethod
    def list_for_student(db: Session, student_id: int) -> list[Submission]:
        return list(
            db.scalars(
                select(Submission)
                .options(selectinload(Submission.code), selectinload(Submission.subjective))
                .where(Submission.student_id == student_id)
                .order_by(Submission.updated_at.desc())
            )
        )

    @staticmethod
    def list_by_question(db: Session, question_id: int) -> list[Submission]:
        return list(
            db.scalars(
                select(Submission)
                .options(selectinload(Submission.code), selectinload(Submission.subjective))
                .where(Submission.question_id == question_id)
                .order_by(Submission.student_id)
            )
        )

    @staticmethod
    def create(db: Session, submission: Submission) -> Submission:
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission

    @staticmethod
    def update(db: Session, obj: object) -> None:
        db.add(obj)
        db.commit()

    @staticmethod
    def student_names(db: Session, student_ids: list[int]) -> dict[int, str]:
        if not student_ids:
            return {}
        rows = db.execute(select(User.id, User.display_name).where(User.id.in_(student_ids)))
        return {rid: name for rid, name in rows}

    @staticmethod
    def question_titles(db: Session, question_ids: list[int]) -> dict[int, str]:
        if not question_ids:
            return {}
        rows = db.execute(select(Question.id, Question.title).where(Question.id.in_(question_ids)))
        return {qid: title for qid, title in rows}

