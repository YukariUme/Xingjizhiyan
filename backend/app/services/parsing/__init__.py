"""复杂教材结构化解析管线。

路线：
  有文字层 PDF  → Native Parser（pdfplumber 表格 + 启发式公式/代码识别）
  无文字层 PDF  → RapidLayout 版面 → RapidOCR 文本 + RapidTable 表格 + 公式 OCR
  PPT/Word      → Native Parser（python-pptx / python-docx）
  ↓
  结构化文档（title/heading/paragraph/table/formula/code）
  ↓
  Chunk + Metadata（block_type / page / language / source_level...）
  ↓
  Embedding → pgvector → RAG
"""

from app.services.parsing.blocks import BlockType, ParsedDocument, StructuredBlock
from app.services.parsing.pipeline import parse_document_file

__all__ = ["BlockType", "ParsedDocument", "StructuredBlock", "parse_document_file"]
