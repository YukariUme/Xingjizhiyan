"""端到端冒烟脚本：工作流 + 提交闭环 + RAG 落地/回退 + 科研综述。

用法（后端运行在 8000 端口时）：
    python -m scripts.smoke
"""

import httpx

BASE = "http://127.0.0.1:8000"


def login(client: httpx.Client, username: str) -> dict:
    resp = client.post("/api/auth/login", json={"username": username, "password": "123456"})
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    client = httpx.Client(base_url=BASE, timeout=60)
    teacher = login(client, "teacher1")
    student = login(client, "student1")
    researcher = login(client, "researcher1")
    th = {"Authorization": f"Bearer {teacher['token']}"}
    sh = {"Authorization": f"Bearer {student['token']}"}
    rh = {"Authorization": f"Bearer {researcher['token']}"}

    defs = client.get("/api/workflows", headers=th).json()
    print("工作流定义:", [d["id"] for d in defs])

    # 备课工作流
    plan = client.post(
        "/api/workflows/lesson_plan/run",
        headers=th,
        json={
            "course": "数据结构",
            "chapter": "第 4 章 树",
            "topic": "二叉树遍历",
            "grade": "大二",
            "objective": "掌握三种遍历",
        },
    ).json()
    print("备课工作流:", plan["status"], [(s["step_id"], s["status"]) for s in plan["steps"]])

    # 学生提交编程题（错误代码 → 自动诊断）
    assignments = client.get("/api/assignments", headers=sh).json()
    prog = next(
        ((a["id"], q["id"]) for a in assignments for q in a["questions"] if q["qtype"] == "programming"),
        None,
    )
    assert prog, "没有找到编程题"
    sub = client.post(
        f"/api/assignments/{prog[0]}/questions/{prog[1]}/submit",
        headers=sh,
        json={"source_code": "def reverse_list(head):\n    pass\n", "language": "python"},
    ).json()
    print(
        "编程提交:",
        sub["verdict"],
        f"{sub['passed_tests']}/{sub['total_tests']}",
        "| 工作流 #",
        sub.get("workflow_run_id"),
        "| 诊断:",
        bool(sub.get("diagnosis", {}).get("error_reason")),
    )
    run = client.get(f"/api/workflows/runs/{sub['workflow_run_id']}", headers=sh).json()
    print("  步骤:", [(s["step_id"], s["status"]) for s in run["steps"]])

    # 简答题提交 → AI 建议 → 等待教师审批
    subj = next(
        ((a["id"], q["id"]) for a in assignments for q in a["questions"] if q["qtype"] == "subjective"),
        None,
    )
    sub2 = client.post(
        f"/api/assignments/{subj[0]}/questions/{subj[1]}/submit",
        headers=sh,
        json={"content": "栈是后进先出（LIFO）结构，队列是先进先出（FIFO）结构。栈用于括号匹配与表达式求值，队列用于任务调度与广度优先搜索。"},
    ).json()
    print("简答提交:", sub2["status"], "| AI 建议:", sub2["ai_suggestion_score"], "| 工作流 #", sub2.get("workflow_run_id"))
    run2 = client.get(f"/api/workflows/runs/{sub2['workflow_run_id']}", headers=sh).json()
    print("  步骤:", [(s["step_id"], s["status"]) for s in run2["steps"]])

    if run2["status"] == "awaiting_approval":
        grade = client.post(
            f"/api/submissions/{sub2['submission_id']}/grade",
            headers=th,
            json={"final_score": 9.0, "comment": "作答清晰"},
        ).json()
        run2b = client.get(f"/api/workflows/runs/{run2['id']}", headers=sh).json()
        print("教师审批:", grade["status"], "→ 工作流:", run2b["status"])

    # 科研综述工作流
    review = client.post("/api/workflows/research_review/run", headers=rh, json={"topic": "RAG"}).json()
    print(
        "科研综述:",
        review["status"],
        [(s["step_id"], s["status"]) for s in review["steps"]],
        "| 综述长度:",
        len(review["output"].get("generate_review", {}).get("review", "")),
    )

    # RAG 落地 / 回退
    hit = client.post(
        "/api/learning/tutor",
        headers=sh,
        json={"message": "什么是二叉树的先序遍历？", "mode": "hint", "history": []},
    ).json()
    print("导师回答 grounded:", hit.get("grounded"), "| 引用:", len(hit["references"]), "| 置信度:", hit.get("confidence"))
    miss = client.post(
        "/api/learning/tutor",
        headers=sh,
        json={"message": "附近有什么好吃的川菜馆？", "mode": "hint", "history": []},
    ).json()
    print("未命中回退 grounded:", miss.get("grounded"), "| 引用:", len(miss["references"]))

    # 多语言提交：Java 实现反转单链表（函数名驼峰 + None→null 等价）
    prog2 = next(
        ((a["id"], q["id"]) for a in assignments for q in a["questions"] if q["qtype"] == "programming" and "链表" in q["title"]),
        prog,
    )
    java_code = (
        "class Solution {\n"
        "    public ListNode reverseList(ListNode head) {\n"
        "        ListNode prev = null;\n"
        "        while (head != null) {\n"
        "            ListNode nxt = head.next;\n"
        "            head.next = prev;\n"
        "            prev = head;\n"
        "            head = nxt;\n"
        "        }\n"
        "        return prev;\n"
        "    }\n"
        "}"
    )
    java_sub = client.post(
        f"/api/assignments/{prog2[0]}/questions/{prog2[1]}/submit",
        headers=sh,
        json={"source_code": java_code, "language": "java"},
    ).json()
    print("Java 提交:", java_sub["verdict"], f"{java_sub['passed_tests']}/{java_sub['total_tests']}")

    # 知识库上传：与编辑一致的元数据
    up_job = client.post(
        "/api/knowledge/upload",
        headers=th,
        files={
            "file": (
                "C语言讲义.md",
                "C 语言是过程式编程语言，支持指针与手动内存管理。".encode("utf-8"),
                "text/markdown",
            )
        },
        data={
            "course": "数据结构",
            "title": "C 语言基础",
            "topic": "C 语言",
            "chapter": "第 0 章",
            "source": "课程讲义",
            "difficulty": "易",
            "type": "讲义",
            "year": "2026",
        },
    ).json()
    import time

    deadline = time.time() + 120
    doc_id = None
    while time.time() < deadline:
        jobs = client.get("/api/knowledge/jobs", headers=th).json()
        job = next((j for j in jobs if j["id"] == up_job["job_id"]), None)
        if job and job["status"] == "success":
            doc_id = job["result"]["document_id"]
            break
        if job and job["status"] == "failed":
            raise SystemExit(f"上传任务失败：{job['error']}")
        time.sleep(1)
    assert doc_id, "上传任务超时"
    up = client.get(f"/api/knowledge/documents/{doc_id}", headers=th).json()
    print("上传元数据:", up["title"], "|", up["topic"], "|", up["chapter"])
    client.delete(f"/api/knowledge/documents/{doc_id}", headers=th)

    # ---------- Demo Mode / P1 新能力冒烟 ----------
    scenarios = client.get("/api/demo/scenarios").json()
    print("Demo 场景:", [s["id"] for s in scenarios])
    demo = client.post("/api/demo/start", json={"scenario_id": "teaching_learning_research"}).json()
    print("Demo 启动:", demo["scenario"]["name"], "| 角色:", demo["current_role"], "| 步骤:", demo["current_step"])
    dh = {"X-Demo-Session": demo["session_id"]}
    diag = client.post("/api/analytics/courses/1/diagnose", headers=dh, json={}).json()
    print("Demo 诊断预置:", len(diag["diagnosis"]["suggestions"]), "条建议")
    step = client.post(
        f"/api/demo/session/{demo['session_id']}/step",
        json={"direction": "next"},
    ).json()
    print("Demo 下一步:", step["current_step"])
    reset = client.post(f"/api/demo/session/{demo['session_id']}/reset", json={}).json()
    print("Demo 重置: state_version =", reset["state_version"])
    client.post(f"/api/demo/session/{demo['session_id']}/exit", json={})

    # 题库管理
    bank = client.get("/api/curriculum/question-bank?course_id=1", headers=th).json()
    print("题库题目数:", len(bank))
    # 知识图谱
    graph = client.get("/api/curriculum/courses/1/graph", headers=sh).json()
    print("知识图谱:", graph["course"]["name"], "| 章节", len(graph["chapters"]), "| 知识点", len(graph["points"]))
    # RAG 使用统计
    stats = client.get("/api/knowledge/stats", headers=th).json()
    print("RAG 统计: 总命中", stats["total_hits"], "| 来源等级", stats["source_levels"])

    print("\n✓ 全部通过")


if __name__ == "__main__":
    main()
