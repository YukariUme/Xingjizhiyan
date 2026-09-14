"""测验服务：章节测验 / 模拟考试 / 薄弱专项 / 错题重测（客观题自动评分，代码题接入 CodeJudge）。"""

import hashlib

from sqlalchemy.orm import Session

from app.database import utcnow
from app.models import (
    Course,
    CourseChapter,
    KnowledgePoint,
    Quiz,
    QuizQuestion,
    QuizResult,
    StudentKnowledgeProfile,
    User,
)
from app.services.analytics_service import AnalyticsService
from app.services.curriculum_service import CurriculumService
from app.services.judge.factory import get_judge_service


def _kp_pick(db: Session, quiz_type: str, course_id: int, student_id: int, chapter_id: int | None) -> list[KnowledgePoint]:
    if quiz_type == "chapter" and chapter_id:
        ids = CurriculumService.chapter_kp_ids(db, chapter_id)
    else:
        ids = CurriculumService.course_kp_ids(db, course_id)
    kps = [db.get(KnowledgePoint, kp_id) for kp_id in ids if db.get(KnowledgePoint, kp_id)]
    if quiz_type == "mock":
        return kps[:10]
    if quiz_type == "weakness":
        profiles = (
            db.query(StudentKnowledgeProfile)
            .filter(StudentKnowledgeProfile.student_id == student_id)
            .all()
        )
        weak_ids = {p.knowledge_point_id for p in profiles if (p.mastery or 0) < 60}
        return [kp for kp in kps if kp.id in weak_ids][:8]
    if quiz_type == "wrong_retest":
        profiles = (
            db.query(StudentKnowledgeProfile)
            .filter(StudentKnowledgeProfile.student_id == student_id)
            .all()
        )
        wrong_ids = {p.knowledge_point_id for p in profiles if (p.errors or 0) > 0}
        return [kp for kp in kps if kp.id in wrong_ids][:8]
    return kps[:8]


def _make_single(kp: KnowledgePoint) -> QuizQuestion:
    digest = int(hashlib.md5(kp.name.encode()).hexdigest()[:4], 16)
    options = [
        kp.description[:80],
        "它与课程其他内容无关，不需要前置知识",
        "它只会在考试中出现，实践中用不到",
        "它已经被淘汰，不必学习",
    ]
    if digest % 2:
        options[0], options[1] = options[1], options[0]
    return QuizQuestion(
        qtype="single",
        title=f"下列关于「{kp.name}」的描述，最准确的是？",
        options=options,
        answer={"index": options.index(kp.description[:80])},
        analysis=kp.description,
        knowledge_point_ids=[kp.id],
        max_score=5,
    )


def _make_judge(kp: KnowledgePoint) -> QuizQuestion:
    return QuizQuestion(
        qtype="judge",
        title=f"「{kp.name}」属于课程《{kp.subject}》的「{kp.chapter}」内容，且在实际问题中有典型应用。（判断正误）",
        options=["正确", "错误"],
        answer={"value": True},
        analysis=kp.description,
        knowledge_point_ids=[kp.id],
        max_score=3,
    )


def _make_short(kp: KnowledgePoint) -> QuizQuestion:
    keywords = [k for k in re_split(kp.description) if len(k) >= 2][:6] or [kp.name]
    return QuizQuestion(
        qtype="short",
        title=f"简述「{kp.name}」的核心概念，并给出一个典型应用场景。",
        options=[],
        answer={"keywords": keywords, "max_score": 8},
        analysis=kp.description,
        knowledge_point_ids=[kp.id],
        max_score=8,
    )


def _make_code(kp: KnowledgePoint) -> QuizQuestion:
    return QuizQuestion(
        qtype="code",
        title=f"用代码实现「{kp.name}」的一个典型操作（可定义辅助函数）。",
        options=[],
        answer={
            "language": "python",
            "test_cases": [
                {"id": 1, "name": "函数定义", "check": "contains", "value": "def", "hint": "需要定义函数"},
                {"id": 2, "name": "主体逻辑", "check": "contains", "value": "return", "hint": "需要返回结果"},
            ],
            "max_score": 10,
        },
        analysis="代码题将接入 CodeJudgeService 自动评测。",
        knowledge_point_ids=[kp.id],
        max_score=10,
    )


import re


def re_split(text: str) -> list[str]:
    return [p.strip("，。；；:：") for p in re.split(r"[，。；、]", text or "")]


