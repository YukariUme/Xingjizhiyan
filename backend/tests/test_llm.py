"""MockLLMService 单元测试。"""

import json

from app.services.llm.mock import MockLLMService


def _parse(raw: str) -> dict:
    return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])


def test_lesson_plan_generation():
    llm = MockLLMService(delay_ms=0)
    system, prompt = "你是智能备课助手", "[智能备课任务]\n课程：数据结构\n章节：第 4 章 树\n教学主题：二叉树遍历\n学生年级：大二\n教学目标：掌握三种遍历\n[知识库参考]\n- 讲义"
    raw = llm.generate(prompt, system=system)
    data = _parse(raw)
    assert "objectives" in data
    assert data["knowledge_points"]
    assert data["flow"]
    assert data["homework"]


def test_grading_json_structure():
    llm = MockLLMService(delay_ms=0)
    raw = llm.generate(
        "[主观题批改任务]\n题目：二叉树遍历\n满分：10\n评分要点：\n- 概念准确\n- 要点完整\n学生答案：前序遍历先访问根节点，再访问左子树和右子树，使用递归实现。",
        system="你是主观题批改助手",
    )
    data = _parse(raw)
    assert 0 <= data["suggestion_score"] <= 10
    assert data["reasoning"]
    assert "knowledge_points" in data
    assert "improvement" in data


def test_tutor_hint_mode_no_full_answer():
    llm = MockLLMService(delay_ms=0)
    raw = llm.generate(
        "[学科导师任务]\n模式：hint\n学生问题：如何反转单链表？\n知识库参考：\n- 线性表讲义",
        system="你是学科导师",
    )
    data = _parse(raw)
    assert "answer" in data
    assert "提示" in data["answer"] or "思考" in data["answer"]


def test_stream_yields_chunks():
    import asyncio

    llm = MockLLMService(delay_ms=0)

    async def collect():
        parts = []
        async for chunk in llm.stream(
            [{"role": "user", "content": "[学科导师任务]\n模式：detail\n学生问题：什么是进程？"}]
        ):
            parts.append(chunk)
        return "".join(parts)

    text = asyncio.run(collect())
    assert "进程" in text

