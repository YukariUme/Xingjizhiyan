"""版面分析（RapidLayout）封装：扫描版 PDF 页面 → 区域级标签。"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LayoutRegion:
    label: str
    box: list[float]  # [x1, y1, x2, y2]
    score: float = 0.0
    page: int | None = None


class LayoutService:
    """RapidLayout 版面检测；模型缺失/加载失败时返回整页 text 区域。"""

    # CDLA 标签：title / text / table / figure / formula / header / footer...
    TEXT_LABELS = {"title", "text", "paragraph", "list", "header", "footer", "note", "abstract"}

    def __init__(self) -> None:
        self._engine = None
        self._load_error: str | None = None

    def available(self) -> bool:
        return self._ensure() is not None

    def _ensure(self):
        if self._engine is not None:
            return self._engine
        try:
            from rapid_layout import RapidLayout

            self._engine = RapidLayout(model_type="pp_layout_cdla")
            return self._engine
        except Exception as exc:  # noqa: BLE001 - 模型未下载/依赖缺失时降级
            self._load_error = str(exc)
            logger.warning("RapidLayout 不可用（%s），扫描版将退化为整页 OCR。", exc)
            return None

    def detect(self, image: Any, page: int | None = None) -> list[LayoutRegion]:
        engine = self._ensure()
        if engine is None:
            return [LayoutRegion(label="text", box=[0, 0, 0, 0], score=1.0, page=page)]
        try:
            result = engine(image)
            regions = []
            for box, name, score in zip(result.boxes or [], result.class_names or [], result.scores or []):
                regions.append(
                    LayoutRegion(
                        label=str(name).lower(),
                        box=[float(v) for v in box],
                        score=float(score),
                        page=page,
                    )
                )
            return regions or [LayoutRegion(label="text", box=[0, 0, 0, 0], score=1.0, page=page)]
        except Exception as exc:  # noqa: BLE001
            logger.warning("版面检测失败（%s），退化为整页 OCR。", exc)
            return [LayoutRegion(label="text", box=[0, 0, 0, 0], score=1.0, page=page)]
