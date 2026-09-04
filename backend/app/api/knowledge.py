"""知识库路由：检索、文档 CRUD、分类统计、文件上传、知识点管理。"""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.config import get_settings
from app.database import get_db, utcnow
from app.models import (
    Course,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeJob,
    KnowledgePoint,
    KnowledgeReview,
    User,
)
from app.repositories.knowledge_repo import KnowledgeRepository
from app.repositories.course_repo import CourseRepository
from app.schemas.knowledge import (
    KnowledgeDocumentOut,
    KnowledgePointOut,
    SearchResult,
)
from app.services.activity_service import ActivityService
from app.services.knowledge_jobs import enqueue_job
from app.services.knowledge_service import KnowledgeService
from app.services.knowledge_service import validate_upload_header
from app.repositories.research_repo import ResearchRepository
from app.services.rag.factory import get_rag_service

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _doc_out(
    db: Session, doc: KnowledgeDocument, chunk_map: dict[int, int] | None = None
) -> KnowledgeDocumentOut:
    return KnowledgeDocumentOut(
        id=doc.id,
        title=doc.title,
        source=doc.source,
        course=doc.course,
        topic=doc.topic,
        chapter=doc.chapter,
        difficulty=doc.difficulty,
        type=doc.type,
        year=doc.year,
        content=doc.content,
        course_id=doc.course_id,
        source_level=doc.source_level,
        visibility=doc.visibility,
        owner_id=doc.owner_id,
        page=doc.page or "",
        document_type=doc.document_type or doc.type,
        size_chars=len(doc.content or ""),
        chunk_count=(chunk_map or {}).get(doc.id, 0),
        created_at=doc.created_at,
    )


@router.get("/documents", response_model=list[KnowledgeDocumentOut])
def list_documents(
    course: str | None = None,
    topic: str | None = None,
    q: str | None = None,
    type: str | None = None,
    sort: str = "time",
    order: str = "desc",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeDocumentOut]:
    service = KnowledgeService(get_rag_service())
    docs = service.list_documents(
        db, course=course, topic=topic, q=q, doc_type=type, sort=sort, order=order
    )
    chunk_map = service.chunk_counts(db, [d.id for d in docs])
    return [_doc_out(db, d, chunk_map) for d in docs]


@router.get("/documents/{doc_id}", response_model=KnowledgeDocumentOut)
def get_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeDocumentOut:
    doc = KnowledgeRepository.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return _doc_out(db, doc)


@router.get("/documents/{doc_id}/chunks", response_model=list[dict])
def document_chunks(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    chunks = db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc_id).all()
    return [
        {
            "id": c.id,
            "chunk_index": c.chunk_index,
            "text": c.text,
            "metadata": c.metadata_json,
        }
        for c in chunks
    ]


@router.post("/documents", response_model=KnowledgeDocumentOut)
def create_document(
    title: str = Form(...),
    course: str = Form(...),
    content: str = Form(...),
    source: str = Form(""),
    topic: str = Form(""),
    chapter: str = Form(""),
    difficulty: str = Form("中"),
    type: str = Form("讲义"),
    year: int = Form(2026),
    user: User = Depends(require_roles("teacher", "researcher")),
    db: Session = Depends(get_db),
) -> KnowledgeDocumentOut:
    service = KnowledgeService(get_rag_service())
    doc = service.create_document(
        db,
        {
            "title": title,
            "course": course,
            "content": content,
            "source": source,
            "topic": topic,
            "chapter": chapter,
            "difficulty": difficulty,
            "type": type,
            "year": year,
        },
        actor_id=user.id,
        actor_role=user.role,
    )
    return _doc_out(db, doc)


