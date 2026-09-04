"""课程学习空间、测验、资料审核与教学诊断集成测试。"""

from tests.conftest import login


def test_course_space_overview_and_quiz(client):
    student = login(client, "student")
    sh = {"Authorization": f"Bearer {student['token']}"}
    courses = client.get("/api/curriculum/courses", headers=sh)
    assert courses.status_code == 200
    card = next((c for c in courses.json() if c["name"] == "数据结构"), None)
    assert card and "progress" in card and "mastery" in card
    course_id = card["id"]
    overview = client.get(f"/api/curriculum/courses/{course_id}/overview", headers=sh)
    assert overview.status_code == 200
    assert overview.json()["chapters"]
    chapters = client.get(f"/api/curriculum/courses/{course_id}/chapters", headers=sh).json()
    assert len(chapters) >= 3
    chapter_id = None
    for ch in chapters:
        view = client.get(f"/api/curriculum/chapters/{ch['id']}/view", headers=sh)
        if view.status_code == 200 and view.json()["knowledge_points"]:
            chapter_id = ch["id"]
            break
    assert chapter_id is not None
    # 预习生成
    preview = client.post(f"/api/curriculum/courses/{course_id}/chapters/{chapter_id}/preview", headers=sh)
    assert preview.status_code == 200
    preview_body = preview.json()
    assert preview_body.get("objectives")
    # 字段结构规范化：check 全为字符串，预习题为 {question, answer_hint}
    assert all(isinstance(c, str) for c in preview_body.get("check", []))
    assert all(set(q) == {"question", "answer_hint"} for q in preview_body.get("pre_questions", []))
    assert preview_body.get("ai_generated") is True
    assert preview_body.get("references")
    assert preview_body.get("workflow_run_id")
    p_run = client.get(f"/api/workflows/runs/{preview_body['workflow_run_id']}", headers=sh).json()
    assert [s["step_id"] for s in p_run["steps"]] == ["retrieve", "agent", "record"]
    # 讲堂生成
    lecture = client.post(
        f"/api/curriculum/chapters/{chapter_id}/lecture",
        headers=sh,
        json={"depth": "standard"},
    )
    assert lecture.status_code == 200
    lecture_body = lecture.json()
    assert lecture_body.get("sections")
    assert all(
        set(s) <= {"title", "content", "example", "code"} for s in lecture_body.get("sections", [])
    )
    assert all(
        set(e) == {"question", "answer_hint"} for e in lecture_body.get("exercises", [])
    )
    assert lecture_body.get("ai_generated") is True
    assert lecture_body.get("references")
    assert lecture_body.get("workflow_run_id")
    l_run = client.get(f"/api/workflows/runs/{lecture_body['workflow_run_id']}", headers=sh).json()
    assert "agent_standard" in [s["step_id"] for s in l_run["steps"]]
    # 测验生成与提交
    quiz = client.post(
        "/api/curriculum/quizzes",
        headers=sh,
        json={"course_id": course_id, "quiz_type": "chapter", "chapter_id": chapter_id},
    )
    assert quiz.status_code == 200
    paper = quiz.json()
    assert paper["questions"]
    assert paper.get("ai_generated") is True
    assert paper.get("references")
    answers = []
    for q in paper["questions"]:
        if q["qtype"] == "single":
            answers.append({"question_id": q["question_id"], "answer": 0})
        elif q["qtype"] == "judge":
            answers.append({"question_id": q["question_id"], "answer": True})
        else:
            answers.append({"question_id": q["question_id"], "answer": "这是一个示例答案。"})
    result = client.post(f"/api/curriculum/quizzes/{paper['quiz_id']}/submit", headers=sh, json={"answers": answers})
    assert result.status_code == 200
    body = result.json()
    assert "score" in body and "suggestions" in body
    assert body.get("ai_generated") is True
    # 课程答疑走独立工作流
    reply = client.post(
        "/api/ai/assistant",
        headers=sh,
        json={"agent": "learning", "payload": {"message": "什么是递归？", "mode": "hint", "history": []}},
    )
    assert reply.status_code == 200
    assert reply.json().get("answer")
    assert reply.json().get("workflow_run_id")


