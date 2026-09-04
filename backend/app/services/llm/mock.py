"""MockLLMService：无需真实 API 的演示实现。

通过识别提示词中的任务标记与结构化字段，结合知识库参考内容，
生成确定性的、可演示的“AI 输出”。接入真实 LLM 后替换该实现即可。
"""

import json
import re
import time
from collections.abc import AsyncIterator

from app.services.llm.base import LLMService


def _field(prompt: str, key: str) -> str:
    """从提示词中提取「key：value」字段。"""
    m = re.search(rf"{re.escape(key)}[：:]\s*([^\n]+)", prompt)
    return m.group(1).strip() if m else ""


def _field_lines(prompt: str, key: str) -> list[str]:
    """从提示词中提取多行字段内容。"""
    m = re.search(rf"{re.escape(key)}[：:]\s*\n(.*?)(?=\n\S|$)", prompt, re.S)
    if not m:
        return []
    return [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]


def _wrap_json(obj: dict) -> str:
    """把结构化结果包装为可解析的 JSON 文本。"""
    return json.dumps(obj, ensure_ascii=False, indent=2)


class MockLLMService(LLMService):
    name = "mock"

    def __init__(self, delay_ms: int = 80) -> None:
        self.delay_ms = delay_ms

    def _simulate_delay(self) -> None:
        if self.delay_ms > 0:
            time.sleep(self.delay_ms / 1000)

    # ---------- 任务分发 ----------
    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        self._simulate_delay()
        marker = system or prompt
        if "备课" in marker:
            return self._lesson_plan(prompt)
        if "主观题批改" in marker or "批改" in marker:
            return self._grade_subjective(prompt)
        if "代码错误诊断" in marker:
            return self._code_diagnosis(prompt)
        if "论文阅读助手" in marker:
            return self._paper_analysis(prompt)
        if "科研前沿探索" in marker:
            return self._frontier(prompt)
        if "教学诊断" in marker:
            return self._diagnose(prompt)
        if "论文对比" in marker:
            return self._compare_papers(prompt)
        if "学科导师" in marker:
            return self._tutor(prompt)
        # 兜底：通用回答
        return self._generic(prompt)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = "\n".join(m["content"] for m in messages if m["role"] == "user")
        prompt = f"{system}\n\n{user}"
        return self.generate(prompt, system=system)

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        text = self.chat(messages)
        step = 8
        for i in range(0, len(text), step):
            await _async_sleep(0.005)
            yield text[i : i + step]

    # ---------- 各任务生成器 ----------
    def _lesson_plan(self, prompt: str) -> str:
        course = _field(prompt, "课程")
        chapter = _field(prompt, "章节")
        topic = _field(prompt, "教学主题") or _field(prompt, "主题")
        grade = _field(prompt, "学生年级")
        objective = _field(prompt, "教学目标")
        kp_refs = _field_lines(prompt, "知识库参考")
        knowledge_points = []
        for ref in kp_refs[:6]:
            name = ref.split("。")[0].replace("1.", "").strip()
            if name:
                knowledge_points.append(name)
        if not knowledge_points:
            knowledge_points = [f"{topic}核心概念", f"{topic}算法实现", f"{topic}应用与练习"]
        return _wrap_json(
            {
                "objectives": f"1. 理解{chapter}中「{topic}」的基本概念与原理；\n"
                f"2. 掌握{topic}的典型方法与实现步骤；\n"
                f"3. 能在实际案例中运用{topic}解决问题，并完成随堂练习与作业。"
                + (f"\n4. {objective}" if objective else ""),
                "knowledge_points": knowledge_points,
                "key_points": [
                    f"{topic}的定义与性质",
                    f"{topic}的实现方法",
                    f"{topic}的典型应用场景",
                ],
                "difficulties": [
                    f"{topic}的边界条件与复杂度分析",
                    f"{topic}在综合问题中的迁移运用",
                ],
                "flow": [
                    {"step": "导入", "content": f"通过生活/工程案例引入{chapter}与{topic}，激发学习动机"},
                    {"step": "讲授", "content": f"讲解{topic}核心概念、性质与实现细节，结合板书/演示"},
                    {"step": "演示", "content": f"现场编码演示{topic}的典型实现并分析复杂度"},
                    {"step": "练习", "content": f"学生完成随堂练习，教师巡视并即时反馈"},
                    {"step": "总结", "content": f"梳理{topic}知识结构，布置课后作业与预习任务"},
                ],
                "cases": [
                    f"案例 1：用{chapter}知识点解决经典问题（含逐步讲解）",
                    f"案例 2：{course}课程中的{topic}应用实例（贴近真实工程）",
                    f"案例 3：易错辨析：{topic}常见误区与陷阱",
                ],
                "exercises": [
                    {"title": "基础题", "desc": f"复述{topic}的核心概念与步骤，完成概念判断题"},
                    {"title": "进阶题", "desc": f"独立实现{topic}的典型算法并通过自测用例"},
                    {"title": "拓展题", "desc": f"将{topic}应用于一个综合场景并说明设计思路"},
                ],
                "homework": [
                    f"作业 1：{topic}概念梳理思维导图",
                    f"作业 2：编程实现{topic}并提交 OJ 评测",
                    f"作业 3：阅读推荐资料，预习下一节内容",
                ],
            }
        )

    def _grade_subjective(self, prompt: str) -> str:
        title = _field(prompt, "题目")
        max_score = float(_field(prompt, "满分") or 10)
        answer = _field_lines(prompt, "学生答案") or []
        points = _field_lines(prompt, "评分要点")
        answer_text = " ".join(answer)
        base = 4.0
        if answer_text:
            base += min(3.0, len(answer_text) / 120)
        hit = 0
        for p in points:
            if p and (p[:8] in answer_text or any(k in answer_text for k in p.split("、"))):
                hit += 1
        base += min(3.0, hit * 1.2)
        score = round(min(max_score, base), 1)
        errors = []
        if not answer_text:
            errors.append("答案为空，未回答题目核心问题")
        elif hit < max(1, len(points) // 2):
            errors.append("回答未覆盖全部评分要点，关键概念表述不完整")
        if len(answer_text) > 0 and len(answer_text) < 30:
            errors.append("论述过短，缺少必要的展开与例证")
        knowledge = [p for p in points[:4] if p]
        improvement = (
            "建议按“概念定义 → 原理/步骤 → 例子 → 总结”的结构组织答案，"
            "补充关键术语与典型例子，确保覆盖所有评分要点。"
            if errors
            else "回答结构完整、要点覆盖良好，可进一步补充边界条件与扩展思考。"
        )
        return _wrap_json(
            {
                "suggestion_score": score,
                "reasoning": f"覆盖 {hit} 个评分要点，论述长度 {len(answer_text)} 字；"
                f"概念准确性与完整性为{'较好' if hit else '不足'}，综合建议 {score} 分（满分 {max_score}）。",
                "knowledge_points": knowledge,
                "errors": errors,
                "improvement": improvement,
            }
        )

    def _code_diagnosis(self, prompt: str) -> str:
        mode = _field(prompt, "模式") or "hint"
        error = _field(prompt, "评测错误") or "未提供错误信息"
        code = _field_lines(prompt, "学生代码") or []
        code_text = "\n".join(code)
        reason = error
        knowledge = []
        if "NameError" in error or "未定义" in error:
            reason = "代码引用了未定义的变量或函数，常见于函数名拼写不一致或忘记定义辅助函数。"
            knowledge = ["函数定义与调用", "变量作用域"]
        elif "IndexError" in error or "越界" in error:
            reason = "列表/字符串下标越界，通常由循环边界或空容器访问引起。"
            knowledge = ["循环边界", "序列索引"]
        elif "Time" in error or "超时" in error:
            reason = "算法复杂度过高，在较大输入下超时，需要优化到更低的复杂度。"
            knowledge = ["算法复杂度分析", "时间复杂度优化"]
        elif not code_text:
            reason = "提交代码为空，无法通过任何测试点。"
            knowledge = ["代码提交规范"]
        elif "pass" in code_text:
            reason = "函数体仅包含占位符 pass，尚未实现核心逻辑。"
            knowledge = ["函数实现"]
        else:
            reason = "代码逻辑与题目要求不符：可能遗漏了关键分支或返回了错误结果。"
            knowledge = ["题目理解", "逻辑分支"]
        thinking = [
            "先复现错误，确认是编译期、运行期还是逻辑错误",
            "定位出错位置：检查变量名、循环边界与空容器访问",
            "对照题目示例验证输入输出是否一致",
            f"根据错误特征判断涉及的知识点：{'、'.join(knowledge)}",
        ]
        advice = [
            "先在本地用题目示例用例复现并打印中间变量",
            "检查函数签名与调用处的命名是否一致",
            "为边界输入（空输入、单元素、最大规模）补充测试",
        ]
        if mode == "detail":
            advice.append("参考知识库中的标准实现思路，逐步重写核心逻辑并再次评测")
            suggestion = "提示：从最简单输入开始手动推演一遍算法流程，通常能直接发现逻辑断点。"
        else:
            suggestion = "先不要看完整答案：请告诉我你定位到的出错行与你的推理，我帮你逐步排查。"
        return _wrap_json(
            {
                "error_reason": reason,
                "knowledge_points": knowledge,
                "thinking": thinking,
                "advice": advice,
                "suggestion": suggestion,
            }
        )

    def _paper_analysis(self, prompt: str) -> str:
        title = _field(prompt, "论文标题")
        content = _field_lines(prompt, "论文内容") or []
        abstract = " ".join(
            ln for ln in content if any(k in ln for k in ["摘要", "abstract", "引言", "1 "])
        )
        sections = {"方法": [], "实验": [], "结论": [], "局限": [], "未来": []}
        for ln in content:
            for key in sections:
                if any(k in ln for k in [f"{i} " + key for i in range(1, 6)]) or key in ln[:6]:
                    sections[key].append(ln)
        summary = abstract or (
            f"本论文围绕「{title}」展开，提出了面向实际场景的方法，并通过实验验证了其有效性。"
        )
        return _wrap_json(
            {
                "summary": summary[:300],
                "research_question": f"论文研究的问题是：如何更有效地解决「{title}」所对应的场景痛点，并验证其实际价值。",
                "method": "、".join(sections["方法"][:2]) or "提出针对场景问题的方法设计与实现流程，包括数据、模型与系统架构。",
                "experiments": "、".join(sections["实验"][:2]) or "在公开数据集与真实场景中进行对比实验，报告准确率/效率等关键指标。",
                "conclusion": "、".join(sections["结论"][:2]) or "实验结果表明所提方法在关键指标上优于基线，具备场景落地价值。",
                "limitations": "、".join(sections["局限"][:2]) or "数据规模有限，跨场景泛化能力仍有待进一步验证。",
                "future": "、".join(sections["未来"][:2]) or "可进一步结合更大规模数据与多模态信息，探索与教学/科研场景的深度融合。",
                "knowledge_points": ["检索增强生成 RAG", "大语言模型"],
            }
        )

    def _frontier(self, prompt: str) -> str:
        topic = _field(prompt, "主题")
        paper_lines = _field_lines(prompt, "相关论文")
        papers = []
        year_counts: dict[str, int] = {}
        for ln in paper_lines[:15]:
            ym = re.search(r"(20\d\d)", ln)
            year = ym.group(1) if ym else "2025"
            year_counts[year] = year_counts.get(year, 0) + 1
            papers.append({"title": ln, "year": int(year)})
        directions = [
            f"{topic}核心方法研究",
            f"{topic}与知识工程结合",
            f"{topic}在教育/科研场景的落地应用",
            f"{topic}的安全、可信与可解释性",
        ]
        methods = [
            {"name": "检索增强生成（RAG）", "count": 4},
            {"name": "提示工程与思维链", "count": 3},
            {"name": "参数高效微调（LoRA）", "count": 3},
            {"name": "多智能体协作", "count": 2},
        ]
        trend = [
            {"year": int(y), "count": c}
            for y, c in sorted(year_counts.items())
        ]
        return _wrap_json(
            {
                "directions": directions,
                "papers": papers,
                "hot_topics": [f"{topic}高质量知识库", f"{topic}评测基准", f"{topic}教学应用"],
                "methods": methods,
                "trend": trend,
            }
        )

    def _diagnose(self, prompt: str) -> str:
        course = _field(prompt, "课程")
        avg = _field(prompt, "平均正确率")
        errors = _field_lines(prompt, "高频错误")
        weak = _field_lines(prompt, "薄弱知识点")
        findings = []
        if errors:
            findings.append(
                {
                    "issue": f"{errors[0]} 是班级表现较差的环节",
                    "evidence": f"该知识点作答正确率较低，且出现在高频错误列表中",
                    "reason": "学生可能记住了概念定义，但无法区分易混概念或在综合问题中迁移应用。",
                }
            )
        if weak:
            findings.append(
                {
                    "issue": f"班级薄弱知识点：{weak[0]}",
                    "evidence": f"相关任务中较多学生未通过（平均正确率 {avg}）",
                    "reason": "建议检查前置知识是否牢固，以及课堂练习是否覆盖该知识点的边界情况。",
                }
            )
        if not findings:
            findings.append(
                {
                    "issue": "班级整体表现较好",
                    "evidence": f"平均正确率 {avg}",
                    "reason": "可以进入下一章节，并在课堂中穿插综合应用。",
                }
            )
        return _wrap_json(
            {
                "findings": findings,
                "suggestions": [
                    {"title": "下一节课增加概念对比环节", "detail": f"针对「{course}」的易混概念安排 10 分钟对比讲解与辨析练习。"},
                    {"title": "补充典型案例与代码实验", "detail": f"围绕薄弱知识点增加 1 个生产者-消费者式案例和 1 道代码实验。"},
                    {"title": "对重点学生推送补充学习内容", "detail": "基于学情画像，向薄弱学生推荐对应章节复习与强化练习。"},
                ],
                "next_lesson": [f"重点讲解：{w}" for w in weak[:3]] or [f"按计划进入下一章节"],
                "materials": ["章节讲义", "典型例题", "代码实验指导"],
            }
        )

    def _compare_papers(self, prompt: str) -> str:
        papers = _field_lines(prompt, "论文列表")
        dimensions = ["研究问题", "方法", "数据集", "指标", "实验结果", "局限性"]
        rows = []
        for dimension in dimensions:
            cells = []
            for paper in papers[:4]:
                short = paper.split("（")[0].strip()[:40] if paper else ""
                cells.append(f"{short}：该维度详见论文原文")
            rows.append({"dimension": dimension, "cells": cells})
        return _wrap_json(
            {
                "rows": rows,
                "summary": (
                    f"共对比 {len(papers)} 篇论文：围绕研究问题、方法、数据集与指标进行结构化对比，"
                    "结论与局限性差异已在表格中标注，建议结合原文进一步核对。"
                ),
            }
        )

    def _tutor(self, prompt: str) -> str:
        mode = _field(prompt, "模式") or "hint"
        question = _field(prompt, "学生问题") or "请介绍一下相关知识"
        refs = _field_lines(prompt, "知识库参考")
        main_ref = refs[0] if refs else ""
        if mode == "hint":
            answer = (
                f"关于「{question}」，你可以从三个层次思考：\n"
                "① 先明确核心概念的定义与适用条件；\n"
                "② 再分析典型步骤或性质，注意边界情况；\n"
                "③ 最后用一个具体例子自测理解是否正确。\n"
                f"提示：{main_ref[:120] if main_ref else '结合教材章节与课堂讲义复习基础概念'}。"
                " 先尝试独立推导，如果卡住，告诉我你卡在哪一步，我再给更具体的引导。"
            )
        else:
            answer = (
                f"针对「{question}」的详细解析：\n"
                f"概念：{main_ref if main_ref else '这是计算机学科中的基础知识点，先掌握定义与核心性质。'}\n"
                "步骤：1) 梳理已知条件与目标；2) 选择对应的方法/数据结构；3) 实现并验证边界；4) 总结复杂度与适用场景。\n"
                "例证：以一个最小规模的实例走一遍完整流程，观察每一步的输出变化。\n"
                "易错点：注意空输入、单元素输入与最大规模输入；检查循环边界与递归出口。"
            )
        return _wrap_json(
            {
                "answer": answer,
                "knowledge_points": [f"{question}"],
                "references": [main_ref] if main_ref else [],
            }
        )

    def _generic(self, prompt: str) -> str:
        return (
            "（Mock AI 回答）我已收到你的问题。当前为演示模式，建议访问「AI 学科导师」或"
            "「科研前沿探索」体验结构化回答；接入真实大模型后，此入口将返回完整的多轮对话。"
        )


async def _async_sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)
