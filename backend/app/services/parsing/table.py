"""表格解析：文字层用 pdfplumber；扫描层用 RapidTable + OCR Provider。"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract_tables_pdfplumber(path: str, page_index: int) -> list[str]:
    """从 PDF 指定页提取表格，返回 Markdown 风格文本。"""
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber 未安装，跳过表格结构化提取。")
        return []
    tables = []
    try:
        with pdfplumber.open(path) as pdf:
            if page_index >= len(pdf.pages):
                return []
            page = pdf.pages[page_index]
            for table in page.extract_tables() or []:
                rows = []
                for row in table:
                    cells = [str(c).replace("\n", " ").strip() if c else "" for c in row]
                    if any(cells):
                        rows.append("| " + " | ".join(cells) + " |")
                if rows:
                    tables.append("\n".join(rows))
    except Exception as exc:  # noqa: BLE001 - 表格损坏不影响正文
        logger.warning("pdfplumber 表格提取失败（第 %d 页）：%s", page_index + 1, exc)
    return tables


def extract_table_rapid(image: Any, ocr_lines: list) -> str:
    """扫描页表格：RapidTable 版面结构 + 外部 OCR 文本 → HTML/Markdown。

    ocr_lines: OCRBox 列表（来自 OCR Provider），用于填充单元格文本。
    依赖 rapid_table + 其表格结构模型；失败时回退为简单行合并。
    """
    try:
        from rapid_table import RapidTable, RapidTableInput
        import numpy as np

        engine = RapidTable(cfg=RapidTableInput(use_ocr=False))
        # 构造 RapidTable 需要的 OCR 结果格式：(ndarray(boxes), (texts), (confs))
        boxes = np.array([[b.box] if b.box else [[0, 0]] for b in ocr_lines], dtype=np.float32) if ocr_lines else np.zeros((0, 4, 2), dtype=np.float32)
        texts = tuple(b.text for b in ocr_lines)
        confs = tuple(b.confidence for b in ocr_lines)
        output = engine([image], ocr_results=[(boxes, texts, confs)] if ocr_lines else None)
        html = (output.pred_htmls or [""])[0]
        if html.strip():
            return _html_to_markdown(html)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RapidTable 不可用（%s），回退简单行合并。", exc)
    # 回退：按行拼为管道分隔文本（保留原始行信息）
    return "\n".join(b.text for b in ocr_lines if b.text.strip())


def _html_to_markdown(html: str) -> str:
    """把 RapidTable 的 <table><tr><td> HTML 转为 Markdown 表格。"""
    import re

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)
    md_rows = []
    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)
        cleaned = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        if any(cleaned):
            md_rows.append("| " + " | ".join(cleaned) + " |")
    if not md_rows:
        return html
    if len(md_rows) >= 2:
        md_rows.insert(1, "| " + " | ".join(["---"] * (md_rows[0].count("|") // 2)) + " |")
    return "\n".join(md_rows)
