"""多智能体圆桌讨论（可加入）：预置第一轮 → 学生加入 → 他人友善回应 → 实时总结。

LLM 不可用或返回非法 JSON 时回退确定性模板，保证离线可演示。
"""

import json
import re

from sqlalchemy.orm import Session

from app.services.ai_meta import ai_meta, references_from_hits
from app.services.llm.factory import get_llm_service
from app.services.rag.factory import get_rag_service


PERSONAS = [
    {"id": "yu", "name": "小宇", "role": "课代表 · 推进讨论", "color": "#173f45"},
    {"id": "hang", "name": "小航", "role": "动手派 · 爱画图举例", "color": "#2a828e"},
    {"id": "nan", "name": "小楠", "role": "谨慎派 · 爱找边界", "color": "#47705e"},
    {"id": "fan", "name": "小凡", "role": "类比派 · 联系生活", "color": "#b26b16"},
    {"id": "senior", "name": "阿凯", "role": "资深程序员 · 工程视角", "color": "#8a6f3c"},
    {"id": "teacher", "name": "林老师", "role": "老师 · 适时点拨", "color": "#9d5d74"},
]


def _parse_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _first_round_fallback(topic: str) -> list[dict]:
    return [
        {
            "speaker": "小宇",
            "stance": "开场",
            "content": f"咱们一起聊「{topic}」。我先抛个问题：它最核心是解决什么？",
            "whiteboard": None,
        },
        {
            "speaker": "小航",
            "stance": "概念",
            "content": "我先说，我觉得得先抓住定义和适用场景——它到底解决什么问题、和相邻概念差在哪，这是理解它的地基。",
            "whiteboard": {"kind": "points", "title": "概念要点", "items": ["定义", "适用场景", "区别"]},
        },
        {
            "speaker": "小楠",
            "stance": "复杂度",
            "content": "我补充一个角度：时间与空间复杂度的权衡，不同数据规模下选型会完全不一样。",
            "whiteboard": {"kind": "compare", "title": "权衡", "left": "时间", "right": "空间"},
        },
        {
            "speaker": "小凡",
            "stance": "类比",
            "content": "我打个生活里的比方：就像排队取号，得想清楚什么时候该先进先出、什么时候后进先出。",
            "whiteboard": None,
        },
        {
            "speaker": "阿凯",
            "stance": "工程",
            "content": "我从工程角度补一句：真实系统里还要看缓存、并发和可维护性，不只看课本上的最优解。",
            "whiteboard": None,
        },
        {
            "speaker": "林老师",
            "stance": "点拨",
            "content": "大家聊得不错，先把共识记下来，再一起看一个具体例子巩固。",
            "whiteboard": None,
        },
    ]


def _reply_fallback(topic: str, student: str) -> list[dict]:
    return [
        {
            "speaker": "小航",
            "stance": "回应",
            "content": f"你这个想法很好！{student.strip() or '你的补充'}——我帮你补个例子就更完整了。",
            "whiteboard": None,
        },
        {
            "speaker": "小楠",
            "stance": "回应",
            "content": "顺着你的思路再想一层：如果数据规模变大，这个选择会不会有边界问题？",
            "whiteboard": None,
        },
        {
            "speaker": "小宇",
            "stance": "鼓励",
            "content": "说得不错，能主动参与讨论就是很好的学习方式。要不要再一起深入一步？",
            "whiteboard": None,
        },
        {
            "speaker": "阿凯",
            "stance": "补充",
            "content": "我再补个工程细节：这个思路在实际项目里落地时，要注意边界和性能取舍。",
            "whiteboard": None,
        },
        {
            "speaker": "林老师",
            "stance": "小结",
            "content": "大家把概念、复杂度、工程和例子都聊到了，继续保持这个节奏。",
            "whiteboard": None,
        },
    ]


def _summary_fallback(topic: str) -> str:
    return (
        f"咱们今天一起把「{topic}」聊得挺清楚：先理解概念与适用场景，再权衡时间/空间复杂度，"
        "还能联系工程实践与生活场景。你也积极参与了，很棒。下一步可以结合一道练习或动图再巩固一遍。"
    )


