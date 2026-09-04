"""API 集成测试：认证、RBAC 与业务闭环。"""

from tests.conftest import login


def wait_job(client, headers: dict, job_id: int, timeout: float = 90.0) -> int:
    """轮询知识库后台任务直到完成，返回创建的 document_id。"""
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        jobs = client.get("/api/knowledge/jobs", headers=headers).json()
        job = next((j for j in jobs if j["id"] == job_id), None)
        if not job:
            raise AssertionError("任务不存在")
        if job["status"] == "success":
            return job["result"]["document_id"]
        if job["status"] == "failed":
            raise AssertionError(f"任务失败：{job['error']}")
        time.sleep(0.5)
    raise AssertionError("任务超时")


def test_health_and_demo_login(client):
    assert client.get("/api/health").json()["status"] == "ok"
    teacher = login(client, "teacher")
    assert teacher["user"]["role"] == "teacher"
    assert teacher["token"]


def test_teacher_dashboard_data(client):
    teacher = login(client, "teacher")
    headers = {"Authorization": f"Bearer {teacher['token']}"}
    courses = client.get("/api/courses", headers=headers)
    assert courses.status_code == 200
    assert len(courses.json()) >= 3
    worklist = client.get("/api/grading/worklist", headers=headers)
    assert worklist.status_code == 200
    assert worklist.json()


def test_student_submissions_and_rbac(client):
    student = login(client, "student")
    headers = {"Authorization": f"Bearer {student['token']}"}
    submissions = client.get("/api/me/submissions", headers=headers)
    assert submissions.status_code == 200
    mine = submissions.json()
    assert mine
    my_id = mine[0]["submission_id"]
    detail = client.get(f"/api/submissions/{my_id}", headers=headers)
    assert detail.status_code == 200
    # 学生不能查看其他学生（student2）的提交
    other_login = client.post(
        "/api/auth/login", json={"username": "student2", "password": "123456"}
    ).json()
    other_headers = {"Authorization": f"Bearer {other_login['token']}"}
    other_subs = client.get("/api/me/submissions", headers=other_headers).json()
    other_id = other_subs[0]["submission_id"]
    resp = client.get(f"/api/submissions/{other_id}", headers=headers)
    assert resp.status_code == 403
    # student2 也看不到 student1 的提交
    resp2 = client.get(f"/api/submissions/{my_id}", headers=other_headers)
    assert resp2.status_code == 403


def test_teacher_grading_flow(client):
    teacher = login(client, "teacher")
    headers = {"Authorization": f"Bearer {teacher['token']}"}
    worklist = client.get("/api/grading/worklist", headers=headers).json()
    pending = next((w for w in worklist if w["teacher_score"] is None), None)
    if not pending:
        return
    # AI 建议批改
    review = client.post(f"/api/submissions/{pending['submission_id']}/ai-review", headers=headers)
    assert review.status_code == 200
    assert review.json()["suggestion_score"] is not None
    # 教师确认
    grade = client.post(
        f"/api/submissions/{pending['submission_id']}/grade",
        headers=headers,
        json={"final_score": 8.5, "comment": "批改通过"},
    )
    assert grade.status_code == 200
    assert grade.json()["status"] == "graded"


