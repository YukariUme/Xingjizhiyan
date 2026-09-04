"""LLM 工厂：按配置创建服务实例（真实实现带结果缓存）。"""

import hashlib
import json
import time
from collections.abc import AsyncIterator
from threading import Lock

from app.config import get_settings
from app.services.llm.base import LLMService
from app.services.llm.deepseek import DeepSeekLLMService
from app.services.llm.mock import MockLLMService


class CachedLLMService(LLMService):
    """给真实 LLM 加进程内 TTL 缓存：相同输入秒回，避免重复生成等待。"""

    name = "deepseek-cached"

    def __init__(self, inner: LLMService, ttl: int = 1800) -> None:
        self._inner = inner
        self._ttl = ttl
        self._cache: dict[str, tuple[float, str]] = {}
        self._lock = Lock()

    def _key(self, messages, temperature, max_tokens) -> str:
        raw = f"{self._inner.name}|{json.dumps(messages, ensure_ascii=False)}|{temperature}|{max_tokens}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _get_or_call(self, messages, temperature, max_tokens) -> str:
        key = self._key(messages, temperature, max_tokens)
        now = time.time()
        with self._lock:
            hit = self._cache.get(key)
            if hit and now - hit[0] < self._ttl:
                return hit[1]
        result = self._inner.chat(messages, temperature, max_tokens)
        with self._lock:
            self._cache[key] = (now, result)
        return result

    def generate(self, prompt, system=None, temperature=0.7, max_tokens=None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self._get_or_call(messages, temperature, max_tokens)

    def chat(self, messages, temperature=0.7, max_tokens=None) -> str:
        return self._get_or_call(messages, temperature, max_tokens)

    async def stream(self, messages) -> AsyncIterator[str]:
        async for chunk in self._inner.stream(messages):
            yield chunk


def get_llm_service() -> LLMService:
    provider = get_settings().llm_provider.lower()
    if provider == "deepseek":
        return CachedLLMService(DeepSeekLLMService())
    return MockLLMService()
