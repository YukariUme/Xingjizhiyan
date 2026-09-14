"""文档解析管线：按文件类型分流，输出结构化文档。

              Document Ingestion
                     │
    ┌────────────────┼────────────────┐
    ↓                ↓                ↓
  有文字层         无文字层          PPT/Word
    ↓                ↓                ↓
 Native Parser   Layout + OCR    Native Parser
    │
    ┌──────────────┼──────────────┐
    ↓              ↓              ↓
   表格            公式            代码
    ↓              ↓              ↓
 Table Parser  Formula OCR    Code Parser
    └──────────────┼──────────────┘
                   ↓
             结构化文档（StructuredBlock）
                   ↓
          Chunk + Metadata → Embedding → pgvector → RAG
"""

import logging
import re
from pathlib import Path
from typing import Callable

from app.services.parsing.blocks import BlockType, ParsedDocument, StructuredBlock
from app.services.parsing.code import detect_code_language, looks_like_code
from app.services.parsing.formula import FormulaExtractor
from app.services.parsing.layout import LayoutService
from app.services.parsing.epub import parse_epub
from app.services.parsing.office import parse_office
from app.services.parsing.table import extract_table_rapid, extract_tables_pdfplumber

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, str], None]


def parse_document_file(
    path: Path,
    progress: ProgressCallback | None = None,
    ocr_provider=None,
) -> ParsedDocument:
    """入口：按扩展名分流解析，返回结构化文档。"""
    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".markdown"}:
        return _parse_text(path)
    if ext == ".epub":
        parsed = parse_epub(path, progress=progress)
        _report(progress, 100, "EPUB 解析完成")
        return parsed
    if ext in {".pptx", ".docx", ".ppt", ".doc"}:
        parsed = parse_office(path)
        _report(progress, 100, "Office 解析完成")
        return parsed
    if ext == ".pdf":
        return _parse_pdf(path, progress=progress, ocr_provider=ocr_provider)
    raise ValueError(f"不支持的文件类型：{ext}（仅支持 txt / md / markdown / pdf / epub / pptx / docx）")


def extract_plain_text(path: Path, progress: ProgressCallback | None = None) -> str:
    """便捷方法：解析后返回纯文本（供既有 extract_text_file 复用）。"""
    return parse_document_file(path, progress=progress).to_text()


def _report(progress: ProgressCallback | None, percent: int, message: str) -> None:
    if progress:
        try:
            progress(max(0, min(100, percent)), message)
        except Exception:  # noqa: BLE001 - 进度回调异常不影响解析
            pass


def _parse_text(path: Path) -> ParsedDocument:
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks: list[StructuredBlock] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        blocks.append(_classify_text_block(para, None, "text"))
    return ParsedDocument(blocks=blocks, title=path.stem, source_path=str(path), parser="native-text")


def _classify_text_block(text: str, page: int | None, source: str) -> StructuredBlock:
    """按内容把文本块归类为 标题/代码/公式/列表/段落。"""
    if looks_like_code(text):
        return StructuredBlock(
            block_type=BlockType.CODE,
            text=text,
            page=page,
            language=detect_code_language(text) or "text",
            source=source,
        )
    if FormulaExtractor.looks_like_formula(text):
        return StructuredBlock(
            block_type=BlockType.FORMULA,
            text=text.strip("$ "),
            page=page,
            source=source,
        )
    if len(text) <= 60 and re.match(
        r"^(第[一二三四五六七八九十百0-9]+[章篇节]\s*\S+|chapter\s+\d+[.:\s]\S+|[0-9]+(\.[0-9]+){1,3}\s*\S+)",
        text,
        re.I,
    ):
        return StructuredBlock(
            block_type=BlockType.HEADING, text=text, page=page, source=source
        )
    if any(text.startswith(prefix) for prefix in ("1. ", "2. ", "3. ", "4. ", "5. ", "• ", "- ", "（1）", "(1)")):
        return StructuredBlock(block_type=BlockType.LIST, text=text, page=page, source=source)
    return StructuredBlock(block_type=BlockType.PARAGRAPH, text=text, page=page, source=source)


# ---------------------------------------------------------------------------
# PDF：有文字层 / 无文字层
# ---------------------------------------------------------------------------

