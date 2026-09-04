"""OCR 工厂：按 OCR_PROVIDER 环境变量切换实现。"""

import logging

from app.config import get_settings
from app.services.ocr.base import OCRProvider

logger = logging.getLogger(__name__)


def get_ocr_provider() -> OCRProvider:
    """返回 OCR Provider。

    OCR_PROVIDER:
      - auto  : 优先 RapidOCR；引擎不可用时回退 Mock（保证管线可跑）
      - rapid : RapidOCR（ONNX，离线中文/英文）
      - paddle: PaddleOCR（需安装 paddleocr，识别率更高但体积大）
      - mock  : 确定性伪 OCR（演示/测试）
    """
    provider = get_settings().ocr_provider.lower()
    if provider == "mock":
        from app.services.ocr.mock import MockOCRProvider

        return MockOCRProvider()
    if provider == "paddle":
        from app.services.ocr.paddle import PaddleOCRProvider

        return PaddleOCRProvider()
    from app.services.ocr.rapid import RapidOCRProvider

    rapid = RapidOCRProvider()
    if provider == "rapid":
        return rapid
    # auto：不可用时回退 mock
    if not rapid.available():
        logger.warning("RapidOCR 不可用，OCR 回退为 Mock 模式（仅演示）。")
        from app.services.ocr.mock import MockOCRProvider

        return MockOCRProvider()
    return rapid
