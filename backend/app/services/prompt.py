"""PromptService：集中管理各 Agent 的提示词模板。

业务代码不直接拼提示词，避免“巨大的 if/else Prompt”散落各处；
接入真实 LLM 时模板可复用。
"""

from app.services.judge.base import JudgeResult


class PromptService:
    @staticmethod
    def lesson_plan(data: dict, knowledge_context: str) -> tuple[str, str]:
        system = (
            "你是高校计算机学科的智能备课助手。请基于教师输入与知识库参考，"
            "输出结构化的教案 JSON。"
        )
        class_analytics = data.get("class_analytics") or ""
        prompt = f"""[智能备课任务]
课程：{data.get('course', '')}
章节：{data.get('chapter', '')}
教学主题：{data.get('topic', '')}
学生年级：{data.get('grade', '')}
教学目标：{data.get('objective', '')}
教学时长：{data.get('duration', '')}
学生水平：{data.get('level', '')}
班级学情参考：
{class_analytics or '（未提供）'}

[知识库参考]
{knowledge_context or '（无）'}

请输出 JSON，字段：objectives（教学目标）、knowledge_points（知识点列表）、
key_points（重点）、difficulties（难点）、flow（教学流程，每项含 step 与 content）、
cases（课堂案例）、exercises（随堂练习，每项含 title 与 desc）、homework（课后作业建议）。
"""
        return system, prompt

    @staticmethod
    def grade_subjective(
        question: dict, answer: str, rubric: list[str], knowledge_context: str
    ) -> tuple[str, str]:
        system = (
            "你是高校计算机学科的主观题批改助手。AI 只提供建议分数与理由，"
            "最终分数由教师确认。请输出结构化 JSON。"
        )
        prompt = f"""[主观题批改任务]
题目：{question.get('title', '')}
题目描述：{question.get('description', '')}
满分：{question.get('max_score', 10)}
评分要点：
{chr(10).join(f'- {p}' for p in rubric) or '- 概念准确、要点完整、论述清晰'}
学生答案：
{answer or '（空）'}

[知识库参考]
{knowledge_context or '（无）'}

请输出 JSON，字段：suggestion_score（建议分，数字）、reasoning（评分理由）、
knowledge_points（涉及知识点列表）、errors（错误与不足列表）、improvement（改进建议）。
"""
        return system, prompt

    @staticmethod
    def tutor(
        message: str,
        history: list[dict],
        knowledge_context: str,
        mode: str,
        grounded: bool = True,
        context_scope: str = "",
        teaching: bool = False,
        primary_title: str = "",
        answer_style: str = "detail",
    ) -> tuple[str, str]:
        if teaching:
            if answer_style == "quick":
                style_note = "快速回答：简明扼要，直接讲清核心结论与要点（3~5 个要点，总长 200~400 字）。"
            else:
                style_note = "深度回答：像老师讲课一样从零开始逐层展开——先讲背景与为什么，再讲概念与原理，最后给典型例子、易错点与练习（600~1200 字）。"
            system = (
                "你是高校计算机学科的 AI 助教，目标是替代教师授课。默认学生没学过该知识点。"
                "必须严格围绕给定的主资料讲解，不能跑题到主资料之外的知识点；背景资料仅作补充。"
                "回答必须可追溯，引用来源。"
            )
        else:
            style_note = ""
            system = (
                "你是高校计算机学科的 AI 学科导师。提示模式只给思路不给完整答案；"
                "详细模式给出逐步解析。回答必须可追溯，引用知识库来源。"
            )
        history_text = "\n".join(
            f"{'学生' if m.get('role') == 'user' else 'AI'}：{m.get('content', '')}"
            for m in history[-6:]
        )
        grounding_note = (
            "（知识库未检索到相关依据，请基于模型自身知识回答，并在回答开头注明这一点。）"
            if not grounded
            else "（知识库已提供参考内容：请优先基于参考内容回答；若参考内容不足以回答，请明确说明该部分属于模型自身知识，不要编造知识库来源。）"
        )
        prompt = f"""[学科导师任务]
模式：{mode}
{style_note}
主资料：{primary_title or "（未指定，按通用知识回答）"}
{context_scope}
对话历史：
{history_text or '（无）'}
学生问题：{message}
{grounding_note}

[知识库参考]
{knowledge_context or '（无）'}

请输出 JSON，字段：answer（回答）、knowledge_points（知识点列表）、references（引用来源列表）。
"""
        return system, prompt

    @staticmethod
    def code_diagnosis(
        question_title: str,
        question_desc: str,
        source_code: str,
        judge: JudgeResult,
        mode: str,
    ) -> tuple[str, str]:
        system = (
            "你是高校编程教学中的代码错误诊断助手。根据评测结果分析错误原因、"
            "涉及知识点、分析思路与学习建议；提示模式不给出完整答案。"
        )
        report_text = "\n".join(
            f"- {r.name}: {'通过' if r.passed else '未通过'} - {r.message}"
            for r in judge.report
        )
        prompt = f"""[代码错误诊断任务]
题目：{question_title}
题目描述：{question_desc}
模式：{mode}
评测错误：{judge.error_message or '（无）'}
评测报告：
{report_text or '（无）'}
学生代码：
{source_code}

请输出 JSON，字段：error_reason（错误原因）、knowledge_points（知识点列表）、
thinking（分析思路列表）、advice（学习建议列表）、suggestion（提示模式的引导语）。
"""
        return system, prompt

    @staticmethod
    def paper_analysis(paper: dict) -> tuple[str, str]:
        system = "你是科研论文阅读助手，负责把论文拆解为可追溯的结构化笔记。"
        prompt = f"""[论文阅读助手任务]
论文标题：{paper.get('title', '')}
作者：{'、'.join(paper.get('authors', []) or [])}
发表：{paper.get('venue', '')} {paper.get('year', '')}

[论文内容]
{paper.get('content', '')}

请输出 JSON，字段：summary（摘要）、research_question（研究问题）、method（方法）、
experiments（实验）、conclusion（结论）、limitations（局限性）、future（可进一步研究的问题）、
knowledge_points（涉及知识点列表）。
"""
        return system, prompt

    @staticmethod
    def frontier(topic: str, papers: list[dict], knowledge_context: str) -> tuple[str, str]:
        system = "你是科研前沿探索助手，基于论文库与知识库分析研究主题的趋势与方向。"
        paper_lines = "\n".join(
            f"- {p.get('title', '')}（{p.get('year', '')}）" for p in papers[:15]
        )
        prompt = f"""[科研前沿探索任务]
主题：{topic}

[相关论文]
{paper_lines or '（暂无可参考论文）'}

[知识库参考]
{knowledge_context or '（无）'}

请输出 JSON，字段：directions（相关研究方向）、papers（论文列表，每项含 title 与 year）、
hot_topics（热点主题）、methods（方法分类，每项含 name 与 count）、
trend（时间趋势，每项含 year 与 count）。
"""
        return system, prompt
