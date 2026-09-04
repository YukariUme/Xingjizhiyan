"""公式识别封装：RapidLaTeXOCR（可选）→ LaTeX；未安装时保留原文标记。"""

import logging
import re

logger = logging.getLogger(__name__)


class FormulaExtractor:
    """把公式区域图片转为 LaTeX 文本。

    RapidLaTeXOCR 现状（评估结论）：
    - 官方包名 rapid_latex_ocr 不在 PyPI（仓库文档与 PyPI 不一致）；
    - 需从 GitHub RapidAI/RapidLaTeXOCR 源码安装，模型另行下载（>100MB）；
    - Python >=3.13 的 PyPI 版本缺失，需源码构建。
    因此本类惰性加载、失败时保留 OCR 原文并用 $...$ 包裹，不影响整条管线。
    """

    def __init__(self) -> None:
        self._engine = None
        self._load_error: str | None = None

    def available(self) -> bool:
        return self._ensure() is not None

    def _ensure(self):
        if self._engine is not None:
            return self._engine
        try:
            from rapid_latex_ocr import LatexOCR

            self._engine = LatexOCR()
            return self._engine
        except Exception as exc:  # noqa: BLE001
            self._load_error = str(exc)
            logger.warning("RapidLaTeXOCR 不可用（%s），公式区域保留原文。", exc)
            return None

    def to_latex(self, image) -> str:
        engine = self._ensure()
        if engine is None:
            return ""
        try:
            result = engine(image)
            text = getattr(result, "text", "") or str(result)
            return text.strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("公式识别失败（%s），保留原文。", exc)
            return ""

    @staticmethod
    def looks_like_formula(text: str) -> bool:
        """启发式判断 OCR 文本是否像数学公式（文字层 PDF 用）。"""
        if not text:
            return False
        compact = re.sub(r"\s+", "", text)
        if len(compact) > 80:
            return False
        math_chars = "∑∫√∞≤≥±×÷→∈∀∃∂∇∈πθαβλμσφω"
        return (
            any(ch in compact for ch in math_chars)
            or bool(re.search(r"[a-zA-Z]\^[a-zA-Z0-9{}]|_[a-zA-Z0-9{}]", compact))
            or bool(re.fullmatch(r"[=+\-*/<>^]?[\w\s.(){}[\]+\-*/^<>=,;]+", compact) and "=" in compact)
        )