class RoundtableService:
    @staticmethod
    def _context(db: Session, topic: str, course_id: int | None) -> tuple[str, list]:
        hits: list = []
        try:
            rag = get_rag_service()
            hits = rag.search(db, topic, top_k=4, course_id=course_id) if course_id else rag.search(db, topic, top_k=4)
        except Exception:  # noqa: BLE001
            pass
        context = "\n".join(
            f"[{h.metadata.get('source_level', 'S')}] {h.document_title}：{h.text[:160]}"
            for h in hits
        )
        return context, hits

    @staticmethod
    def start(db: Session, topic: str, course_id: int | None = None) -> dict:
        topic = (topic or "递归与迭代").strip()
        context, hits = RoundtableService._context(db, topic, course_id)
        llm = get_llm_service()
        prompt = (
            f"请为「{topic}」组织一场圆桌讨论的**第一轮发言**（学生尚未加入）。\n"
            f"知识库参考：\n{context or '（无）'}\n\n"
            "请输出 JSON：turns（数组，每项含 speaker/stance/content/whiteboard）。\n"
            "要求：先课代表小宇友好开场，然后同学小航、小楠、小凡各发表第一轮观点；"
            "资深程序员阿凯可从工程角度补充，老师林老师只在必要时温和小结。"
            "以同学讨论为主，语气友善、鼓励，不要提前结束讨论。whiteboard 可为 null 或 points/compare。"
        )
        raw = llm.generate(prompt, system="你是友好、像同学一样一起学习的讨论伙伴。")
        parsed = _parse_json(raw)
        turns = parsed.get("turns") if isinstance(parsed.get("turns"), list) else []
        if not turns:
            turns = _first_round_fallback(topic)
        return {
            "topic": topic,
            "personas": PERSONAS,
            "turns": turns,
            **ai_meta(llm.name, references_from_hits(hits), source="roundtable"),
        }

    @staticmethod
    def reply(db: Session, topic: str, turns: list, student_message: str, course_id: int | None = None) -> dict:
        student_message = (student_message or "").strip()
        if not student_message:
            return {"turns": _reply_fallback(topic, "我还没想好，请先给我一点引导。")}
        context, hits = RoundtableService._context(db, topic, course_id)
        llm = get_llm_service()
        history = "\n".join(
            f"{t.get('speaker', '')}：{t.get('content', '')}" for t in (turns or [])[-12:]
        )
        prompt = (
            f"圆桌主题：「{topic}」。\n"
            f"已有讨论：\n{history}\n\n"
            f"学生刚刚加入并说：{student_message}\n\n"
            "请让 2~3 位同学友善回应学生：肯定其想法、补充一个角度、或温和地提出一个更深的问题；"
            "资深程序员阿凯可补充工程细节，老师林老师可温和小结。语气必须友善、鼓励，不要否定学生。\n"
            '输出 JSON：turns（数组，每项含 speaker/stance/content/whiteboard，whiteboard 可为 null）。'
        )
        raw = llm.generate(prompt, system="你是友善、善于鼓励同学的学习伙伴。")
        parsed = _parse_json(raw)
        turns_out = parsed.get("turns") if isinstance(parsed.get("turns"), list) else []
        if not turns_out:
            turns_out = _reply_fallback(topic, student_message)
        return {
            "turns": turns_out,
            **ai_meta(llm.name, references_from_hits(hits), source="roundtable"),
        }

    @staticmethod
    def summarize(db: Session, topic: str, turns: list, course_id: int | None = None) -> dict:
        context, hits = RoundtableService._context(db, topic, course_id)
        llm = get_llm_service()
        history = "\n".join(
            f"{t.get('speaker', '')}：{t.get('content', '')}" for t in (turns or [])[-20:]
        )
        prompt = (
            f"请对下面的圆桌讨论做一次**友好、鼓励性**的实时总结。\n"
            f"主题：{topic}\n讨论记录：\n{history}\n\n"
            "总结应包含：同学们的核心共识、不同角度的分歧、学生参与的亮点、以及一个下一步建议；"
            "最后老师给一句鼓励。"
            "输出 JSON：summary（字符串）。"
        )
        raw = llm.generate(prompt, system="你是善于鼓励同学的学习伙伴。")
        parsed = _parse_json(raw)
        summary = parsed.get("summary") or _summary_fallback(topic)
        return {
            "summary": summary,
            **ai_meta(llm.name, references_from_hits(hits), source="roundtable"),
        }
