"""课程章节/知识点同步：旧数据库启动时自动补建章节、知识点并建立关联。"""

from sqlalchemy.orm import Session

from app.models import Course, CourseChapter, CourseKnowledgeSpace, KnowledgePoint


def sync_curriculum(db: Session) -> dict:
    """幂等同步：为每门课程补建章节与知识空间，补充主要知识点并关联章节。"""
    from app.mock.curriculum import EXTRA_KNOWLEDGE_POINTS, FULL_CHAPTERS

    courses = db.query(Course).all()
    created_chapters = 0
    created_kps = 0
    for course in courses:
        if not db.query(CourseKnowledgeSpace).filter_by(course_id=course.id).first():
            db.add(CourseKnowledgeSpace(course_id=course.id, enabled=True, default_scope="official"))
        existing_keys = {
            ch.key for ch in db.query(CourseChapter).filter_by(course_id=course.id).all()
        }
        for index, ch in enumerate(FULL_CHAPTERS.get(course.name, []), start=1):
            if ch["key"] in existing_keys:
                continue
            db.add(
                CourseChapter(
                    course_id=course.id,
                    order=index,
                    key=ch["key"],
                    title=ch["title"],
                    official_ref=ch["official_ref"],
                    summary=ch["summary"],
                )
            )
            created_chapters += 1
    db.commit()

    existing_kps = {(kp.subject, kp.name) for kp in db.query(KnowledgePoint).all()}
    for data in EXTRA_KNOWLEDGE_POINTS:
        if (data["subject"], data["name"]) in existing_kps:
            continue
        db.add(KnowledgePoint(**data))
        created_kps += 1
    db.commit()

    # 按「课程 + 第 N 章」关联知识点到章节
    course_by_id = {c.id: c for c in db.query(Course).all()}
    chapter_map = {}
    for ch in db.query(CourseChapter).all():
        course = course_by_id.get(ch.course_id)
        if course:
            chapter_map[(course.name, ch.official_ref)] = ch
    linked = 0
    for kp in db.query(KnowledgePoint).filter(KnowledgePoint.chapter_id.is_(None)).all():
        for ch in FULL_CHAPTERS.get(kp.subject, []):
            if ch["official_ref"] in (kp.chapter or ""):
                target = chapter_map.get((kp.subject, ch["official_ref"]))
                if target:
                    kp.chapter_id = target.id
                    linked += 1
                break
    db.commit()
    return {
        "courses": len(courses),
        "created_chapters": created_chapters,
        "created_knowledge_points": created_kps,
        "linked_knowledge_points": linked,
    }