def _looks_scanned(text: str, page_count: int) -> bool:
    cleaned = re.sub(r"\s+", "", text or "")
    if page_count <= 0:
        return True
    return len(cleaned) < 40 * page_count


def _parse_pdf(path: Path, progress: ProgressCallback | None, ocr_provider=None) -> ParsedDocument:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    page_count = len(reader.pages)
    text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
    if not _looks_scanned(text, page_count):
        return _parse_pdf_native(path, page_count, progress)
    return _parse_pdf_scanned(path, page_count, progress, ocr_provider)


def _parse_pdf_native(path: Path, page_count: int, progress: ProgressCallback | None) -> ParsedDocument:
    """有文字层：pypdf 正文 + pdfplumber 表格（按 bbox 剔除后保序）。"""
    from pypdf import PdfReader

    blocks: list[StructuredBlock] = []
    reader = PdfReader(str(path))
    for page_index in range(page_count):
        _report(progress, int((page_index + 1) / max(1, page_count) * 85), f"解析文字层 第{page_index + 1}/{page_count}页")
        page = reader.pages[page_index]
        page_text = page.extract_text() or ""
        table_texts: list[str] = []
        try:
            import pdfplumber

            with pdfplumber.open(str(path)) as pdf:
                if page_index < len(pdf.pages):
                    ppage = pdf.pages[page_index]
                    table_boxes = [t.bbox for t in (ppage.find_tables() or [])]
                    filtered = ppage
                    for box in table_boxes:
                        filtered = filtered.filter(
                            lambda obj, _box=box: not _obj_in_bbox(obj, _box)
                        )
                    body = (filtered.extract_text() or "").strip()
                    if body and body != page_text:
                        page_text = body
                    table_texts = extract_tables_pdfplumber(str(path), page_index)
        except Exception as exc:  # noqa: BLE001 - pdfplumber 不可用时用 pypdf 文本
            logger.debug("pdfplumber 不可用（%s），仅使用 pypdf 文本。", exc)

        page_blocks = _split_page_text(page_text, page_index + 1)
        blocks.extend(page_blocks)
        for table_text in table_texts:
            blocks.append(
                StructuredBlock(
                    block_type=BlockType.TABLE,
                    text=table_text,
                    page=page_index + 1,
                    source="pdfplumber",
                )
            )
    _report(progress, 92, "结构化文档组装完成")
    return ParsedDocument(blocks=blocks, title=path.stem, source_path=str(path), parser="native-pdf")


def _split_page_text(page_text: str, page_no: int) -> list[StructuredBlock]:
    """把单页 pypdf 文本拆块：短标题行独立成 heading，其余行合并为段落。"""
    blocks: list[StructuredBlock] = []
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            blocks.append(_classify_text_block(" ".join(buffer), page_no, "native"))
            buffer.clear()

    for line in lines:
        if len(line) <= 60 and re.match(
            r"^(第[一二三四五六七八九十百0-9]+[章篇节]\s*\S+|chapter\s+\d+[.:\s]\S+|[0-9]+(\.[0-9]+){1,3}\s*\S+)",
            line,
            re.I,
        ):
            flush()
            blocks.append(
                StructuredBlock(
                    block_type=BlockType.HEADING, text=line, page=page_no, source="native"
                )
            )
        else:
            buffer.append(line)
    flush()
    return blocks


def _obj_in_bbox(obj, bbox) -> bool:
    """判断 pdfplumber 对象是否落在表格 bbox 内。"""
    try:
        x0, top, x1, bottom = bbox
        return obj["x0"] >= x0 - 2 and obj["x1"] <= x1 + 2 and obj["top"] >= top - 2 and obj["bottom"] <= bottom + 2
    except Exception:  # noqa: BLE001
        return False


