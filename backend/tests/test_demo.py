"""Demo Mode 测试：场景、会话、角色切换、重置、预置响应与数据隔离。"""

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models import Course, StudentKnowledgeProfile, User
from app.models.demo import DemoScenario, DemoSession
from app.services.demo.service import ensure_scenarios, reset_demo, set_role, start_demo


def test_demo_scenarios_and_start():
    """场景落库 + 启动会话返回完整状态。"""
    db = SessionLocal()
    try:
        ensure_scenarios(db)
        assert db.query(DemoScenario).count() >= 3
        session = start_demo(db, "teaching_learning_research")
        assert session["current_role"] == "teacher"
        assert session["current_step"]
        assert len(session["scenario"]["steps"]) >= 5
        assert session["demo_mode"] is True
    finally:
        db.close()


def test_demo_role_switch_and_reset():
    """角色切换与一键重置：state_version 递增、步骤回到第一步。"""
    db = SessionLocal()
    try:
        session = start_demo(db, "teaching_learning_research")
        sid = session["session_id"]
        switched = set_role(db, sid, "student")
        assert switched["current_role"] == "student"
        assert switched["role_user"]["display_name"] == "李明"
        reset = reset_demo(db, sid)
        assert reset["state_version"] > session["state_version"]
        assert reset["current_role"] == "teacher"
    finally:
        db.close()


def test_demo_preset_middleware(client: TestClient):
    """带 X-Demo-Session 的关键 AI 端点返回预置结果（不依赖真实 LLM）。"""
    db = SessionLocal()
    try:
        session = start_demo(db, "teaching_learning_research")
    finally:
        db.close()
    headers = {"X-Demo-Session": session["session_id"]}
    # 教学诊断
    resp = client.post("/api/analytics/courses/1/diagnose", headers=headers, json={})
    assert resp.status_code == 200
    assert resp.json()["diagnosis"]["suggestions"]
    # 课程答疑
    resp = client.post(
        "/api/ai/assistant",
        headers=headers,
        json={"agent": "learning", "payload": {"message": "为什么生产者和消费者都需要使用信号量？"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "empty" in body["answer"]
    assert body["grounded"] is True
    # 论文分析
    resp = client.post("/api/research/papers/1/analyze", headers=headers, json={})
    assert resp.status_code == 200
    assert resp.json()["experiments"]


def test_demo_reset_isolates_real_data():
    """重置只影响 Demo 账户：真实学生数据不受影响，Demo 初始画像被重建。"""
    db = SessionLocal()
    try:
        real_student = db.query(User).filter(User.username == "student1").first()
        real_profile_count = (
            db.query(StudentKnowledgeProfile)
            .filter(StudentKnowledgeProfile.student_id == real_student.id)
            .count()
            if real_student
            else -1
        )
        start_demo(db, "teaching_learning_research")
        demo_student = db.query(User).filter(User.username == "demo_student").first()
        demo_profiles = (
            db.query(StudentKnowledgeProfile)
            .filter(StudentKnowledgeProfile.student_id == demo_student.id)
            .all()
        )
        assert len(demo_profiles) >= 3
        if real_student:
            after = (
                db.query(StudentKnowledgeProfile)
                .filter(StudentKnowledgeProfile.student_id == real_student.id)
                .count()
            )
            assert after == real_profile_count
        # 清理会话，避免影响其他测试
        db.query(DemoSession).delete()
        db.commit()
    finally:
        db.close()
