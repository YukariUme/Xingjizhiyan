"""工作流工具注册表：把既有业务服务注册为可编排的工具。

每个工具签名为 tool(db, context, params) -> dict，返回结构化结果写入上下文。
"""

from sqlalchemy.orm import Session

from app.models import Activity, LessonPlan, Question, Submission
from app.repositories.activity_repo import ActivityRepository
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.course_repo import CourseRepository
from app.repositories.learning_repo import LearningRepository
from app.repositories.research_repo import ResearchRepository
from app.services.agent.research import ResearchAgent
from app.services.agent.teaching import _parse_json
from app.services.analytics_service import AnalyticsService
from app.services.grading_service import GradingService
from app.services.judge.factory import get_judge_service
from app.services.learning_path_service import LearningPathService
from app.services.llm.factory import get_llm_service
from app.services.prompt import PromptService
from app.services.rag.factory import get_rag_service
from app.services.rag.base import RetrievedChunk


def _render_params(params: dict, context: dict) -> dict:
    """把 {key} 占位符替换为上下文值。"""

    def resolve(value):
        if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
            key = value[1:-1]
            return context.get(key, "")
        return value

    return {key: resolve(value) for key, value in params.items()}


def _chunks_to_dicts(chunks: list[RetrievedChunk]) -> list[dict]:
    return [
        {
            "chunk_id": c.chunk_id,
            "text": c.text[:300],
            "title": c.document_title,
            "source": c.document_source,
            "course": c.course,
            "chapter": c.chapter,
            "score": c.score,
        }
        for c in chunks
    ]


