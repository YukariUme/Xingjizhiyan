"""结构化文档数据模型：块类型、块、文档。"""

from dataclasses import dataclass, field
from enum import Enum


class BlockType(str, Enum):
    """文档块类型（同时写入 chunk metadata，供前端/检索展示）。"""

    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FORMULA = "formula"
    CODE = "code"
    LIST = "list"
    IMAGE = "image"
    PAGE_BREAK = "page_break"
    NOTE = "note"


@dataclass
class StructuredBlock:
    """一个结构化块：带类型、页码与来源信息的文本单元。"""

    block_type: BlockType
    text: str
    page: int | None = None
    language: str | None = None  # 代码块语言
    source: str = ""  # 来源：native/layout/table/formula/office
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "block_type": self.block_type.value,
            "text": self.text,
            "page": self.page,
            "language": self.language,
            "source": self.source,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StructuredBlock":
        return cls(
            block_type=BlockType(data.get("block_type", "paragraph")),
            text=data.get("text", ""),
            page=data.get("page"),
            language=data.get("language"),
            source=data.get("source", ""),
            confidence=float(data.get("confidence", 1.0)),
            metadata=data.get("metadata", {}) or {},
        )


@dataclass
class ParsedDocument:
    """解析结果：块列表 + 摘要信息。"""

    blocks: list[StructuredBlock]
    title: str = ""
    source_path: str = ""
    parser: str = ""

    def to_text(self, sep: str = "\n\n") -> str:
        """把块列表合成为可检索纯文本（表格/公式保留结构标记）。"""
        parts = []
        for block in self.blocks:
            if block.block_type in (BlockType.PAGE_BREAK, BlockType.IMAGE):
                continue
            text = block.text.strip()
            if not text:
                continue
            if block.block_type == BlockType.TABLE:
                parts.append(f"【表格】\n{text}")
            elif block.block_type == BlockType.FORMULA:
                parts.append(f"【公式】{text}")
            elif block.block_type == BlockType.CODE:
                parts.append(f"【代码】\n{text}")
            else:
                parts.append(text)
        return sep.join(parts)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "source_path": self.source_path,
            "parser": self.parser,
            "blocks": [b.to_dict() for b in self.blocks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ParsedDocument":
        return cls(
            blocks=[StructuredBlock.from_dict(b) for b in data.get("blocks", [])],
            title=data.get("title", ""),
            source_path=data.get("source_path", ""),
            parser=data.get("parser", ""),
        )
