"""OCR Provider 统一接口。

设计目标：
- 与 LLM / Embedding / Vision 抽象层保持同构，业务代码只依赖本接口；
- 提供 line 级包围盒，供 RapidLayout 版面区域 / RapidTable 表格结构复用；
- 后续切换 PaddleOCR 或接入云 OCR 时，实现同一接口即可替换。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OCRBox:
    """一行识别结果：文本 + 置信度 + 四点包围盒。"""

    text: str
    confidence: float = 0.0
    # 四点坐标 [[x0,y0],[x1,y1],[x2,y2],[x3,y3]]，左上开始顺时针
    box: list[list[float]] | None = None


@dataclass
class OCRResult:
    """整图识别结果：合并文本 + 行级明细。"""

    text: str
    boxes: list[OCRBox] = field(default_factory=list)
    engine: str = "unknown"
    elapsed_ms: float = 0.0
    detail: dict = field(default_factory=dict)


class OCRProvider(ABC):
    """OCR 提供方接口。"""

    name: str = "base"

    @abstractmethod
    def available(self) -> bool:
        """底层引擎是否可用（模型/依赖缺失时返回 False，调用方自动降级）。"""
        raise NotImplementedError

    @abstractmethod
    def recognize(self, image: Any, *, lang: str = "ch") -> OCRResult:
        """识别图片，返回合并文本与行级明细。

        image 支持：PNG/JPEG 字节串、RGB/BGR ndarray、或本地文件路径。
        """
        raise NotImplementedError

    def recognize_lines(self, image: Any, *, lang: str = "ch") -> list[OCRBox]:
        """便捷方法：只取行级结果。"""
        return self.recognize(image, lang=lang).boxes


def boxes_to_text(boxes: list[OCRBox]) -> str:
    """把行级 OCR 结果合并为段落文本（按 y 坐标排序，容忍轻微倾斜）。"""
    if not boxes:
        return ""
    ordered = sorted(
        boxes,
        key=lambda b: (round(min(p[1] for p in b.box) if b.box else 0, 0), b.box[0][0] if b.box else 0),
    )
    return "\n".join(b.text.strip() for b in ordered if b.text.strip())
