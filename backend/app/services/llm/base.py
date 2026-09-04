"""LLMService 统一接口。业务代码只依赖该接口，不直接写厂商 API。"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class LLMError(RuntimeError):
    """LLM 调用失败统一异常。"""


class LLMService(ABC):
    """大模型服务统一接口。

    实现类：MockLLMService（演示）、DeepSeekLLMService（真实接入）、
    未来可增加 SparkLLMService 等，通过配置 LLM_PROVIDER 切换。
    """

    name: str = "base"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """单次生成：给定提示词返回文本。"""
        raise NotImplementedError

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """多轮对话：messages = [{role: system|user|assistant, content: str}]。"""
        raise NotImplementedError

    @abstractmethod
    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        """流式输出（实现为异步生成器）。"""
        raise NotImplementedError
        yield  # pragma: no cover

