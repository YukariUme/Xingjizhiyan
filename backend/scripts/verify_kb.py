"""知识库管理自检：分类树合并新课程、类型/课程筛选、时间/大小排序、搜索。"""

import httpx

BASE = "http://127.0.0.1:8000"


def main() -> None:
    client = httpx.Client(base_url=BASE, timeout=90)
    teacher = client.post(
        "/api/auth/login", json={"username": "teacher1", "password": "123456"}
    ).json()
    th = {"Authorization": f"Bearer {teacher['token']}"}

    # 1) 新建课程后，学科分类树应包含该课程（即使 0 文档）
    course = client.post(
        "/api/courses",
        headers=th,
        json={"name": "计算机组成原理", "code": "CS250", "semester": "2026 秋季"},
    ).json()
    subjects = client.get("/api/knowledge/subjects", headers=th).json()
    names = [s["course"] for s in subjects]
    print("学科分类树包含新课程:", "计算机组成原理" in names, "|", len(subjects), "门课程")

    # 2) 筛选与排序
    docs = client.get(
        "/api/knowledge/documents",
        headers=th,
        params={"course": "数据结构", "sort": "size", "order": "desc"},
    ).json()
    print("按大小倒序前 3:", [(d["title"][:16], d["size_chars"], d["chunk_count"]) for d in docs[:3]])

    docs2 = client.get(
        "/api/knowledge/documents",
        headers=th,
        params={"type": "教材", "sort": "time", "order": "asc"},
    ).json()
    print("教材类型按时间正序:", len(docs2), "篇 | 第一篇:", docs2[0]["title"][:16] if docs2 else None)

    docs3 = client.get(
        "/api/knowledge/documents", headers=th, params={"q": "动态规划"}
    ).json()
    print("搜索「动态规划」:", len(docs3), "篇 |", [d["title"][:14] for d in docs3[:3]])

    client.delete(f"/api/courses/{course['id']}", headers=th)
    print("已清理测试课程 ✓")


if __name__ == "__main__":
    main()

