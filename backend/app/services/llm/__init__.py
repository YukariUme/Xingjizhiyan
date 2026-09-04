"""LLM 抽象层：LLMService 接口 + Mock/DeepSeek 实现 + 工厂。"""

from app.services.llm.base import LLMService, LLMError
from app.services.llm.factory import get_llm_service

__all__ = ["LLMService", "LLMError", "get_llm_service"]

