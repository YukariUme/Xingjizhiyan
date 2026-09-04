"""Agent 集成单元测试（使用种子数据）。"""

import json

from app.database import SessionLocal
from app.models import User
from app.repositories.user_repo import UserRepository
from app.services.agent.factory import get_agent_service
from app.services.agent.research import ResearchAgent
from app.services.llm.base import LLMService
from app.services.prompt import PromptService
from app.services.rag.factory import get_rag_service


class _ObjectFieldLLM(LLMService):
    """返回 experiments 为对象（表格）的 LLM，验证归一化。"""

    name = "object-field-mock"

    def generate(self, prompt, system=None, temperature=0.7, max_tokens=None) -> str:
        return json.dumps(
            {
                "summary": "摘要文本",
                "research_question": "研究问题",
                "method": "方法文本",
                "experiments": {
                    "组别": "实验组",
                    "人数": 30,
                    "干预方式": "AI 辅助教学",
                    "测量指标": "正确率",
                    "主要结果": "提升 12%",
                },
                "conclusion": "结论",
                "limitations": "局限",
                "future": "未来",
                "knowledge_points": ["动态规划", {"name": "对象知识点"}],
            },
            ensure_ascii=False,
        )

    def chat(self, messages, temperature=0.7, max_tokens=None) -> str:
        return self.generate("")

    async def stream(self, messages):
        yield self.generate("")


def _user(db, role: str) -> User:
    return db.query(User).filter(User.role == role).first()


def test_teaching_agent_lesson_plan():
    db = SessionLocal()
    try:
        teacher = _user(db, "teacher")
        agent = get_agent_service("teaching")
        result = agent.run(
            db,
            teacher,
            {
                "course": "数据结构",
                "chapter": "第 4 章 树",
                "topic": "二叉树遍历",
                "grade": "大二",
                "objective": "掌握三种遍历",
            },
        )
        assert result["objectives"]
        assert result["knowledge_points"]
        assert result["flow"]
        assert result["id"] > 0
    finally:
        db.close()


def test_learning_agent_tutor():
    db = SessionLocal()
    try:
        student = _user(db, "student")
        agent = get_agent_service("learning")
        result = agent.run(
            db,
            student,
            {"task": "tutor", "message": "什么是哈希表？", "mode": "hint", "history": []},
        )
        assert result["answer"]
        assert result["knowledge_points"]
        assert result["conversation_id"]
    finally:
        db.close()


def test_research_agent_explore():
    db = SessionLocal()
    try:
        researcher = _user(db, "researcher")
        agent = get_agent_service("research")
        result = agent.run(db, researcher, {"task": "explore", "topic": "RAG"})
        assert result["topic"] == "RAG"
        assert result["papers"]
        assert result["trend"]
    finally:
        db.close()


def test_research_agent_paper_analysis():
    db = SessionLocal()
    try:
        researcher = _user(db, "researcher")
        agent = get_agent_service("research")
        result = agent.run(db, researcher, {"task": "analyze", "paper_id": 1})
        assert result["paper_id"] == 1
        assert result["summary"]
        assert result["method"]
        assert result["references"]
    finally:
        db.close()


def test_research_agent_normalizes_object_fields():
    """LLM 把 experiments 返回成对象/表格时，前端不应收到对象（回归测试）。"""
    db = SessionLocal()
    try:
        researcher = _user(db, "researcher")
        agent = ResearchAgent(
            llm=_ObjectFieldLLM(),
            rag=get_rag_service(),
            prompts=PromptService(),
        )
        result = agent.run(db, researcher, {"task": "analyze", "paper_id": 1})
        assert isinstance(result["experiments"], str)
        assert "实验组" in result["experiments"]
        assert "主要结果" in result["experiments"]
        assert isinstance(result["summary"], str)
        assert all(isinstance(kp, str) for kp in result["knowledge_points"])
        assert "对象知识点" in result["knowledge_points"]
    finally:
        db.close()
