"""Agent 抽象层：不同业务 Agent 拥有独立 Prompt 与逻辑。"""

from app.services.agent.base import AgentService
from app.services.agent.factory import get_agent_service

__all__ = ["AgentService", "get_agent_service"]

