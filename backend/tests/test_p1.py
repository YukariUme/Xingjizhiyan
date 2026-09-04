"""P1 能力测试：知识图谱、RAG 统计、题库管理、错题本与冲刺计划。"""

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models import Course
from app.services.rag.sqlite import SQLiteRAGService


def _os_course_id() -> int:
    db = SessionLocal()
    try:
        return db.query(Course).filter(Course.name == "操作系统").first().id
    finally:
        db.close()


def test_knowledge_graph(client: TestClient, student):
    cid = _os_course_id()
    headers = {"Authorization": f"Bearer {student['token']}"}
    resp = client.get(f"/api/curriculum/courses/{cid}/graph", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["course"]["name"] == "操作系统"
    assert len(body["chapters"]) >= 3
    assert len(body["points"]) >= 3
    assert all("chapter_id" in p for p in body["points"])


def test_rag_stats_and_hit_count(client: TestClient, teacher):
    """RAG 命中后知识库统计的命中次数递增。"""
    headers = {"Authorization": f"Bearer {teacher['token']}"}
    db = SessionLocal()
    try:
        rag = SQLiteRAGService()
        before = rag.retrieve_context(db, "什么是动态规划", top_k=3)
        assert before["grounded"] is True
    finally:
        db.close()
    resp = client.get("/api/knowledge/stats", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_hits"] >= 1
    assert body["source_levels"]
    assert any(d["hits"] > 0 for d in body["top_documents"])


def test_question_bank_crud(client: TestClient, teacher):
    cid = _os_course_id()
    headers = {"Authorization": f"Bearer {teacher['token']}"}
    created = client.post(
        "/api/curriculum/question-bank",
        headers=headers,
        json={
            "course_id": cid,
            "qtype": "multiple",
            "title": "以下哪些是进程同步机制？（多选）",
            "options": ["信号量", "互斥锁", "管程", "文件系统"],
            "answer": {"indexes": [0, 1, 2]},
            "analysis": "信号量/互斥锁/管程均为同步机制。",
            "knowledge_point_ids": [],
            "max_score": 5,
        },
    )
    assert created.status_code == 200, created.text
    qid = created.json()["id"]
    listing = client.get(f"/api/curriculum/question-bank?course_id={cid}", headers=headers)
    assert any(q["id"] == qid for q in listing.json())
    updated = client.put(
        f"/api/curriculum/question-bank/{qid}",
        headers=headers,
        json={"title": "更新后的多选题目"},
    )
    assert updated.status_code == 200
    deleted = client.delete(f"/api/curriculum/question-bank/{qid}", headers=headers)
    assert deleted.status_code == 200


def test_wrongbook_and_sprint(client: TestClient, student):
    headers = {"Authorization": f"Bearer {student['token']}"}
    wb = client.get("/api/curriculum/wrongbook", headers=headers)
    assert wb.status_code == 200
    assert "by_knowledge_point" in wb.json()
    sp = client.get("/api/curriculum/sprint?exam_date=2026-12-30", headers=headers)
    assert sp.status_code == 200
    assert sp.json()["days_left"] is not None
    assert "plan" in sp.json()
