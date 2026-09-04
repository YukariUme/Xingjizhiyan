"""VisionService 统一接口：图片理解（教材页/PPT 截图/手写题/代码截图）。

第一版提供 MockVisionService（离线演示），并为 GLM-4V / Qwen-VL 预留实现骨架，
通过 VISION_PROVIDER 配置切换；未来可继续增加其他多模态模型。
"""

import base64
import logging
from abc import ABC, abstractmethod

from app.config import get_settings

logger = logging.getLogger(__name__)


class VisionError(RuntimeError):
    """图片理解调用失败统一异常。"""


class VisionService(ABC):
    """多模态图片理解服务统一接口。"""

    name: str = "base"

    @abstractmethod
    def analyze_image(self, image_bytes: bytes, prompt: str = "") -> str:
        """输入图片字节与提示词，返回图片内容的结构化文本描述。"""
        raise NotImplementedError


class MockVisionService(VisionService):
    """离线 Mock：根据提示词返回稳定的预置描述，供演示与测试。"""

    name = "mock"

    def analyze_image(self, image_bytes: bytes, prompt: str = "") -> str:
        size_kb = len(image_bytes) // 1024
        hint = (prompt or "").strip()
        if "代码" in hint or "code" in hint.lower() or "程序" in hint:
            description = (
                "图片内容：学生上传的代码/程序截图。画面包含一段源代码与可能的运行结果，"
                "疑似存在并发/同步相关代码（线程、锁或信号量调用）。"
            )
        elif "手写" in hint or "作业" in hint:
            description = (
                "图片内容：学生手写作业/笔记照片，涉及进程同步相关概念（互斥、同步、信号量），"
                "字迹中可辨认出 P/V 操作与生产者-消费者关键词。"
            )
        elif "教材" in hint or "PPT" in hint or "讲义" in hint:
            description = (
                "图片内容：教材/课件页面截图，标题为“进程同步”，"
                "正文包含临界区、信号量 P/V 操作与生产者-消费者问题的定义和图示。"
            )
        else:
            description = (
                "图片内容：学生上传的课程相关图片（教材页/课件/笔记/代码截图），"
                "与进程同步、信号量等操作系统知识点相关。"
            )
        return f"{description}（图片大小约 {size_kb}KB，当前为 Mock 视觉识别）"


class _OpenAIChatVisionMixin:
    """基于 OpenAI 兼容 /chat/completions 的视觉模型公共实现（GLM-4V / Qwen-VL）。"""

    api_key: str = ""
    base_url: str = ""
    model: str = ""

    def analyze_image(self, image_bytes: bytes, prompt: str = "") -> str:
        if not self.api_key:
            raise VisionError(
                f"{self.name} 未配置 API Key：请在 .env 设置 "
                f"{self.name.upper()}_API_KEY 后切换 VISION_PROVIDER={self.name}"
            )
        import httpx

        data_url = (
            "data:image/png;base64,"
            + base64.b64encode(image_bytes).decode("ascii")
        )
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or "请描述这张图片的内容"},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ]
        resp = httpx.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "messages": messages, "max_tokens": 800},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")


class GLM4VVisionService(_OpenAIChatVisionMixin, VisionService):
    """智谱 GLM-4V（预留）：OpenAI 兼容接口。"""

    name = "glm4v"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.glm4v_api_key
        self.base_url = settings.glm4v_base_url
        self.model = settings.glm4v_model


class QwenVLVisionService(_OpenAIChatVisionMixin, VisionService):
    """通义千问 Qwen-VL（预留）：DashScope OpenAI 兼容接口。"""

    name = "qwen_vl"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.qwen_vl_api_key
        self.base_url = settings.qwen_vl_base_url
        self.model = settings.qwen_vl_model


def get_vision_service() -> VisionService:
    """按 VISION_PROVIDER 创建视觉服务：mock | glm4v | qwen_vl。"""
    provider = get_settings().vision_provider.lower()
    if provider == "glm4v":
        return GLM4VVisionService()
    if provider == "qwen_vl":
        return QwenVLVisionService()
    return MockVisionService()
