"""AgentService 统一接口。"""

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.models import User
from app.services.llm.base import LLMService
from app.services.prompt import PromptService
from app.services.rag.base import RAGService


class AgentService(ABC):
    """业务 Agent 基类：每个 Agent 持有自己的 LLM / RAG / Prompt 组合。"""

    name: str = "base"

    def __init__(
        self,
        llm: LLMService,
        rag: RAGService,
        prompts: PromptService | None = None,
    ) -> None:
        self.llm = llm
        self.rag = rag
        self.prompts = prompts or PromptService()

    @abstractmethod
    def run(self, db: Session, user: User, payload: dict) -> dict:
        """执行 Agent 主任务，返回结构化结果。"""
        raise NotImplementedError