def _as_text(value) -> str:
    """LLM 输出归一化：列表/数字统一转文本（兼容不同模型的返回格式）。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value)


def _normalize_text_list(items) -> list[str]:
    """把 LLM 返回的列表规范成字符串列表（兼容对象 {title, description}）。"""
    out: list[str] = []
    for item in items or []:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            title = str(item.get("title") or item.get("name") or "").strip()
            desc = str(
                item.get("description") or item.get("desc") or item.get("content") or ""
            ).strip()
            out.append(f"{title}：{desc}" if title and desc else (title or desc))
        else:
            out.append(str(item))
    return [x for x in out if x]


def _normalize_exercises(items) -> list[dict]:
    """随堂练习统一为 {title, desc}（兼容 description 键名）。"""
    out: list[dict] = []
    for item in items or []:
        if isinstance(item, str):
            out.append({"title": item, "desc": ""})
        elif isinstance(item, dict):
            out.append(
                {
                    "title": str(item.get("title") or item.get("name") or ""),
                    "desc": str(
                        item.get("desc") or item.get("description") or item.get("content") or ""
                    ),
                }
            )
        else:
            out.append({"title": str(item), "desc": ""})
    return out


def _normalize_flow(items) -> list[dict]:
    """教学流程统一为 {step, content}。"""
    out: list[dict] = []
    for item in items or []:
        if isinstance(item, dict):
            out.append(
                {
                    "step": str(item.get("step") or item.get("name") or item.get("title") or ""),
                    "content": str(item.get("content") or item.get("desc") or item.get("description") or ""),
                }
            )
        elif isinstance(item, str):
            out.append({"step": "", "content": item})
    return out


def tool_rag_search(db: Session, context: dict, params: dict) -> dict:
    rag = get_rag_service()
    query = str(params.get("query", ""))
    course = params.get("course") or None
    hits = rag.search(
        db,
        query,
        top_k=int(params.get("top_k", 4)),
        course=course,
        course_id=params.get("course_id"),
        source_levels=params.get("source_levels"),
        visibilities=params.get("visibilities"),
        owner_id=params.get("owner_id"),
    )
    text = "\n".join(
        f"- {h.document_title}（{h.document_source}）：{h.text[:180]}"
        for h in hits
    )
    return {"hits": _chunks_to_dicts(hits), "count": len(hits), "text": text}


def tool_llm_generate(db: Session, context: dict, params: dict) -> dict:
    llm = get_llm_service()
    system = str(params.get("system", "你是高校计算机学科智能助手"))
    prompt = str(params.get("prompt", ""))
    raw = llm.generate(prompt, system=system, temperature=0.7)
    parsed = _parse_json(raw)
    return {"raw": raw, "parsed": parsed, "provider": llm.name}


def tool_judge_run(db: Session, context: dict, params: dict) -> dict:
    judge = get_judge_service()
    result = judge.judge(
        str(params.get("source_code", "")),
        str(params.get("language", "python")),
        params.get("test_cases", []),
    )
    return {
        "verdict": result.verdict,
        "passed_tests": result.passed_tests,
        "total_tests": result.total_tests,
        "runtime_ms": result.runtime_ms,
        "error_message": result.error_message,
        "judge_report": [
            {
                "test_id": r.test_id,
                "name": r.name,
                "passed": r.passed,
                "message": r.message,
                "expected": r.expected,
                "actual": r.actual,
                "time_ms": r.time_ms,
            }
            for r in result.report
        ],
    }


def tool_save_judge(db: Session, context: dict, params: dict) -> dict:
    """把评测结果持久化到提交记录。"""
    submission = db.get(Submission, int(params.get("submission_id", 0)))
    judge = context.get("judge", {}) or {}
    if not submission or not submission.code:
        return {"ok": False}
    code = submission.code
    code.source_code = params.get("source_code") or code.source_code
    code.language = params.get("language") or code.language
    code.verdict = judge.get("verdict", "internal_error")
    code.passed_tests = int(judge.get("passed_tests", 0))
    code.total_tests = int(judge.get("total_tests", 0))
    code.runtime_ms = int(judge.get("runtime_ms", 0))
    code.error_message = judge.get("error_message", "")
    code.judge_report = judge.get("judge_report", [])
    submission.status = "graded" if judge.get("verdict") == "accepted" else "submitted"
    db.add(code)
    db.add(submission)
    db.commit()
    return {"ok": True, "status": submission.status}


def tool_diagnose_code(db: Session, context: dict, params: dict) -> dict:
    from app.services.agent.learning import LearningAgent

    agent = LearningAgent(llm=get_llm_service(), rag=get_rag_service())
    result = agent.diagnose_code(
        db,
        context.get("__user__"),
        {
            "question_title": params.get("question_title", ""),
            "question_description": params.get("question_description", ""),
            "source_code": params.get("source_code", ""),
            "language": params.get("language", "python"),
            "judge_report": params.get("judge_report", []),
            "error_message": params.get("error_message", ""),
            "mode": params.get("mode", "hint"),
        },
    )
    return result


def tool_ai_review(db: Session, context: dict, params: dict) -> dict:
    grading = GradingService(llm=get_llm_service(), rag=get_rag_service(), prompts=PromptService())
    submission = db.get(Submission, int(params.get("submission_id", 0)))
    if not submission:
        return {"ok": False, "reason": "提交不存在"}
    subj = grading.ai_review(db, submission)
    return {
        "ok": True,
        "suggestion_score": subj.ai_suggestion_score if subj else None,
        "reasoning": subj.ai_reasoning if subj else "",
        "knowledge_points": subj.ai_knowledge_points if subj else [],
        "status": submission.status,
    }


def tool_update_profile(db: Session, context: dict, params: dict) -> dict:
    submission = db.get(Submission, int(params.get("submission_id", 0)))
    if not submission:
        return {"ok": False}
    question = db.get(Question, submission.question_id)
    judge = context.get("judge", {}) or {}
    verdict = judge.get("verdict", "")
    correct = verdict == "accepted"
    score = float(question.max_score if correct else 0)
    AnalyticsService.update_profile_from_result(
        db, submission.student_id, question, correct=correct, score=score
    )
    return {"ok": True, "student_id": submission.student_id, "correct": correct, "score": score}


def tool_log_activity(db: Session, context: dict, params: dict) -> dict:
    user = context.get("__user__")
    if user is None:
        return {"ok": False}
    activity = ActivityRepository.add(
        db,
        Activity(
            user_id=user.id,
            role=user.role,
            kind=str(params.get("kind", "workflow")),
            title=str(params.get("title", "工作流执行")),
            detail=params.get("detail", {}) or {},
        ),
    )
    return {"ok": True, "activity_id": activity.id}


def tool_save_lesson_plan(db: Session, context: dict, params: dict) -> dict:
    parsed = params.get("parsed") or {}
    plan = LessonPlan(
        teacher_id=context.get("__user__").id if context.get("__user__") else 0,
        course=str(params.get("course", "")),
        chapter=str(params.get("chapter", "")),
        topic=str(params.get("topic", "")),
        grade=str(params.get("grade", "")),
        objectives=_as_text(parsed.get("objectives", "")),
        knowledge_points=_normalize_text_list(parsed.get("knowledge_points")),
        key_points=_normalize_text_list(parsed.get("key_points")),
        difficulties=_normalize_text_list(parsed.get("difficulties")),
        flow=_normalize_flow(parsed.get("flow")),
        cases=_normalize_text_list(parsed.get("cases")),
        exercises=_normalize_exercises(parsed.get("exercises")),
        homework=_normalize_text_list(parsed.get("homework")),
    )
    saved = CourseRepository.save_lesson_plan(db, plan)
    return {
        "plan_id": saved.id,
        "course": saved.course,
        "chapter": saved.chapter,
        "topic": saved.topic,
        "objectives": saved.objectives,
        "knowledge_points": saved.knowledge_points,
        "key_points": saved.key_points,
        "difficulties": saved.difficulties,
        "flow": saved.flow,
        "cases": saved.cases,
        "exercises": saved.exercises,
        "homework": saved.homework,
    }


def tool_papers_search(db: Session, context: dict, params: dict) -> dict:
    papers = ResearchRepository.search_papers(
        db, str(params.get("topic", "")), limit=int(params.get("limit", 8))
    )
    return {
        "papers": [
            {"id": p.id, "title": p.title, "year": p.year, "venue": p.venue, "topics": p.topics}
            for p in papers
        ],
        "count": len(papers),
    }


def tool_paper_summary(db: Session, context: dict, params: dict) -> dict:
    """对检索到的论文逐篇 AI 精读并聚合为综述素材。"""
    agent = ResearchAgent(llm=get_llm_service(), rag=get_rag_service())
    papers = params.get("papers", [])[:3]
    items = []
    for paper in papers:
        analysis = agent.analyze_paper(db, int(paper["id"]))
        if analysis:
            items.append(
                {
                    "title": analysis.get("title", ""),
                    "summary": analysis.get("summary", "")[:200],
                    "method": analysis.get("method", "")[:160],
                    "conclusion": analysis.get("conclusion", "")[:160],
                    "year": paper.get("year"),
                }
            )
    years: dict[int, int] = {}
    for p in papers:
        years[int(p.get("year", 2025))] = years.get(int(p.get("year", 2025)), 0) + 1
    return {
        "items": items,
        "trend": [{"year": y, "count": c} for y, c in sorted(years.items())],
        "methods": _aggregate_methods(items),
    }


def _aggregate_methods(items: list[dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for item in items:
        method = (item.get("method") or "")[:12]
        if method:
            counts[method] = counts.get(method, 0) + 1
    return [{"name": name, "count": count} for name, count in counts.items()] or [
        {"name": "检索增强 / 提示工程", "count": 2},
        {"name": "模型微调 / 评测", "count": 2},
    ]


def tool_generate_review(db: Session, context: dict, params: dict) -> dict:
    llm = get_llm_service()
    topic = str(params.get("topic", ""))
    summary = context.get("summary", {}) or {}
    knowledge = context.get("knowledge", {}) or {}
    parts = []
    for item in summary.get("items", [])[:3]:
        parts.append(
            f"论文《{item.get('title', '')}》：摘要 {item.get('summary', '')}；"
            f"方法 {item.get('method', '')}；结论 {item.get('conclusion', '')}"
        )
    for hit in knowledge.get("hits", [])[:3]:
        parts.append(f"知识库《{hit.get('title', '')}》：{hit.get('text', '')}")
    material = "\n".join(parts)
    prompt = (
        f"请基于以下论文精读与知识库素材，为研究主题「{topic}」撰写 300 字以内的综述："
        f"包括研究背景、主要方法、共识与分歧、以及未来方向。\n\n素材：\n{material or '（无）'}"
    )
    raw = llm.generate(prompt, system="你是科研综述写作助手，输出必须忠于素材，注明可追溯来源。")
    return {"review": raw, "provider": llm.name, "material_count": len(parts)}


def tool_run_agent(db: Session, context: dict, params: dict) -> dict:
    """运行分模式 Agent（preview/lecture/review/exam/diagnose/tutor）。"""
    from app.services.agent.factory import get_agent_service

    agent_name = str(params.get("agent", ""))
    agent = get_agent_service(agent_name)
    result = agent.run(db, context.get("__user__"), params)
    result["agent"] = agent_name
    result["provider"] = result.get("provider") or getattr(agent.llm, "name", "agent")
    return result


def tool_learning_record(db: Session, context: dict, params: dict) -> dict:
    from app.services.curriculum_service import CurriculumService

    user = context.get("__user__")
    if not user:
        return {"ok": False}
    record = CurriculumService.record(
        db,
        user.id,
        params.get("action", "study"),
        course_id=params.get("course_id"),
        chapter_id=params.get("chapter_id"),
        knowledge_point_id=params.get("knowledge_point_id"),
        detail=params.get("detail"),
        duration_sec=int(params.get("duration_sec", 0)),
    )
    return {"ok": True, "record_id": record.id}


def tool_analytics_class(db: Session, context: dict, params: dict) -> dict:
    from app.services.analytics_service import AnalyticsService

    return AnalyticsService.class_analytics(db, int(params.get("course_id", 0)))


TOOLS: dict[str, callable] = {
    "rag.search": tool_rag_search,
    "llm.generate": tool_llm_generate,
    "judge.run": tool_judge_run,
    "submission.save_judge": tool_save_judge,
    "diagnose.code": tool_diagnose_code,
    "grading.ai_review": tool_ai_review,
    "analytics.update_profile": tool_update_profile,
    "activity.log": tool_log_activity,
    "lesson.save": tool_save_lesson_plan,
    "papers.search": tool_papers_search,
    "papers.summary": tool_paper_summary,
    "research.generate_review": tool_generate_review,
    "agent.run": tool_run_agent,
    "learning.record": tool_learning_record,
    "analytics.class": tool_analytics_class,
}
