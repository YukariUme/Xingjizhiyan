"""PaddleOCR Provider（预留）：切换到 PaddleOCR 时实现同一接口。

保留原因：RapidOCR 默认离线可用；部分教材（尤其竖排、表格、公式密集）
场景下 PaddleOCR 的 PP-OCRv4 系列识别率更高，可按 OCR_PROVIDER=paddle 切换。
"""

import logging
from typing import Any

from app.services.ocr.base import OCRBox, OCRProvider, OCRResult
from app.services.ocr.rapid import _to_ndarray

logger = logging.getLogger(__name__)


class PaddleOCRProvider(OCRProvider):
    name = "paddle"

    def __init__(self, use_doc_orientation: bool = False) -> None:
        self._engine = None
        self._load_error: str | None = None
        self.use_doc_orientation = use_doc_orientation

    def _ensure(self):
        if self._engine is not None:
            return self._engine
        try:
            from paddleocr import PaddleOCR

            self._engine = PaddleOCR(
                use_doc_orientation_classify=self.use_doc_orientation,
                lang="ch",
                show_log=False,
            )
            return self._engine
        except Exception as exc:  # noqa: BLE001
            self._load_error = str(exc)
            logger.warning("PaddleOCR 初始化失败（%s），请确认已安装 paddleocr。", exc)
            return None

    def available(self) -> bool:
        return self._ensure() is not None

    def recognize(self, image: Any, *, lang: str = "ch") -> OCRResult:
        engine = self._ensure()
        if engine is None:
            raise RuntimeError(f"PaddleOCR 不可用：{self._load_error or '未知错误'}")
        result = engine.ocr(_to_ndarray(image), cls=True)
        boxes: list[OCRBox] = []
        for page in result or []:
            for item in page or []:
                pts, (text, conf) = item
                boxes.append(
                    OCRBox(
                        text=str(text),
                        confidence=float(conf),
                        box=[[float(p[0]), float(p[1])] for p in pts],
                    )
                )
        return OCRResult(
            text="\n".join(b.text for b in boxes),
            boxes=boxes,
            engine=self.name,
        )