def build_quiz(
    db: Session,
    course_id: int,
    student: User,
    quiz_type: str = "chapter",
    chapter_id: int | None = None,
    scope_kp_ids: list[int] | None = None,
) -> Quiz:
    course = db.get(Course, course_id)
    kps = _kp_pick(db, quiz_type, course_id, student.id, chapter_id)
    if scope_kp_ids:
        kps = [kp for kp in kps if kp.id in scope_kp_ids][:8]
    quiz = Quiz(
        course_id=course_id,
        chapter_id=chapter_id,
        title=f"《{course.name if course else ''}》测验 · {quiz_type}",
        quiz_type=quiz_type,
        created_by=student.id,
    )
    db.add(quiz)
    db.flush()
    questions = []
    for index, kp in enumerate(kps[:8], start=1):
        maker = [_make_single, _make_judge, _make_short, _make_code][index % 4]
        question = maker(kp)
        question.quiz_id = quiz.id
        question.order = index
        db.add(question)
        questions.append(question)
    db.commit()
    db.refresh(quiz)
    return quiz


def _grade_question(db: Session, question: QuizQuestion, answer) -> tuple[float, bool]:
    """返回 (得分, 是否通过)。"""
    if question.qtype == "single":
        ok = answer == question.answer.get("index")
        return (question.max_score if ok else 0.0), ok
    if question.qtype == "judge":
        ok = bool(answer) == bool(question.answer.get("value"))
        return (question.max_score if ok else 0.0), ok
    if question.qtype == "multiple":
        correct = set(question.answer.get("indexes", []))
        chosen = set(answer or [])
        ok = correct == chosen
        return (question.max_score if ok else 0.0), ok
    if question.qtype == "code":
        result = get_judge_service().judge(
            str(answer or ""),
            question.answer.get("language", "python"),
            question.answer.get("test_cases", []),
        )
        score = question.max_score * result.passed_tests / max(1, result.total_tests)
        return round(score, 1), result.verdict == "accepted"
    # short / analysis：按关键词命中率给分
    keywords = question.answer.get("keywords", [])
    text = str(answer or "")
    hits = sum(1 for k in keywords if k in text)
    ratio = hits / max(1, len(keywords))
    return round(question.max_score * ratio, 1), ratio >= 0.6


def submit_quiz(db: Session, quiz_id: int, student: User, answers: list[dict]) -> dict:
    quiz = db.get(Quiz, quiz_id)
    if not quiz:
        raise ValueError("测验不存在")
    questions = (
        db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.order).all()
    )
    answer_map = {a.get("question_id"): a.get("answer") for a in answers}
    details = []
    total_score = 0.0
    max_score = sum(q.max_score for q in questions)
    kp_results: dict[int, list[bool]] = {}
    for question in questions:
        answer = answer_map.get(question.id)
        score, ok = _grade_question(db, question, answer)
        total_score += score
        details.append(
            {
                "question_id": question.id,
                "qtype": question.qtype,
                "title": question.title,
                "score": score,
                "max_score": question.max_score,
                "correct": ok,
                "analysis": question.analysis,
                "knowledge_point_ids": question.knowledge_point_ids,
            }
        )
        for kp_id in question.knowledge_point_ids:
            kp_results.setdefault(kp_id, []).append(ok)
            AnalyticsService.update_profile_from_result(
                db,
                student.id,
                question,
                correct=ok,
                score=score,
            )
    weak = []
    for kp_id, results in kp_results.items():
        accuracy = sum(results) / len(results)
        if accuracy < 0.6:
            kp = db.get(KnowledgePoint, kp_id)
            weak.append({"knowledge_point_id": kp_id, "name": kp.name if kp else f"知识点 {kp_id}", "accuracy": round(accuracy * 100, 1)})
    suggestions = [
        {
            "step": f"复习「{w['name']}」",
            "detail": f"本次正确率 {w['accuracy']}%，建议先完成章节复习与强化练习。",
        }
        for w in sorted(weak, key=lambda x: x["accuracy"])[:4]
    ]
    if not suggestions:
        suggestions = [{"step": "进入下一阶段", "detail": "本次测验表现良好，建议预习下一章节或阅读相关论文。"}]
    result = QuizResult(
        quiz_id=quiz.id,
        student_id=student.id,
        score=round(total_score, 1),
        max_score=max_score,
        answers=answers,
        details={"questions": details, "suggestions": suggestions, "weak": weak},
        finished_at=utcnow(),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    AnalyticsService.refresh_student_learning_state(db, student.id)
    return {
        "result_id": result.id,
        "score": result.score,
        "max_score": result.max_score,
        "accuracy": round(100 * result.score / max(1, result.max_score), 1),
        "weak_points": weak,
        "suggestions": suggestions,
        "details": details,
    }
