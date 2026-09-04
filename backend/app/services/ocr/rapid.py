"""RapidOCR Provider（默认）：ONNX 本地推理，离线中文/英文识别。"""

import logging
from typing import Any

from app.services.ocr.base import OCRBox, OCRProvider, OCRResult

logger = logging.getLogger(__name__)


class RapidOCRProvider(OCRProvider):
    name = "rapid"

    def __init__(self) -> None:
        self._engine = None
        self._load_error: str | None = None

    def _ensure(self):
        if self._engine is not None:
            return self._engine
        try:
            from rapidocr_onnxruntime import RapidOCR

            self._engine = RapidOCR()
            return self._engine
        except Exception as exc:  # noqa: BLE001 - 引擎缺失/模型损坏统一降级
            self._load_error = str(exc)
            logger.warning("RapidOCR 初始化失败（%s），将回退 Mock OCR。", exc)
            return None

    def available(self) -> bool:
        return self._ensure() is not None

    def recognize(self, image: Any, *, lang: str = "ch") -> OCRResult:
        engine = self._ensure()
        if engine is None:
            raise RuntimeError(f"RapidOCR 不可用：{self._load_error or '未知错误'}")
        img = _to_ndarray(image)
        result, elapse = engine(img)
        boxes: list[OCRBox] = []
        for item in result or []:
            # RapidOCR 返回 [四点坐标, 文本, 置信度]
            pts, text, conf = item[0], item[1], float(item[2])
            boxes.append(OCRBox(text=text, confidence=conf, box=[[float(p[0]), float(p[1])] for p in pts]))
        text = "\n".join(b.text for b in boxes)
        return OCRResult(
            text=text,
            boxes=boxes,
            engine=self.name,
            elapsed_ms=float(elapse or 0) * 1000,
        )


def _to_ndarray(image: Any):
    """把 字节串/路径/ndarray 统一转为 ndarray（BGR），兼容 RapidOCR/Paddle。"""
    if hasattr(image, "shape"):  # ndarray
        return image
    import cv2
    import numpy as np

    if isinstance(image, (str, bytes)):
        data = np.frombuffer(image if isinstance(image, bytes) else open(image, "rb").read(), dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    raise TypeError(f"不支持的图片输入类型：{type(image)}")
