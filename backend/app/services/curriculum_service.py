"""课程学习空间服务：课程总览、章节、预习/复习、学习任务/计划/记录。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Course,
    CourseChapter,
    KnowledgeDocument,
    KnowledgePoint,
    LearningRecord,
    LearningTask,
    Quiz,
    StudentKnowledgeProfile,
    User,
)
from app.repositories.course_repo import CourseRepository
from app.repositories.learning_repo import LearningRepository
from app.services.analytics_service import AnalyticsService
from app.services.learning_path_service import LearningPathService


class CurriculumService:
    @staticmethod
    def chapters(db: Session, course_id: int) -> list[CourseChapter]:
        return list(
            db.scalars(
                select(CourseChapter)
                .where(CourseChapter.course_id == course_id)
                .order_by(CourseChapter.order)
            )
        )

    @staticmethod
    def course_kp_ids(db: Session, course_id: int) -> list[int]:
        course = db.get(Course, course_id)
        if not course:
            return []
        return list(
            db.scalars(
                select(KnowledgePoint.id).where(KnowledgePoint.subject == course.name)
            )
        )

    @staticmethod
    def chapter_kp_ids(db: Session, chapter_id: int) -> list[int]:
        return list(
            db.scalars(
                select(KnowledgePoint.id).where(KnowledgePoint.chapter_id == chapter_id)
            )
        )

    @staticmethod
    def course_overview(db: Session, student_id: int, course_id: int) -> dict:
        """课程首页：进度、掌握度、当前章节、任务、薄弱点、最近活动。"""
        course = db.get(Course, course_id)
        chapters = CurriculumService.chapters(db, course_id)
        kp_ids = CurriculumService.course_kp_ids(db, course_id)
        profiles = (
            db.query(StudentKnowledgeProfile)
            .filter(
                StudentKnowledgeProfile.student_id == student_id,
                StudentKnowledgeProfile.knowledge_point_id.in_(kp_ids),
            )
            .all()
            if kp_ids
            else []
        )
        mastery = round(sum(p.mastery or 0 for p in profiles) / max(1, len(profiles)), 1)
        weak = sorted(
            [
                {
                    "knowledge_point_id": p.knowledge_point_id,
                    "name": (
                        db.get(KnowledgePoint, p.knowledge_point_id).name
                        if db.get(KnowledgePoint, p.knowledge_point_id)
                        else f"知识点 {p.knowledge_point_id}"
                    ),
                    "mastery": p.mastery,
                }
                for p in profiles
                if (p.mastery or 0) < 60
            ],
            key=lambda x: x["mastery"],
        )
        records = (
            db.query(LearningRecord)
            .filter(LearningRecord.student_id == student_id, LearningRecord.course_id == course_id)
            .order_by(LearningRecord.created_at.desc())
            .limit(5)
            .all()
        )
        done_chapters = {
            r.chapter_id
            for r in db.query(LearningRecord)
            .filter(
                LearningRecord.student_id == student_id,
                LearningRecord.course_id == course_id,
                LearningRecord.chapter_id.isnot(None),
            )
            .all()
        }
        progress = round(100 * len(done_chapters) / max(1, len(chapters)), 1)
        last_record = records[0] if records else None
        current_chapter = None
        if last_record and last_record.chapter_id:
            ch = db.get(CourseChapter, last_record.chapter_id)
            current_chapter = {
                "id": ch.id,
                "title": ch.title,
                "official_ref": ch.official_ref,
            } if ch else None
        tasks = (
            db.query(LearningTask)
            .filter(
                LearningTask.student_id == student_id,
                LearningTask.course_id == course_id,
                LearningTask.status == "todo",
            )
            .order_by(LearningTask.due_at)
            .limit(8)
            .all()
        )
        return {
            "course_id": course_id,
            "course_name": course.name if course else "",
            "code": course.code if course else "",
            "semester": course.semester if course else "",
            "progress": progress,
            "mastery": mastery,
            "current_chapter": current_chapter,
            "chapters": [
                {
                    "id": ch.id,
                    "order": ch.order,
                    "key": ch.key,
                    "title": ch.title,
                    "official_ref": ch.official_ref,
                    "summary": ch.summary,
                    "done": ch.id in done_chapters,
                }
                for ch in chapters
            ],
            "weak_points": weak,
            "recent_records": [
                {
                    "action": r.action,
                    "detail": r.detail,
                    "created_at": r.created_at.isoformat(),
                }
                for r in records
            ],
            "pending_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "reason": t.reason,
                    "task_type": t.task_type,
                    "due_at": t.due_at.isoformat() if t.due_at else None,
                }
                for t in tasks
            ],
        }

    @staticmethod
    def chapter_view(db: Session, student_id: int, chapter_id: int) -> dict:
        """课后复习数据：本章总结、知识结构、薄弱点、错题、练习。"""
        chapter = db.get(CourseChapter, chapter_id)
        if not chapter:
            return {}
        kp_ids = CurriculumService.chapter_kp_ids(db, chapter_id)
        kps = (
            db.query(KnowledgePoint).filter(KnowledgePoint.id.in_(kp_ids)).all()
            if kp_ids
            else []
        )
        profiles = (
            db.query(StudentKnowledgeProfile)
            .filter(
                StudentKnowledgeProfile.student_id == student_id,
                StudentKnowledgeProfile.knowledge_point_id.in_(kp_ids),
            )
            .all()
            if kp_ids
            else []
        )
        weak = [
            {"name": db.get(KnowledgePoint, p.knowledge_point_id).name, "mastery": p.mastery}
            for p in profiles
            if (p.mastery or 0) < 60 and db.get(KnowledgePoint, p.knowledge_point_id)
        ]
        errors = [
            {
                "knowledge_point": db.get(KnowledgePoint, p.knowledge_point_id).name,
                "errors": p.errors,
                "mastery": p.mastery,
            }
            for p in profiles
            if (p.errors or 0) > 0 and db.get(KnowledgePoint, p.knowledge_point_id)
        ]
        return {
            "chapter_id": chapter.id,
            "title": chapter.title,
            "official_ref": chapter.official_ref,
            "summary": chapter.summary,
            "knowledge_points": [
                {
                    "id": kp.id,
                    "name": kp.name,
                    "description": kp.description,
                    "prerequisites": kp.prerequisites,
                    "related_points": kp.related_points,
                }
                for kp in kps
            ],
            "weak_points": weak,
            "errors": errors,
        }

    @staticmethod
    def record(
        db: Session,
        student_id: int,
        action: str,
        course_id: int | None = None,
        chapter_id: int | None = None,
        knowledge_point_id: int | None = None,
        detail: dict | None = None,
        duration_sec: int = 0,
    ) -> LearningRecord:
        record = LearningRecord(
            student_id=student_id,
            course_id=course_id,
            chapter_id=chapter_id,
            knowledge_point_id=knowledge_point_id,
            action=action,
            detail=detail or {},
            duration_sec=duration_sec,
        )
        db.add(record)
        db.commit()
        return record

    @staticmethod
    def list_tasks(db: Session, student_id: int, course_id: int | None = None) -> list[LearningTask]:
        query = db.query(LearningTask).filter(LearningTask.student_id == student_id)
        if course_id:
            query = query.filter(LearningTask.course_id == course_id)
        return query.order_by(LearningTask.due_at).limit(30).all()

    @staticmethod
    def complete_task(db: Session, student_id: int, task_id: int) -> bool:
        task = db.get(LearningTask, task_id)
        if not task or task.student_id != student_id:
            return False
        task.status = "done"
        db.add(task)
        db.commit()
        return True

