"""Demo Mode 路由：场景选择、会话、步骤、角色切换、重置与退出。"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import create_token
from app.database import get_db
from app.models.demo import DemoScenario, DemoSession
from app.services.demo.definitions import SCENARIOS
from app.services.demo.service import (
    demo_user_for_role,
    ensure_scenarios,
    exit_demo,
    get_session,
    reset_demo,
    set_role,
    set_step,
    start_demo,
)

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/scenarios")
def list_scenarios(db: Session = Depends(get_db)) -> list[dict]:
    """返回预置演示场景（含步骤与说明）。"""
    ensure_scenarios(db)  # 同步最新步骤定义（新增/修改步骤后立即生效）
    rows = db.query(DemoScenario).order_by(DemoScenario.created_at).all()
    if rows:
        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "course": r.course_id,
                "steps": r.steps,
            }
            for r in rows
        ]
    return SCENARIOS


@router.post("/start")
def start(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    """启动演示：{scenario_id}，重置 Demo 数据并返回会话。"""
    scenario_id = data.get("scenario_id")
    try:
        return start_demo(db, scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/session/{session_id}")
def session_status(
    session_id: str,
    db: Session = Depends(get_db),
) -> dict:
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="演示会话不存在")
    from app.services.demo.service import session_out

    return session_out(db, session)


@router.post("/session/{session_id}/step")
def step(
    session_id: str,
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    """前进/后退/指定步骤：{direction: next|prev, step_id?}。"""
    try:
        return set_step(
            db,
            session_id,
            data.get("step_id"),
            data.get("direction", "next"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/session/{session_id}/role")
def switch_role(
    session_id: str,
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    """切换演示角色：{role: teacher|student|researcher}。"""
    try:
        return set_role(db, session_id, data.get("role", "teacher"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/session/{session_id}/reset")
def reset_session(
    session_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """一键重置：恢复 Demo 初始状态。"""
    try:
        return reset_demo(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/session/{session_id}/exit")
def exit_session(
    session_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """退出演示：删除会话，前端恢复真实登录态。"""
    exit_demo(db, session_id)
    return {"ok": True}


@router.post("/login")
def demo_login(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    """以 Demo 角色登录：{role: teacher|student|researcher}。"""
    role = data.get("role", "teacher")
    user = demo_user_for_role(db, role)
    if not user:
        raise HTTPException(status_code=404, detail="Demo 账号不存在")
    return {
        "token": create_token(user.id),
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "identity": user.identity,
            "modes": user.modes or ["learning", "research"],
            "title": user.title,
        },
    }
