"""Agent 工厂：按类型创建独立的业务 Agent。"""

from app.services.agent.base import AgentService
from app.services.agent.learning import LearningAgent
from app.services.agent.research import ResearchAgent
from app.services.agent.teaching import TeachingAgent
from app.services.agent.modes import (
    DiagnoseAgent,
    ExamAgent,
    LectureAgent,
    PreviewAgent,
    ReviewAgent,
)
from app.services.llm.factory import get_llm_service
from app.services.rag.factory import get_rag_service


def get_agent_service(agent_type: str) -> AgentService:
    llm = get_llm_service()
    rag = get_rag_service()
    if agent_type == "teaching":
        return TeachingAgent(llm=llm, rag=rag)
    if agent_type == "research":
        return ResearchAgent(llm=llm, rag=rag)
    if agent_type == "preview":
        return PreviewAgent(llm=llm, rag=rag)
    if agent_type == "lecture":
        return LectureAgent(llm=llm, rag=rag)
    if agent_type == "review":
        return ReviewAgent(llm=llm, rag=rag)
    if agent_type == "exam":
        return ExamAgent(llm=llm, rag=rag)
    if agent_type == "diagnose":
        return DiagnoseAgent(llm=llm, rag=rag)
    return LearningAgent(llm=llm, rag=rag)
