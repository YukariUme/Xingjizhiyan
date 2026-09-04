"""工作流引擎与 RAG 落地/回退单元测试。"""

from app.database import SessionLocal
from app.models import LessonPlan, Submission, User
from app.services.rag.factory import get_rag_service
from app.services.workflow.service import WorkflowService, _resolve
from app.services.workflow.tools import (
    _normalize_exercises,
    _normalize_flow,
    _normalize_text_list,
)


def _user(db, role: str) -> User:
    return db.query(User).filter(User.role == role).first()


def test_lesson_plan_workflow_with_branch():
    db = SessionLocal()
    try:
        teacher = _user(db, "teacher")
        run = WorkflowService.run(
            db,
            "lesson_plan",
            {
                "course": "数据结构",
                "chapter": "第 4 章 树",
                "topic": "二叉树遍历",
                "grade": "大二",
                "objective": "掌握三种遍历",
            },
            teacher,
        )
        assert run.status == "success"
        step_ids = [s.step_id for s in run.steps]
        assert step_ids == ["retrieve", "generate", "branch", "case_analysis", "save"]
        assert run.output_json["save"]["topic"] == "二叉树遍历"
        assert db.query(LessonPlan).filter(LessonPlan.id == run.output_json["save"]["plan_id"]).first()
    finally:
        db.close()


def test_lesson_plan_programming_branch():
    db = SessionLocal()
    try:
        teacher = _user(db, "teacher")
        run = WorkflowService.run(
            db,
            "lesson_plan",
            {
                "course": "数据结构",
                "chapter": "第 4 章",
                "topic": "编程题：二叉树遍历实现",
                "grade": "大二",
                "objective": "",
            },
            teacher,
        )
        assert run.status == "success"
        assert "code_case" in [s.step_id for s in run.steps]
    finally:
        db.close()


def test_research_review_workflow():
    db = SessionLocal()
    try:
        researcher = _user(db, "researcher")
        run = WorkflowService.run(db, "research_review", {"topic": "RAG"}, researcher)
        assert run.status == "success"
        assert [s.step_id for s in run.steps] == [
            "papers",
            "branch",
            "summary",
            "knowledge",
            "generate_review",
        ]
        assert len(run.output_json["summary"]["items"]) >= 1
        assert run.output_json["generate_review"]["review"]
    finally:
        db.close()


def test_research_review_fallback_when_no_papers():
    db = SessionLocal()
    try:
        researcher = _user(db, "researcher")
        run = WorkflowService.run(
            db, "research_review", {"topic": "量子引力拓扑学的教育应用"}, researcher
        )
        assert run.status == "success"
        assert [s.step_id for s in run.steps] == ["papers", "branch", "llm_only"]
        assert run.output_json["llm_only"]["review"]
    finally:
        db.close()


def test_assignment_loop_workflow_awaits_teacher():
    db = SessionLocal()
    try:
        student = _user(db, "student")
        submission = db.query(Submission).filter(Submission.qtype == "subjective").first()
        run = WorkflowService.run(
            db,
            "assignment_loop",
            {
                "submission_id": submission.id,
                "qtype": "subjective",
                "assignment_id": submission.assignment_id,
                "question_id": submission.question_id,
                "source_code": "",
                "language": "python",
                "test_cases": [],
                "question_title": "测试题",
                "question_description": "",
            },
            student,
        )
        assert run.status == "awaiting_approval"
        assert [s.step_id for s in run.steps] == ["branch_type", "ai_review", "activity_sub", "approve"]
        teacher = _user(db, "teacher")
        finished = WorkflowService.approve(
            db, run.id, teacher, {"final_score": 8.0, "comment": "ok"}
        )
        assert finished.status == "success"
    finally:
        db.close()


def test_rag_grounding_and_fallback():
    db = SessionLocal()
    try:
        rag = get_rag_service()
        hit = rag.generate_answer(db, "二叉树的前序遍历怎么写", top_k=3)
        assert hit["grounded"] is True
        assert hit["references"]
        assert hit["confidence"] > 0
        miss = rag.generate_answer(db, "今天中午吃什么比较健康", top_k=3)
        assert miss["grounded"] is False
        assert miss["references"] == []
        assert miss["answer"]
    finally:
        db.close()


def test_workflow_placeholder_resolution():
    """内嵌占位符与点路径解析（防止 {course} {topic} 被误当成单一表达式）。"""
    context = {
        "course": "数据结构",
        "topic": "二叉树遍历",
        "judge": {"passed_tests": 2, "total_tests": 3},
    }
    assert _resolve("{course} {topic}", context) == "数据结构 二叉树遍历"
    assert _resolve("{judge.passed_tests}/{judge.total_tests}", context) == "2/3"
    assert _resolve("普通字符串", context) == "普通字符串"


def test_lesson_plan_field_normalization():
    """真实 LLM 返回对象数组时，教案字段规范成字符串/标准结构（防止前端渲染崩溃）。"""
    assert _normalize_text_list(
        [{"title": "案例A", "description": "讲解稳定匹配"}, "普通案例"]
    ) == ["案例A：讲解稳定匹配", "普通案例"]
    assert _normalize_exercises(
        [{"title": "练习1", "description": "实现算法"}, {"title": "练习2", "desc": "手写推导"}]
    ) == [
        {"title": "练习1", "desc": "实现算法"},
        {"title": "练习2", "desc": "手写推导"},
    ]
    assert _normalize_flow(
        [{"step": "导入", "content": "案例导入"}, {"name": "总结", "desc": "回顾"}]
    ) == [
        {"step": "导入", "content": "案例导入"},
        {"step": "总结", "content": "回顾"},
    ]
