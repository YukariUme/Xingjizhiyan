"""端到端：PG 后端 + CodeCrucible 本地判题（教师建 IO 题 → 学生提交 → AC）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def _login(client: TestClient, role: str) -> tuple[dict, dict]:
    r = client.get(f"/api/auth/demo/{role}")
    assert r.status_code == 200, r.text
    data = r.json()
    return data, {"Authorization": f"Bearer {data['token']}"}


def main() -> None:
    with TestClient(app) as client:
        teacher, t_headers = _login(client, "teacher")
        courses = client.get("/api/courses", headers=t_headers).json()
        course = next((c for c in courses if c["name"] == "数据结构"), courses[0])
        print("course:", course["name"], course["id"])

        # 教师创建作业：一道标准输入输出编程题
        created = client.post(
            "/api/assignments",
            headers=t_headers,
            json={
                "title": "E2E 测试 · 两数之和",
                "description": "输入两个整数，输出它们的和。",
                "course_id": course["id"],
                "due_at": "2027-01-01T00:00:00Z",
                "questions": [
                    {
                        "qtype": "programming",
                        "title": "两数之和",
                        "description": "读取 a b，输出 a+b。",
                        "language": "python",
                        "code_template": "# 请输入代码",
                        "max_score": 10,
                        "knowledge_point_ids": [],
                        "test_cases": [
                            {"id": 1, "name": "样例1", "mode": "io", "input": "1 2\n", "output": "3\n"},
                            {"id": 2, "name": "样例2", "mode": "io", "input": "10 -4\n", "output": "6\n"},
                        ],
                    }
                ],
            },
        )
        assert created.status_code == 200, created.text
        assignment = created.json()
        qid = assignment["questions"][0]["id"]
        print("assignment:", assignment["id"], "question:", qid)

        # 学生提交正确代码
        student, s_headers = _login(client, "student")
        submit = client.post(
            f"/api/assignments/{assignment['id']}/questions/{qid}/submit",
            headers=s_headers,
            json={
                "source_code": "a, b = map(int, input().split())\nprint(a + b)\n",
                "language": "python",
            },
        )
        assert submit.status_code == 200, submit.text
        result = submit.json()
        print("verdict:", result.get("verdict"), "| passed:", result.get("passed_tests"), "/", result.get("total_tests"))
        assert result.get("verdict") == "accepted", result
        assert result.get("passed_tests") == 2

        # 学生提交错误代码 → WA
        submit2 = client.post(
            f"/api/assignments/{assignment['id']}/questions/{qid}/submit",
            headers=s_headers,
            json={"source_code": "print('hello')\n", "language": "python"},
        )
        assert submit2.status_code == 200, submit2.text
        result2 = submit2.json()
        print("verdict2:", result2.get("verdict"))
        assert result2.get("verdict") == "wrong_answer"

        print("E2E OK")


if __name__ == "__main__":
    main()