def test_student_code_submit_and_diagnosis(client):
    student = login(client, "student")
    headers = {"Authorization": f"Bearer {student['token']}"}
    # 找到一门课的编程题
    assignments = client.get("/api/assignments", headers=headers).json()
    prog = None
    for a in assignments:
        for q in a["questions"]:
            if q["qtype"] == "programming":
                prog = (a["id"], q["id"])
                break
        if prog:
            break
    assert prog
    resp = client.post(
        f"/api/assignments/{prog[0]}/questions/{prog[1]}/submit",
        headers=headers,
        json={"source_code": "def reverse_list(head):\n    pass\n", "language": "python"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] in ("accepted", "wrong_answer", "compile_error")
    diagnosis = client.post(
        "/api/learning/diagnose",
        headers=headers,
        json={
            "question_title": "反转单链表",
            "source_code": body["source_code"] if False else "def reverse_list(head):\n    pass\n",
            "language": "python",
            "judge_report": body["judge_report"],
            "error_message": body["error_message"],
            "mode": "hint",
        },
    )
    assert diagnosis.status_code == 200
    assert diagnosis.json()["error_reason"]


def test_knowledge_crud(client):
    teacher = login(client, "teacher")
    headers = {"Authorization": f"Bearer {teacher['token']}"}
    created = client.post(
        "/api/knowledge/documents",
        headers=headers,
        data={
            "title": "测试文档：图的拓扑排序",
            "course": "数据结构",
            "content": "拓扑排序是对有向无环图（DAG）顶点的一种线性排序。实验讲义：首先计算各顶点入度，将入度为 0 的顶点入队，依次出队并删除相关边。",
            "topic": "图",
            "chapter": "第 5 章",
            "source": "测试讲义",
            "type": "讲义",
            "difficulty": "难",
            "year": "2026",
        },
    )
    assert created.status_code == 200, created.text
    doc_id = created.json()["id"]
    docs = client.get("/api/knowledge/documents?course=数据结构", headers=headers)
    assert any(d["id"] == doc_id for d in docs.json())
    reindex = client.post(f"/api/knowledge/documents/{doc_id}/reindex", headers=headers)
    assert reindex.status_code == 200
    deleted = client.delete(f"/api/knowledge/documents/{doc_id}", headers=headers)
    assert deleted.status_code == 200
    after = client.get(f"/api/knowledge/documents/{doc_id}", headers=headers)
    assert after.status_code == 404


def test_research_workbench_and_explore(client):
    researcher = login(client, "researcher")
    headers = {"Authorization": f"Bearer {researcher['token']}"}
    wb = client.get("/api/research/workbench", headers=headers)
    assert wb.status_code == 200
    assert wb.json()["topics"]
    explore = client.post("/api/research/explore", headers=headers, json={"topic": "RAG"})
    assert explore.status_code == 200
    assert explore.json()["papers"]
    analyze = client.post("/api/research/papers/1/analyze", headers=headers)
    assert analyze.status_code == 200
    assert analyze.json()["summary"]


def test_student_learning_path(client):
    student = login(client, "student")
    headers = {"Authorization": f"Bearer {student['token']}"}
    recs = client.get("/api/learning/recommendations", headers=headers)
    assert recs.status_code == 200
    assert recs.json()
    profile = client.get("/api/analytics/me", headers=headers)
    assert profile.status_code == 200


def test_knowledge_upload_with_metadata(client):
    """上传走后台任务，完成后保存与“编辑”一致的元数据。"""
    teacher = login(client, "teacher")
    headers = {"Authorization": f"Bearer {teacher['token']}"}
    files = {
        "file": (
            "算法讲义.md",
            "# 测试\n哈希表通过哈希函数把关键字映射到存储位置，冲突处理常用链地址法与开放定址法。".encode("utf-8"),
            "text/markdown",
        )
    }
    data = {
        "course": "数据结构",
        "title": "自定义上传标题",
        "topic": "查找与哈希",
        "chapter": "第 7 章",
        "source": "测试来源",
        "difficulty": "难",
        "type": "讲义",
        "year": "2026",
    }
    resp = client.post("/api/knowledge/upload", headers=headers, files=files, data=data)
    assert resp.status_code == 200, resp.text
    job_id = resp.json()["job_id"]
    doc_id = wait_job(client, headers, job_id)
    body = client.get(f"/api/knowledge/documents/{doc_id}", headers=headers).json()
    assert body["title"] == "自定义上传标题"
    assert body["topic"] == "查找与哈希"
    assert body["chapter"] == "第 7 章"
    assert body["source"] == "测试来源"
    assert body["difficulty"] == "难"
    assert body["type"] == "讲义"
    # 清理
    client.delete(f"/api/knowledge/documents/{body['id']}", headers=headers)


def test_register_login_flow(client):
    """注册（用户名唯一、密码校验）→ 自动登录 → 再次登录。"""
    payload = {
        "username": "newstudent",
        "password": "123456",
        "display_name": "新同学",
        "identity": "undergraduate",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["username"] == "newstudent"
    assert body["token"]
    # 用户名重复
    dup = client.post("/api/auth/register", json=payload)
    assert dup.status_code == 400
    # 密码过短
    short = client.post(
        "/api/auth/register",
        json={"username": "shortpw", "password": "123", "display_name": "短密码", "identity": "undergraduate"},
    )
    assert short.status_code == 400
    # 用新账号登录
    login = client.post("/api/auth/login", json={"username": "newstudent", "password": "123456"})
    assert login.status_code == 200
    assert login.json()["user"]["display_name"] == "新同学"


def test_course_invite_and_delete(client):
    teacher = login(client, "teacher")
    th = {"Authorization": f"Bearer {teacher['token']}"}
    created = client.post(
        "/api/courses",
        headers=th,
        json={"name": "测试课程", "code": "TST999", "description": "用于测试", "semester": "2026 春季"},
    )
    assert created.status_code == 200, created.text
    course_id = created.json()["id"]
    # 教师查看学生列表（邀请前为空）
    students = client.get(f"/api/courses/{course_id}/students", headers=th)
    assert students.status_code == 200 and students.json() == []
    # 第一步：教师邀请 student1 → 生成待接受邀请（不直接选课）
    invite = client.post(
        f"/api/courses/{course_id}/invite", headers=th, json={"student_username": "student1"}
    )
    assert invite.status_code == 200
    assert invite.json()["student"]["display_name"] == "李明"
    assert invite.json()["invitation"]["status"] == "pending"
    # 重复邀请（待接受中）
    again = client.post(
        f"/api/courses/{course_id}/invite", headers=th, json={"student_username": "student1"}
    )
    assert again.status_code == 400
    # 第二步：学生端此时还看不到该课程，但能看到待接受邀请
    student = login(client, "student")
    sh = {"Authorization": f"Bearer {student['token']}"}
    mine = client.get("/api/courses", headers=sh).json()
    assert not any(c["id"] == course_id for c in mine)
    invites = client.get("/api/course-invitations", headers=sh).json()
    assert invites and any(i["course_id"] == course_id for i in invites)
    pending_id = next(i["id"] for i in invites if i["course_id"] == course_id)
    # 第三步：学生接受邀请 → 正式选课
    accepted = client.post(f"/api/course-invitations/{pending_id}/accept", headers=sh)
    assert accepted.status_code == 200
    mine2 = client.get("/api/courses", headers=sh).json()
    assert any(c["id"] == course_id for c in mine2)
    teacher_view = client.get(f"/api/courses/{course_id}/invitations", headers=th).json()
    assert teacher_view[0]["status"] == "accepted"
    # 非本课程教师不能管理
    reg = client.post(
        "/api/auth/register",
        json={"username": "otherteacher", "password": "123456", "display_name": "别的老师", "identity": "teacher"},
    ).json()
    oh = {"Authorization": f"Bearer {reg['token']}"}
    forbidden = client.post(
        f"/api/courses/{course_id}/invite", headers=oh, json={"student_username": "student1"}
    )
    assert forbidden.status_code == 403
    # 删除课程
    deleted = client.delete(f"/api/courses/{course_id}", headers=th)
    assert deleted.status_code == 200
    gone = client.get(f"/api/courses/{course_id}", headers=th)
    assert gone.status_code == 404


def test_invitation_decline_and_cancel(client):
    teacher = login(client, "teacher")
    th = {"Authorization": f"Bearer {teacher['token']}"}
    course = client.post(
        "/api/courses",
        headers=th,
        json={"name": "邀请流程课程", "code": "INV2026", "semester": "2026 春季"},
    ).json()
    course_id = course["id"]
    # 邀请 student2 → 学生拒绝
    client.post(f"/api/courses/{course_id}/invite", headers=th, json={"student_username": "student2"})
    s2 = client.post("/api/auth/login", json={"username": "student2", "password": "123456"}).json()
    s2h = {"Authorization": f"Bearer {s2['token']}"}
    inv2 = client.get("/api/course-invitations", headers=s2h).json()
    inv2_id = next(i["id"] for i in inv2 if i["course_id"] == course_id)
    declined = client.post(f"/api/course-invitations/{inv2_id}/decline", headers=s2h)
    assert declined.status_code == 200
    # 教师可对已拒绝学生重新邀请
    reinvite = client.post(f"/api/courses/{course_id}/invite", headers=th, json={"student_username": "student2"})
    assert reinvite.status_code == 200
    # 邀请 student3 → 教师撤销
    client.post(f"/api/courses/{course_id}/invite", headers=th, json={"student_username": "student3"})
    inv3 = client.get(f"/api/courses/{course_id}/invitations", headers=th).json()
    inv3_id = next(i["id"] for i in inv3 if i["student_username"] == "student3")
    cancelled = client.post(f"/api/course-invitations/{inv3_id}/cancel", headers=th)
    assert cancelled.status_code == 200
    # 清理
    client.delete(f"/api/courses/{course_id}", headers=th)


def test_kb_subjects_match_teacher_courses(client):
    """知识库学科分类与当前教师的课程管理完全一致（含 0 文档新课程，且互不可见）。"""
    teacher = login(client, "teacher")
    th = {"Authorization": f"Bearer {teacher['token']}"}
    course = client.post(
        "/api/courses",
        headers=th,
        json={"name": "分类一致性课程", "code": "KB999", "semester": "2026 秋季"},
    ).json()
    subjects = client.get("/api/knowledge/subjects", headers=th).json()
    assert any(s["course"] == "分类一致性课程" for s in subjects)
    assert all(isinstance(s["doc_count"], int) for s in subjects)
    # 另一位教师看不到不属于自己的课程
    other = client.post(
        "/api/auth/register",
        json={"username": "otherteacher2", "password": "123456", "display_name": "第二位老师", "identity": "teacher"},
    ).json()
    oh = {"Authorization": f"Bearer {other['token']}"}
    other_subjects = client.get("/api/knowledge/subjects", headers=oh).json()
    assert not any(s["course"] == "分类一致性课程" for s in other_subjects)
    client.delete(f"/api/courses/{course['id']}", headers=th)


def test_lesson_plan_history_and_tutor_history(client):
    """教案自动保存可查看/删除；导师对话自动保存可清空。"""
    teacher = login(client, "teacher")
    th = {"Authorization": f"Bearer {teacher['token']}"}
    plan = client.post(
        "/api/workflows/lesson_plan/run",
        headers=th,
        json={"course": "数据结构", "chapter": "第 4 章", "topic": "历史教案测试", "grade": "大二", "objective": ""},
    ).json()
    assert plan["status"] == "success"
    plans = client.get("/api/lesson-plans", headers=th).json()
    saved = next(p for p in plans if p["topic"] == "历史教案测试")
    detail = client.get(f"/api/lesson-plans/{saved['id']}", headers=th).json()
    assert detail["course"] == "数据结构"
    deleted = client.delete(f"/api/lesson-plans/{saved['id']}", headers=th)
    assert deleted.status_code == 200
    gone = client.get(f"/api/lesson-plans/{saved['id']}", headers=th)
    assert gone.status_code == 404

    # 导师对话历史：发送消息后自动保存，清空后为空
    student = login(client, "student")
    sh = {"Authorization": f"Bearer {student['token']}"}
    client.post(
        "/api/learning/tutor",
        headers=sh,
        json={"message": "什么是递归？", "mode": "hint", "history": []},
    )
    msgs = client.get("/api/learning/history?agent_type=learning", headers=sh).json()
    assert any(m["role"] == "assistant" for m in msgs)
    cleared = client.delete("/api/learning/history", headers=sh)
    assert cleared.status_code == 200
    assert client.get("/api/learning/history?agent_type=learning", headers=sh).json() == []
