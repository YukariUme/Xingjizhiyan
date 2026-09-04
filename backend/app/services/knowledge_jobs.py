"""知识库后台任务：上传/批量导入异步处理，回报进度，避免阻塞页面。"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import KnowledgeDocument, KnowledgeJob, User
from app.services.knowledge_service import (
    KnowledgeService,
    suggest_chapter_splits,
)
from app.services.parsing import parse_document_file
from app.services.rag.factory import get_rag_service


_JOB_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kb-job")
_OCR_LOCAL = threading.local()
_OCR_PAGE_WORKERS = max(1, min(4, (os.cpu_count() or 2) - 1))


def enqueue_job(job_id: int) -> None:
    """把任务提交到后台单线程队列（串行处理，避免 SQLite 写冲突）。"""
    _JOB_EXECUTOR.submit(_run_job, job_id)


def _run_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        _process_job(db, job_id)
    except Exception as exc:  # noqa: BLE001
        try:
            job = db.get(KnowledgeJob, job_id)
            if job:
                job.status = "failed"
                job.error = str(exc)
                job.message = "处理失败"
                db.add(job)
                db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
    finally:
        db.close()


def _process_job(db: Session, job_id: int) -> None:
    job = db.get(KnowledgeJob, job_id)
    if not job:
        return
    job.status = "running"
    job.message = "排队处理中…"
    _commit(db, job)
    if job.kind == "upload":
        _process_upload(db, job)
    else:
        _process_import(db, job)


def _commit(db: Session, job: KnowledgeJob) -> None:
    db.add(job)
    try:
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()


def _update(db: Session, job: KnowledgeJob, progress: int | None = None, message: str | None = None) -> None:
    if progress is not None:
        job.progress = max(0, min(100, int(progress)))
    if message is not None:
        job.message = message
    _commit(db, job)


def _process_upload(db: Session, job: KnowledgeJob) -> None:
    path = Path(job.file_path)
    if not path.is_file():
        raise FileNotFoundError("上传的临时文件不存在")
    parsed = _parse_with_progress(path, lambda p, m: _update(db, job, p, m))
    content = parsed.to_text()
    owner = db.get(User, job.owner_id)
    meta = job.result_json or {}
    _update(db, job, 96, "切分并建立索引…")
    doc = KnowledgeService(get_rag_service()).create_document(
        db,
        {
            "title": meta.get("title") or path.stem,
            "course": job.course,
            "content": content,
            "blocks": parsed.to_dict().get("blocks", []),
            "source": meta.get("source") or job.filename,
            "topic": meta.get("topic", ""),
            "chapter": meta.get("chapter", ""),
            "difficulty": meta.get("difficulty", "中"),
            "type": meta.get("type", "讲义"),
            "year": int(meta.get("year", 2026)),
        },
        actor_id=job.owner_id,
        actor_role=owner.role if owner else "teacher",
    )
    job.result_json = {
        "document_id": doc.id,
        "title": doc.title,
        "course": doc.course,
    }
    job.status = "success"
    job.progress = 100
    job.message = f"完成：{doc.title}"
    _commit(db, job)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _process_import(db: Session, job: KnowledgeJob) -> None:
    files = job.result_json.get("files") or []
    results = []
    for index, filename in enumerate(files):
        path = Path(job.file_path) / filename
        if not path.is_file():
            results.append({"filename": filename, "status": "skipped", "reason": "文件不存在"})
            continue
        if db.query(KnowledgeDocument).filter(KnowledgeDocument.source == filename).first():
            results.append({"filename": filename, "status": "skipped", "reason": "已导入"})
            continue
        base = int(index * 100 / max(1, len(files)))
        try:
            parsed = _parse_with_progress(
                path,
                lambda p, m, base=base: _update(
                    db, job, base + int(p * (100 / max(1, len(files)))), f"处理 {filename}：{m}"
                ),
            )
            content = parsed.to_text()
            if not content.strip():
                results.append({"filename": filename, "status": "failed", "reason": "未能提取到文本（可能是扫描版且 OCR 失败）"})
                continue
            doc = KnowledgeService(get_rag_service()).create_document(
                db,
                {
                    "title": path.stem,
                    "course": job.course,
                    "content": content,
                    "blocks": parsed.to_dict().get("blocks", []),
                    "source": filename,
                    "topic": "",
                    "chapter": "",
                    "difficulty": "中",
                    "type": "教材",
                    "year": 2026,
                },
                actor_id=job.owner_id,
                actor_role="teacher",
            )
            results.append(
                {
                    "filename": filename,
                    "status": "imported",
                    "document_id": doc.id,
                    "title": doc.title,
                    "suggested_chapters": suggest_chapter_splits(content),
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append({"filename": filename, "status": "failed", "reason": str(exc)})
    job.result_json = {"course": job.course, "results": results}
    job.status = "success"
    job.progress = 100
    job.message = f"导入完成：{sum(1 for r in results if r['status'] == 'imported')}/{len(files)} 个文件"
    _commit(db, job)


def _extract_with_progress(path: Path, on_progress) -> str:
    """提取文本并回报进度（兼容旧调用方）。"""
    return _parse_with_progress(path, on_progress).to_text()


def _parse_with_progress(path: Path, on_progress):
    """结构化解析并回报进度；扫描版 PDF 走 Layout + OCR 管线。"""
    return parse_document_file(path, progress=on_progress)


def _ocr_pdf_parallel(path: Path, page_count: int, on_progress) -> str:
    """渲染页面后用多线程并行 OCR，逐页回报进度。"""
    import fitz

    on_progress(5, "渲染页面图片…")
    doc = fitz.open(str(path))
    images: list[bytes] = []
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), colorspace=fitz.csGRAY)
            images.append(pix.tobytes("png"))
    finally:
        doc.close()

    done = [0]
    results: dict[int, str] = {}
    lock = threading.Lock()

    def worker(index: int, png: bytes) -> None:
        engine = _get_ocr_engine()
        page_text = ""
        try:
            result, _ = engine(png)
            if result:
                page_text = "\n".join(item[1] for item in result)
        except Exception:  # noqa: BLE001
            page_text = ""
        with lock:
            results[index] = page_text
            done[0] += 1
            on_progress(
                5 + int(done[0] * 90 / max(1, page_count)),
                f"OCR 识别 {done[0]}/{page_count} 页",
            )

    with ThreadPoolExecutor(max_workers=_OCR_PAGE_WORKERS) as pool:
        futures = [pool.submit(worker, i, png) for i, png in enumerate(images)]
        for future in futures:
            future.result()
    return "\n\n".join(results.get(i, "") for i in range(len(images)) if results.get(i, "").strip())


def _get_ocr_engine():
    if not hasattr(_OCR_LOCAL, "engine"):
        from rapidocr_onnxruntime import RapidOCR

        _OCR_LOCAL.engine = RapidOCR()
    return _OCR_LOCAL.engine