def _parse_pdf_scanned(
    path: Path,
    page_count: int,
    progress: ProgressCallback | None,
    ocr_provider=None,
) -> ParsedDocument:
    """无文字层：渲染 → RapidLayout 版面 → 分区域 OCR/表格/公式。"""
    import fitz

    if ocr_provider is None:
        from app.services.ocr.factory import get_ocr_provider

        ocr_provider = get_ocr_provider()
    layout = LayoutService()
    formula = FormulaExtractor()
    blocks: list[StructuredBlock] = []
    doc = fitz.open(str(path))
    try:
        for page_index in range(page_count):
            percent = int((page_index + 1) / max(1, page_count) * 85)
            _report(progress, percent, f"扫描版 OCR 第{page_index + 1}/{page_count}页")
            page = doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY)
            png_bytes = pix.tobytes("png")
            regions = layout.detect(png_bytes, page=page_index + 1)
            page_blocks: list[StructuredBlock] = []
            if len(regions) == 1 and regions[0].label == "text" and regions[0].box == [0, 0, 0, 0]:
                # 版面不可用：整页 OCR
                result = ocr_provider.recognize(png_bytes)
                page_blocks.extend(_group_ocr_lines(result.boxes, page_index + 1, ocr_provider.name))
            else:
                img = _png_bytes_to_cv(png_bytes)
                for region in sorted(regions, key=lambda r: (r.box[1], r.box[0])):
                    label = region.label
                    crop = _crop_region(img, region.box)
                    if label in ("table", "表格"):
                        if crop is None:
                            continue
                        result = ocr_provider.recognize(crop)
                        table_text = extract_table_rapid(crop, result.boxes)
                        if table_text.strip():
                            page_blocks.append(
                                StructuredBlock(
                                    block_type=BlockType.TABLE,
                                    text=table_text,
                                    page=page_index + 1,
                                    source="rapidtable",
                                    confidence=region.score,
                                )
                            )
                    elif label in ("formula", "formula_number"):
                        latex = formula.to_latex(crop) if crop is not None else ""
                        if latex:
                            page_blocks.append(
                                StructuredBlock(
                                    block_type=BlockType.FORMULA,
                                    text=latex,
                                    page=page_index + 1,
                                    source="rapidlatex",
                                    confidence=region.score,
                                )
                            )
                        else:
                            result = ocr_provider.recognize(crop) if crop is not None else None
                            raw = result.text.strip() if result else ""
                            if raw:
                                page_blocks.append(
                                    StructuredBlock(
                                        block_type=BlockType.FORMULA,
                                        text=raw,
                                        page=page_index + 1,
                                        source="ocr-fallback",
                                        confidence=region.score,
                                    )
                                )
                    elif label in ("figure", "image"):
                        page_blocks.append(
                            StructuredBlock(
                                block_type=BlockType.IMAGE,
                                text="",
                                page=page_index + 1,
                                source="layout",
                                confidence=region.score,
                                metadata={"region": label},
                            )
                        )
                    else:
                        result = ocr_provider.recognize(crop) if crop is not None else None
                        if result and result.text.strip():
                            page_blocks.extend(_group_ocr_lines(result.boxes, page_index + 1, ocr_provider.name))
            blocks.extend(page_blocks)
            blocks.append(
                StructuredBlock(block_type=BlockType.PAGE_BREAK, text="", page=page_index + 1, source="layout")
            )
    finally:
        doc.close()
    _report(progress, 95, "扫描版结构化完成")
    return ParsedDocument(blocks=blocks, title=path.stem, source_path=str(path), parser="layout-ocr")


def _group_ocr_lines(boxes, page_no: int, engine: str) -> list[StructuredBlock]:
    """把 OCR 行按 y 坐标聚类为段落块，再做代码/公式/标题归类。"""
    from app.services.ocr.base import boxes_to_text

    if not boxes:
        return []
    ordered = sorted(boxes, key=lambda b: (min(p[1] for p in b.box) if b.box else 0, b.box[0][0] if b.box else 0))
    groups: list[list] = []
    current: list = []
    last_y: float | None = None
    for box in ordered:
        y = min(p[1] for p in box.box) if box.box else 0
        if last_y is not None and y - last_y > 24 and current:
            groups.append(current)
            current = []
        current.append(box)
        last_y = y
    if current:
        groups.append(current)
    blocks = []
    for group in groups:
        text = boxes_to_text(group)
        if not text.strip():
            continue
        blocks.append(_classify_text_block(text.strip(), page_no, engine))
    return blocks


def _png_bytes_to_cv(png_bytes: bytes):
    import cv2
    import numpy as np

    data = np.frombuffer(png_bytes, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def _crop_region(img, box: list[float]):
    """按 RapidLayout bbox 裁切区域；越界时安全处理。"""
    import numpy as np

    if img is None or not box or len(box) < 4:
        return None
    x0, y0, x1, y1 = [int(v) for v in box]
    h, w = img.shape[:2]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    return img[y0:y1, x0:x1]
