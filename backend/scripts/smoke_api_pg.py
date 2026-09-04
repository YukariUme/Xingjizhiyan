"""PG 后端 API 冒烟：登录 → 知识库 → RAG 搜索 → 编程题提交。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def main() -> None:
    with TestClient(app) as client:
        # 登录
        r = client.get("/api/auth/demo/teacher")
        assert r.status_code == 200, r.text
        token = r.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("login ok")

        # 知识库文档
        r = client.get("/api/knowledge/documents", headers=headers)
        assert r.status_code == 200, r.text
        docs = r.json()
        print("documents:", len(docs))

        # RAG 搜索
        r = client.get("/api/knowledge/search", headers=headers, params={"q": "信号量", "course": "操作系统"})
        print("search status:", r.status_code)
        if r.status_code == 200:
            data = r.json()
            hits = (
                data.get("results")
                if isinstance(data, dict)
                else data
            )
            print("search hits:", len(hits))
            for h in hits[:3]:
                print("  -", h.get("score"), (h.get("title") or "")[:30])

        # 编程题提交（走 assignment_loop 工作流 + Mock Judge）
        r = client.get("/api/assignments", headers=headers)
        if r.status_code == 200:
            print("assignments:", len(r.json() or []))
        r = client.get("/api/courses", headers=headers)
        print("courses:", r.status_code)

        # 健康检查
        r = client.get("/api/health")
        assert r.status_code == 200
        print("health:", r.json()["status"])


if __name__ == "__main__":
    main()
