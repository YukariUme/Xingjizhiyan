"""知识库管理服务：文档 CRUD、分类统计、切分索引与检索。"""

import re
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import utcnow
from app.models import Activity, Course, KnowledgeChunk, KnowledgeDocument, KnowledgePoint
from app.repositories.knowledge_repo import KnowledgeRepository
from app.services.parsing import parse_document_file
from app.services.rag.base import RAGService


ALLOWED_IMPORT_SUFFIXES = {
    ".txt",
    ".md",
    ".markdown",
    ".pdf",
    ".ppt",
    ".pptx",
    ".doc",
    ".docx",
}


def validate_upload_header(filename: str, head: bytes) -> None:
    """上传文件头校验：PDF/Office 魔数 + 文本编码，防止伪装文件入库。"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf" and not head.startswith(b"%PDF"):
        raise ValueError("文件头无效：不是有效的 PDF 文件")
    if ext in {"pptx", "docx"} and not head.startswith(b"PK"):
        raise ValueError("文件头无效：不是有效的 Office 文档（请确认未损坏）")
    if ext in {"txt", "md", "markdown"}:
        if b"\x00" in head:
            raise ValueError("文件头无效：文本文件包含二进制内容")

_OCR_ENGINE = None


def _ocr_engine():
    """惰性加载 OCR 引擎（RapidOCR，离线中文识别）。"""
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR

            _OCR_ENGINE = RapidOCR()
        except Exception:  # noqa: BLE001
            _OCR_ENGINE = False
    return _OCR_ENGINE


def _looks_scanned(text: str, page_count: int) -> bool:
    """按每页平均字符数判断是否为扫描版（无文字层）PDF。"""
    cleaned = re.sub(r"\s+", "", text or "")
    if page_count <= 0:
        return True
    return len(cleaned) < 40 * page_count


def _ocr_pdf_text(path: Path) -> str:
    """把扫描版 PDF 逐页渲染为图片并 OCR 识别为文本。"""
    engine = _ocr_engine()
    if not engine:
        raise ValueError(
            "扫描版 PDF 需要 OCR：请先执行 python -m pip install pymupdf rapidocr_onnxruntime"
        )
    import fitz  # PyMuPDF

    doc = fitz.open(str(path))
    parts = []
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY)
            result, _ = engine(pix.tobytes("png"))
            if result:
                parts.append("\n".join(item[1] for item in result))
    finally:
        doc.close()
    return "\n\n".join(part for part in parts if part.strip())


def extract_text_file(path: Path) -> str:
    """从 txt / md / pdf / pptx / docx 中提取文本（上传与目录批量导入共用）。

    PDF 走结构化解析管线：文字层保留表格，扫描层走 Layout + OCR；
    返回合并后的纯文本（结构化块另由 parse_document_file 提供）。
    """
    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".markdown"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if ext in {".pptx", ".docx"}:
        return parse_document_file(path).to_text()
    if ext in {".ppt", ".doc"}:
        raise ValueError(
            f"旧版 {ext} 二进制格式暂不支持解析，请先用 Office 另存为"
            f"{'.pptx' if ext == '.ppt' else '.docx'} 后再上传。"
        )
    if ext == ".pdf":
        if not get_settings().pdf_ocr_enabled:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            page_count = len(reader.pages)
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
            if _looks_scanned(text, page_count):
                raise ValueError("扫描版 PDF 未启用 OCR（PDF_OCR_ENABLED=false）")
            return text
        return parse_document_file(path).to_text()
    raise ValueError(f"不支持的文件类型：{ext}（仅支持 txt / md / pdf）")


def _extract_office_text(path: Path, ext: str) -> str:
    """解析 PPTX（逐页文字+表格）与 DOCX（段落+表格），返回可检索文本。"""
    parts: list[str] = []
    if ext == ".pptx":
        from pptx import Presentation

        prs = Presentation(str(path))
        for index, slide in enumerate(prs.slides, 1):
            slide_parts: list[str] = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    text = "\n".join(
                        para.text.strip()
                        for para in shape.text_frame.paragraphs
                        if para.text.strip()
                    )
                    if text:
                        slide_parts.append(text)
                if shape.has_table:
                    for row in shape.table.rows:
                        cells = [cell.text.strip() for cell in row.cells]
                        if any(cells):
                            slide_parts.append(" | ".join(cells))
            if slide_parts:
                parts.append(f"【第 {index} 页】\n" + "\n".join(slide_parts))
    else:  # .docx
        from docx import Document

        doc = Document(str(path))
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text.strip())
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    parts.append(" | ".join(cells))
    return "\n\n".join(parts)


def suggest_chapter_splits(text: str, max_hits: int = 30) -> list[str]:
    """从教材全文启发式识别章节标题（第X章 / Chapter X），用于拆分建议。"""
    if not text:
        return []
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) > 60:
            continue
        if re.match(r"^第[一二三四五六七八九十百0-9０-９]+[章篇]\s*\S+", line):
            lines.append(line)
        elif re.match(r"^(chapter|lesson|unit)\s+\d+[.:\s].+", line, re.I):
            lines.append(line)
    # 去重并保持顺序
    seen = set()
    out = []
    for line in lines:
        key = line.lower()[:40]
        if key not in seen:
            seen.add(key)
            out.append(line)
        if len(out) >= max_hits:
            break
    return out


class KnowledgeService:
    def __init__(self, rag: RAGService) -> None:
        self.rag = rag

    # ---------- 文档 CRUD ----------
    def list_documents(
        self,
        db: Session,
        course: str | None = None,
        topic: str | None = None,
        q: str | None = None,
        doc_type: str | None = None,
        sort: str = "time",
        order: str = "desc",
    ) -> list[KnowledgeDocument]:
        docs = KnowledgeRepository.list_documents(db, course)
        if topic:
            docs = [d for d in docs if topic.lower() in (d.topic or "").lower()]
        if doc_type:
            docs = [d for d in docs if (d.type or "") == doc_type]
        if q:
            kw = q.lower()
            docs = [
                d
                for d in docs
                if kw in (d.title or "").lower()
                or kw in (d.content or "").lower()
                or kw in (d.source or "").lower()
            ]
        reverse = order == "desc"
        if sort == "size":
            docs.sort(key=lambda d: len(d.content or ""), reverse=reverse)
        else:
            docs.sort(key=lambda d: d.created_at or utcnow(), reverse=reverse)
        return docs

    def create_document(
        self,
        db: Session,
        data: dict,
        actor_id: int,
        actor_role: str,
        source_level: str = "S",
        visibility: str = "official",
        owner_id: int | None = None,
        page: str = "",
    ) -> KnowledgeDocument:
        course_id = data.get("course_id")
        if not course_id and data.get("course"):
            course = db.scalar(select(Course).where(Course.name == data["course"]))
            course_id = course.id if course else None
        doc = KnowledgeDocument(
            title=data["title"],
            source=data.get("source", ""),
            course=data.get("course", ""),
            topic=data.get("topic", ""),
            chapter=data.get("chapter", ""),
            difficulty=data.get("difficulty", "中"),
            type=data.get("type", "讲义"),
            year=data.get("year", 2026),
            content=data.get("content", ""),
            metadata_json={
                "title": data.get("title", ""),
                "source": data.get("source", ""),
                "course": data.get("course", ""),
                "topic": data.get("topic", ""),
                "chapter": data.get("chapter", ""),
                "difficulty": data.get("difficulty", "中"),
                "type": data.get("type", "讲义"),
                "year": data.get("year", 2026),
                "blocks": data.get("blocks") or [],
            },
            course_id=course_id,
            source_level=source_level,
            visibility=visibility,
            owner_id=owner_id,
            page=page,
            document_type=data.get("type", "讲义"),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        chunk_count = self.rag.ingest_document(db, doc.id)
        db.add(
            Activity(
                user_id=actor_id,
                role=actor_role,
                kind="knowledge_create",
                title=f"新增知识文档：{doc.title}",
                detail={"document_id": doc.id, "course": doc.course, "chunks": chunk_count},
            )
        )
        db.commit()
        return doc

    def update_document(self, db: Session, doc_id: int, data: dict, actor_id: int) -> KnowledgeDocument | None:
        doc = KnowledgeRepository.get_document(db, doc_id)
        if not doc:
            return None
        for key in (
            "title", "source", "course", "topic", "chapter", "difficulty", "type", "year",
            "content", "page", "source_level", "visibility",
        ):
            if key in data:
                setattr(doc, key, data[key])
        if "course" in data:
            course = db.scalar(select(Course).where(Course.name == data["course"]))
            doc.course_id = course.id if course else None
        db.add(doc)
        db.commit()
        db.refresh(doc)
        self.rag.ingest_document(db, doc.id)
        return doc

    def delete_document(self, db: Session, doc_id: int) -> bool:
        doc = KnowledgeRepository.get_document(db, doc_id)
        if not doc:
            return False
        from app.models import KnowledgeReview

        db.query(KnowledgeReview).filter(KnowledgeReview.document_id == doc_id).delete()
        db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc_id).delete()
        db.delete(doc)
        db.commit()
        return True

    def reindex(self, db: Session, doc_id: int) -> int:
        """重新切分与向量化，返回切片数量。"""
        return self.rag.ingest_document(db, doc_id)

    # ---------- 分类统计 ----------
    def subject_stats(self, db: Session, user=None) -> list[dict]:
        """学科分类统计：与当前用户的“课程管理”完全一致。

        教师只显示自己创建的课程；其他角色显示全部课程；0 文档的新课程也列出。
        """
        from app.models import Course

        rows = db.execute(
            select(
                KnowledgeDocument.course,
                func.count(KnowledgeDocument.id).label("doc_count"),
            ).group_by(KnowledgeDocument.course)
        )
        counts = {r.course: r.doc_count for r in rows}
        query = select(Course.name)
        if user and user.role == "teacher":
            query = query.where(Course.teacher_id == user.id)
        course_names = set(db.scalars(query))
        names = sorted(set(counts) | course_names)
        return [{"course": name, "doc_count": counts.get(name, 0)} for name in names]

    def chunk_counts(self, db: Session, doc_ids: list[int]) -> dict[int, int]:
        if not doc_ids:
            return {}
        rows = db.execute(
            select(KnowledgeChunk.document_id, func.count(KnowledgeChunk.id))
            .where(KnowledgeChunk.document_id.in_(doc_ids))
            .group_by(KnowledgeChunk.document_id)
        )
        return {doc_id: count for doc_id, count in rows}

    def topic_options(self, db: Session) -> list[str]:
        rows = db.execute(
            select(KnowledgeDocument.topic).distinct().order_by(KnowledgeDocument.topic)
        )
        return [r.topic for r in rows if r.topic]

    def list_points(self, db: Session, subject: str | None = None) -> list[KnowledgePoint]:
        return KnowledgeRepository.list_points(db, subject)

    def add_point(self, db: Session, data: dict) -> KnowledgePoint:
        point = KnowledgePoint(
            name=data["name"],
            subject=data.get("subject", ""),
            chapter=data.get("chapter", ""),
            difficulty=data.get("difficulty", "中"),
            description=data.get("description", ""),
            prerequisites=data.get("prerequisites", []),
        )
        db.add(point)
        db.commit()
        db.refresh(point)
        return point

    # ---------- 目录批量导入 ----------
    def import_scan(self, db: Session) -> dict:
        """扫描批量导入目录，列出可导入文件与导入状态。"""
        folder = Path(get_settings().knowledge_files_dir)
        folder.mkdir(parents=True, exist_ok=True)
        files = []
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.suffix.lower() not in ALLOWED_IMPORT_SUFFIXES:
                continue
            imported = (
                db.query(KnowledgeDocument)
                .filter(KnowledgeDocument.source == path.name)
                .first()
            )
            files.append(
                {
                    "filename": path.name,
                    "size_mb": round(path.stat().st_size / 1024 / 1024, 1),
                    "imported": imported is not None,
                    "document_id": imported.id if imported else None,
                }
            )
        return {"dir": str(folder), "files": files}

    def import_run(
        self, db: Session, course: str, filenames: list[str], actor_id: int, actor_role: str
    ) -> dict:
        """把目录中的教材文件导入知识库并按课程归档。"""
        folder = Path(get_settings().knowledge_files_dir)
        results = []
        for filename in filenames:
            path = folder / filename
            if not path.is_file():
                results.append({"filename": filename, "status": "skipped", "reason": "文件不存在"})
                continue
            if (
                db.query(KnowledgeDocument)
                .filter(KnowledgeDocument.source == filename)
                .first()
            ):
                results.append({"filename": filename, "status": "skipped", "reason": "已导入"})
                continue
            try:
                content = extract_text_file(path)
                if not content.strip():
                    results.append({"filename": filename, "status": "failed", "reason": "未能提取到文本（可能是扫描版 PDF）"})
                    continue
                doc = self.create_document(
                    db,
                    {
                        "title": path.stem,
                        "course": course,
                        "content": content,
                        "source": filename,
                        "topic": "",
                        "chapter": "",
                        "difficulty": "中",
                        "type": "教材",
                        "year": 2026,
                    },
                    actor_id=actor_id,
                    actor_role=actor_role,
                )
                results.append(
                    {
                        "filename": filename,
                        "status": "imported",
                        "document_id": doc.id,
                        "title": doc.title,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                results.append({"filename": filename, "status": "failed", "reason": str(exc)})
        return {"course": course, "results": results}
