"""Demo 预置响应中间件：带 X-Demo-Session 的关键 AI 端点返回预置结果。"""

import json
import re

from fastapi import Request
from fastapi.responses import JSONResponse

from app.database import SessionLocal
from app.services.demo.definitions import (
    preset_code_diagnosis,
    preset_diagnosis,
    preset_lecture,
    preset_paper_analysis,
    preset_teaching,
    preset_tutor,
)
from app.services.demo.service import get_session


def _match(path: str, pattern: str) -> bool:
    return re.fullmatch(pattern, path) is not None


def _preset_for(session_id: str, path: str, body: dict) -> dict | None:
    """按请求路径返回预置响应；未命中返回 None（走真实逻辑）。"""
    db = SessionLocal()
    try:
        if not get_session(db, session_id):
            return None
    finally:
        db.close()

    if _match(path, r"/api/analytics/courses/\d+/diagnose"):
        return preset_diagnosis()
    if _match(path, r"/api/curriculum/chapters/\d+/lecture"):
        return preset_lecture()
    if path == "/api/learning/diagnose":
        return preset_code_diagnosis()
    if path == "/api/ai/assistant" and body.get("agent") == "learning":
        payload = body.get("payload") or {}
        mode = payload.get("mode") or ""
        primary_ids = payload.get("primary_document_ids") or []
        if payload.get("teaching") or mode in ("teaching", "quick", "deep") or primary_ids:
            title = ""
            if primary_ids:
                from app.models import KnowledgeDocument

                doc = db.query(KnowledgeDocument).filter(
                    KnowledgeDocument.id == int(primary_ids[0])
                ).first()
                title = doc.title if doc else ""
            return preset_teaching(title, quick=(mode == "quick"), hint=(mode == "hint"))
        return preset_tutor()
    if _match(path, r"/api/research/papers/\d+/analyze"):
        return preset_paper_analysis()
    return None


async def demo_middleware(request: Request, call_next):
    """拦截 Demo 会话的关键 AI 端点，返回预置 JSON（保证现场演示稳定）。"""
    session_id = request.headers.get("X-Demo-Session")
    if session_id and request.method == "POST":
        try:
            raw = await request.body()
            body = json.loads(raw) if raw else {}
        except Exception:  # noqa: BLE001
            body = {}
        preset = _preset_for(session_id, request.url.path, body)
        if preset is not None:
            return JSONResponse(preset)
        # 恢复 body 供后续路由读取
        request._body = raw  # type: ignore[attr-defined]
    return await call_next(request)