def test_student_material_review_flow(client):
    student = login(client, "student")
    sh = {"Authorization": f"Bearer {student['token']}"}
    teacher = login(client, "teacher")
    th = {"Authorization": f"Bearer {teacher['token']}"}
    courses = client.get("/api/curriculum/courses", headers=sh).json()
    course_id = next(c["id"] for c in courses if c["name"] == "数据结构")
    # 学生上传并申请共享
    files = {"file": ("共享笔记.md", "数据结构个人笔记：二叉树遍历有三种递归写法。".encode("utf-8"), "text/markdown")}
    up = client.post(
        f"/api/curriculum/courses/{course_id}/materials/upload",
        headers=sh,
        files=files,
        data={"scope": "shared", "title": "我的二叉树笔记"},
    )
    assert up.status_code == 200
    assert up.json()["review_pending"] is True
    # 学生资料列表应包含自己的私有（审核中）
    materials = client.get(f"/api/curriculum/courses/{course_id}/materials", headers=sh).json()
    assert any(m["title"] == "我的二叉树笔记" and m["source_level"] == "P" for m in materials)
    # 教师审核通过 → 变为 [A] 共享
    reviews = client.get("/api/knowledge/reviews?status=pending", headers=th).json()
    review = next(r for r in reviews if r["title"] == "我的二叉树笔记")
    approved = client.post(f"/api/knowledge/reviews/{review['id']}", headers=th, json={"action": "approve"})
    assert approved.status_code == 200
    materials2 = client.get(f"/api/curriculum/courses/{course_id}/materials", headers=sh).json()
    assert any(m["title"] == "我的二叉树笔记" and m["source_level"] == "A" and m["visibility"] == "shared" for m in materials2)
    # 清理
    doc_id = review["document_id"]
    client.delete(f"/api/knowledge/documents/{doc_id}", headers=th)


def test_teacher_diagnose_and_paper_compare(client):
    teacher = login(client, "teacher")
    th = {"Authorization": f"Bearer {teacher['token']}"}
    diag = client.post("/api/analytics/courses/1/diagnose", headers=th)
    assert diag.status_code == 200
    body = diag.json()
    assert body["diagnosis"]["suggestions"]
    assert body["diagnosis"].get("ai_generated") is True
    assert body["diagnosis"].get("references")
    researcher = login(client, "researcher")
    rh = {"Authorization": f"Bearer {researcher['token']}"}
    papers = client.get("/api/research/papers", headers=rh).json()
    ids = [p["id"] for p in papers[:3]]
    compared = client.post("/api/research/compare", headers=rh, json={"paper_ids": ids})
    assert compared.status_code == 200
    assert compared.json()["papers"]
    # 知识点 ↔ 论文
    related = client.get("/api/knowledge/points/3/related", headers=rh)
    assert related.status_code == 200
    assert "papers" in related.json()


def test_curriculum_data_complete():
    """所有课程都有完整章节与主要知识点，且同步幂等。"""
    from app.database import SessionLocal
    from app.models import Course, CourseChapter, KnowledgePoint
    from app.services.curriculum_sync import sync_curriculum

    db = SessionLocal()
    try:
        result = sync_curriculum(db)
        assert result["created_chapters"] == 0  # 幂等：已有章节不再重复创建
        course = db.query(Course).filter(Course.name == "数据结构").first()
        chapters = db.query(CourseChapter).filter_by(course_id=course.id).all()
        assert len(chapters) >= 8
        kps = db.query(KnowledgePoint).filter(KnowledgePoint.subject == "数据结构").all()
        assert len(kps) >= 8
        linked = (
            db.query(KnowledgePoint)
            .filter(
                KnowledgePoint.subject == "数据结构",
                KnowledgePoint.chapter_id.isnot(None),
            )
            .count()
        )
        assert linked >= 7
        # 7 门课都有章节；计算机组成原理也有主要知识点
        course2 = db.query(Course).filter(Course.name == "计算机组成原理").first()
        assert db.query(CourseChapter).filter_by(course_id=course2.id).count() >= 6
        assert db.query(KnowledgePoint).filter(KnowledgePoint.subject == "计算机组成原理").count() >= 6
    finally:
        db.close()
