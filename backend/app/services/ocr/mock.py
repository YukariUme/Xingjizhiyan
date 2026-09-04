"""Mock OCR：离线演示 / 测试用，不依赖任何模型。"""

import hashlib
import re

from app.services.ocr.base import OCRBox, OCRProvider, OCRResult


class MockOCRProvider(OCRProvider):
    """确定性伪 OCR。

    真实场景不会使用；用于无模型环境下的管线演示与单元测试：
    对任意图片返回基于内容哈希的占位文本，保证流程可跑通。
    """

    name = "mock"

    def available(self) -> bool:
        return True

    def recognize(self, image, *, lang: str = "ch") -> OCRResult:
        raw = getattr(image, "tobytes", lambda: image)()
        if isinstance(raw, memoryview):
            raw = raw.tobytes()
        digest = hashlib.md5(bytes(raw)).hexdigest()
        seed = int(digest[:8], 16)
        lines = []
        for i in range(3):
            lines.append(f"[mock-ocr] 第{i + 1}行 哈希{seed % 1000}")
        boxes = [
            OCRBox(text=t, confidence=0.5, box=[[0, i * 20], [200, i * 20], [200, i * 20 + 16], [0, i * 20 + 16]])
            for i, t in enumerate(lines)
        ]
        return OCRResult(text="\n".join(lines), boxes=boxes, engine=self.name)
