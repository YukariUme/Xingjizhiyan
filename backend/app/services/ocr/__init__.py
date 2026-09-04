"""OCR Provider 抽象层：扫描版 PDF / 图片文字识别。"""

from app.services.ocr.base import OCRBox, OCRProvider, OCRResult
from app.services.ocr.factory import get_ocr_provider
from app.services.ocr.mock import MockOCRProvider
from app.services.ocr.paddle import PaddleOCRProvider
from app.services.ocr.rapid import RapidOCRProvider

__all__ = [
    "OCRBox",
    "OCRProvider",
    "OCRResult",
    "get_ocr_provider",
    "MockOCRProvider",
    "RapidOCRProvider",
    "PaddleOCRProvider",
]
