"""DeepSeekLLMService：真实 LLM 接入实现（OpenAI 兼容协议）。

通过配置 LLM_PROVIDER=deepseek 启用；未配置 API Key 时抛出清晰错误，
避免密钥硬编码。
"""

import json
from collections.abc import AsyncIterator

import httpx

from app.config import get_settings
from app.services.llm.base import LLMError, LLMService


class DeepSeekLLMService(LLMService):
    name = "deepseek"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.deepseek_api_key:
            raise LLMError(
                "未配置 DEEPSEEK_API_KEY。请在 backend/.env 中设置后重启，"
                "或将 LLM_PROVIDER 保持为 mock。"
            )
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url
        self.model = settings.deepseek_model

    def _complete(self, messages: list[dict[str, str]], temperature: float, max_tokens: int | None) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
            raise LLMError(f"DeepSeek API 调用失败：{exc}") from exc

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self._complete(messages, temperature, max_tokens)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        return self._complete(messages, temperature, max_tokens)

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        """SSE 流式输出：逐 token 解析 choices[].delta.content。"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "stream": True,
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                        if delta:
                            yield delta
        except httpx.HTTPError as exc:
            raise LLMError(f"DeepSeek 流式调用失败：{exc}") from exc