@router.put("/documents/{doc_id}", response_model=KnowledgeDocumentOut)
def update_document(
    doc_id: int,
    data: dict,
    user: User = Depends(require_roles("teacher", "researcher")),
    db: Session = Depends(get_db),
) -> KnowledgeDocumentOut:
    service = KnowledgeService(get_rag_service())
    doc = service.update_document(db, doc_id, data, user.id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return _doc_out(db, doc)


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    user: User = Depends(require_roles("teacher", "researcher")),
    db: Session = Depends(get_db),
):
    service = KnowledgeService(get_rag_service())
    ok = service.delete_document(db, doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文档不存在")
    ActivityService.log(db, user, "knowledge_delete", f"删除知识文档 #{doc_id}")
    return {"ok": True}


@router.post("/documents/{doc_id}/reindex")
def reindex_document(
    doc_id: int,
    user: User = Depends(require_roles("teacher", "researcher")),
    db: Session = Depends(get_db),
):
    service = KnowledgeService(get_rag_service())
    count = service.reindex(db, doc_id)
    if count == 0 and not KnowledgeRepository.get_document(db, doc_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"ok": True, "chunks": count}


@router.post("/reindex-all")
def reindex_all(
    user: User = Depends(require_roles("teacher", "researcher")),
    db: Session = Depends(get_db),
):
    """全量重建知识库索引（新增/删除文件后一键生效）。"""
    service = KnowledgeService(get_rag_service())
    docs = KnowledgeRepository.list_documents(db)
    total = 0
    for doc in docs:
        total += service.reindex(db, doc.id)
    ActivityService.log(
        db, user, "knowledge_reindex", f"全量重建知识库索引：{len(docs)} 个文档 / {total} 个切片"
    )
    return {"ok": True, "documents": len(docs), "chunks": total}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    course: str = Form(...),
    title: str | None = Form(None),
    topic: str = Form(""),
    chapter: str = Form(""),
    source: str = Form(""),
    difficulty: str = Form("中"),
    type: str = Form("讲义"),
    year: int = Form(2026),
    user: User = Depends(require_roles("teacher", "researcher")),
    db: Session = Depends(get_db),
) -> dict:
    """提交上传任务：立即返回任务号，后台异步提取/OCR/切分入库。

    支持大文件（上限 MAX_UPLOAD_MB，默认 200MB）：流式落盘后再解析，
    避免一次性把整个文件读进内存；页面通过 /api/knowledge/jobs 查看进度。
    """
    filename = file.filename or "未命名文档"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {"txt", "md", "markdown", "pdf", "ppt", "pptx", "doc", "docx"}:
        raise HTTPException(
            status_code=400,
            detail="仅支持 txt / md / pdf / pptx / docx 文件（旧版 .ppt/.doc 请另存为新格式）",
        )
    max_bytes = get_settings().max_upload_mb * 1024 * 1024

    jobs_dir = Path(get_settings().knowledge_files_dir) / "_jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = jobs_dir / f"{uuid.uuid4().hex}.{ext}"
    head = await file.read(16)
    await file.seek(0)
    try:
        validate_upload_header(filename, head)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    total = 0
    try:
        with tmp_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件超过 {get_settings().max_upload_mb}MB 限制；"
                        "可将 PDF 按章节拆分后分别上传，或先把 PDF 转为 txt 再上传。",
                    )
                out.write(chunk)
    finally:
        if total == 0:
            tmp_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="文件内容为空")
    job = KnowledgeJob(
        owner_id=user.id,
        kind="upload",
        status="pending",
        filename=filename,
        course=course,
        file_path=str(tmp_path),
        progress=0,
        message="等待处理…",
        result_json={
            "title": title or filename,
            "source": source or filename,
            "topic": topic,
            "chapter": chapter,
            "difficulty": difficulty,
            "type": type,
            "year": year,
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_job(job.id)
    return {"ok": True, "job_id": job.id, "status": job.status, "message": "已提交后台处理"}


@router.get("/import/scan")
def import_scan(
    user: User = Depends(require_roles("teacher", "researcher")),
    db: Session = Depends(get_db),
) -> dict:
    """扫描批量导入目录（backend/data/knowledge_files），列出待导入教材。"""
    return KnowledgeService(get_rag_service()).import_scan(db)


@router.get("/stats")
def knowledge_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """RAG 使用统计：文档命中次数、来源等级占比、Top 命中文档。"""
    docs = db.query(KnowledgeDocument).all()
    source_levels: dict[str, int] = {}
    total_hits = 0
    doc_stats = []
    for doc in docs:
        hits = doc.rag_hit_count or 0
        total_hits += hits
        level = doc.source_level or "S"
        source_levels[level] = source_levels.get(level, 0) + 1
        if hits > 0:
            doc_stats.append(
                {
                    "id": doc.id,
                    "title": doc.title,
                    "course": doc.course,
                    "source_level": level,
                    "hits": hits,
                }
            )
    doc_stats.sort(key=lambda d: d["hits"], reverse=True)
    return {
        "total_documents": len(docs),
        "total_hits": total_hits,
        "source_levels": source_levels,
        "top_documents": doc_stats[:15],
    }


@router.post("/import/run")
def import_run(
    data: dict,
    user: User = Depends(require_roles("teacher", "researcher")),
    db: Session = Depends(get_db),
) -> dict:
    """提交批量导入任务：后台逐个文件提取/OCR/入库，返回任务号。"""
    course = (data.get("course") or "").strip()
    filenames = data.get("files") or []
    if not course:
        raise HTTPException(status_code=400, detail="请选择课程分类")
    if not filenames:
        raise HTTPException(status_code=400, detail="请选择要导入的文件")
    folder = Path(get_settings().knowledge_files_dir)
    job = KnowledgeJob(
        owner_id=user.id,
        kind="import",
        status="pending",
        filename="、".join(filenames),
        course=course,
        file_path=str(folder),
        progress=0,
        message="等待处理…",
        result_json={"files": filenames, "course": course},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_job(job.id)
    return {"ok": True, "job_id": job.id, "status": job.status, "message": "已提交后台处理"}


@router.get("/jobs")
def list_jobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """查看自己的知识库后台任务（上传/批量导入）及进度。"""
    jobs = (
        db.query(KnowledgeJob)
        .filter(KnowledgeJob.owner_id == user.id)
        .order_by(KnowledgeJob.created_at.desc())
        .limit(30)
        .all()
    )
    return [
        {
            "id": j.id,
            "kind": j.kind,
            "status": j.status,
            "filename": j.filename,
            "course": j.course,
            "progress": j.progress,
            "message": j.message,
            "result": j.result_json,
            "error": j.error,
            "created_at": j.created_at.isoformat(),
            "updated_at": j.updated_at.isoformat(),
        }
        for j in jobs
    ]


@router.get("/reviews")
def list_reviews(
    status: str = "pending",
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> list[dict]:
    """教师查看自己课程的共享资料审核（学生申请加入课程共享）。"""
    course_ids = [c.id for c in CourseRepository.list_for_teacher(db, user.id)]
    query = (
        db.query(KnowledgeReview).filter(KnowledgeReview.course_id.in_(course_ids))
        if course_ids
        else db.query(KnowledgeReview).filter(False)
    )
    if status:
        query = query.filter(KnowledgeReview.status == status)
    reviews = query.order_by(KnowledgeReview.created_at.desc()).limit(50).all()
    items = []
    for review in reviews:
        doc = db.get(KnowledgeDocument, review.document_id)
        requester = db.get(User, review.requester_id)
        course = db.get(Course, review.course_id)
        items.append(
            {
                "id": review.id,
                "document_id": review.document_id,
                "title": doc.title if doc else "",
                "course": course.name if course else "",
                "course_id": review.course_id,
                "requester": requester.display_name if requester else "",
                "status": review.status,
                "comment": review.comment,
                "created_at": review.created_at.isoformat(),
            }
        )
    return items


@router.post("/reviews/{review_id}")
def review_document(
    review_id: int,
    data: dict,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    """审核学生共享资料：approve（进入课程共享）/ reject（驳回）/ private（仅自己）。"""
    review = db.get(KnowledgeReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="审核记录不存在")
    course = db.get(Course, review.course_id)
    if not course or course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能审核自己课程的资料")
    action = data.get("action", "approve")
    doc = db.get(KnowledgeDocument, review.document_id)
    review.reviewer_id = user.id
    review.comment = data.get("comment", "")
    review.reviewed_at = utcnow()
    if action == "approve":
        review.status = "approved"
        if doc:
            doc.visibility = "shared"
            doc.source_level = "A"
            doc.approved_by = user.id
            doc.approved_at = utcnow()
            db.add(doc)
            from app.services.rag.factory import get_rag_service

            get_rag_service().ingest_document(db, doc.id)
    elif action == "private":
        review.status = "private"
    else:
        review.status = "rejected"
    db.add(review)
    db.commit()
    return {"ok": True, "status": review.status}


@router.get("/subjects")
def subject_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return KnowledgeService(get_rag_service()).subject_stats(db, user=user)


@router.get("/topics")
def topic_options(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[str]:
    return KnowledgeService(get_rag_service()).topic_options(db)


@router.get("/points", response_model=list[KnowledgePointOut])
def list_points(
    subject: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgePointOut]:
    points = KnowledgeService(get_rag_service()).list_points(db, subject)
    return [KnowledgePointOut.model_validate(p) for p in points]


@router.get("/points/{point_id}/related")
def related_knowledge(
    point_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """课程知识点 ↔ 科研连接：返回相关论文与课程资料（支持“深入研究”/“回到课程知识”）。"""
    point = db.get(KnowledgePoint, point_id)
    if not point:
        raise HTTPException(status_code=404, detail="知识点不存在")
    papers = ResearchRepository.search_papers(db, point.name, limit=6)
    docs = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.course == point.subject)
        .limit(6)
        .all()
    )
    return {
        "knowledge_point": {
            "id": point.id,
            "name": point.name,
            "subject": point.subject,
            "chapter": point.chapter,
            "description": point.description,
            "prerequisites": point.prerequisites,
            "related_points": point.related_points,
        },
        "papers": [
            {"id": p.id, "title": p.title, "year": p.year, "venue": p.venue, "topics": p.topics}
            for p in papers
        ],
        "documents": [
            {"id": d.id, "title": d.title, "type": d.type, "source": d.source}
            for d in docs
        ],
    }


@router.post("/points", response_model=KnowledgePointOut)
def add_point(
    data: dict,
    user: User = Depends(require_roles("teacher", "researcher")),
    db: Session = Depends(get_db),
) -> KnowledgePointOut:
    point = KnowledgeService(get_rag_service()).add_point(db, data)
    return KnowledgePointOut.model_validate(point)


@router.put("/points/{point_id}/subpoints")
def update_sub_points(
    point_id: int,
    data: dict,
    user: User = Depends(require_roles("teacher", "researcher")),
    db: Session = Depends(get_db),
) -> dict:
    """保存知识点的一级/二级子知识点列表（思维导图在线编辑）。"""
    point = db.get(KnowledgePoint, point_id)
    if not point:
        raise HTTPException(status_code=404, detail="知识点不存在")
    subs = data.get("sub_points") or []
    if not isinstance(subs, list):
        raise HTTPException(status_code=400, detail="sub_points 必须是列表")
    cleaned = [
        {
            "name": str(s.get("name", "")).strip(),
            "description": str(s.get("description", "")).strip(),
            "difficulty": str(s.get("difficulty", "中")).strip() or "中",
        }
        for s in subs
        if isinstance(s, dict) and str(s.get("name", "")).strip()
    ]
    point.sub_points = cleaned
    db.add(point)
    db.commit()
    db.refresh(point)
    return {"ok": True, "id": point.id, "sub_points": point.sub_points}


@router.get("/search", response_model=list[SearchResult])
def search_knowledge(
    q: str,
    course: str | None = None,
    top_k: int = 5,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SearchResult]:
    """RAG 检索接口：返回切片 + 文档来源，供全局搜索与引用展示复用。"""
    results = get_rag_service().search(db, q, top_k=min(20, max(1, top_k)), course=course)
    return [
        SearchResult(
            chunk={
                "id": r.chunk_id,
                "document_id": 0,
                "chunk_index": 0,
                "text": r.text,
                "metadata_json": r.metadata,
            },
            document={
                "id": 0,
                "title": r.document_title,
                "source": r.document_source,
                "course": r.course,
                "topic": r.topic,
                "chapter": r.chapter,
                "difficulty": r.metadata.get("difficulty", "中"),
                "type": r.metadata.get("type", "讲义"),
                "year": r.metadata.get("year", 2026),
                "content": r.text,
            },
            score=r.score,
        )
        for r in results
    ]
