"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    activities,
    ai,
    analytics,
    assignments,
    auth,
    courses,
    course_invitations,
    curriculum,
    demo,
    grading,
    knowledge,
    learning,
    playground,
    planning,
    research,
    roundtable,
    session,
    submissions,
    workflows,
)
from app.api.demo_middleware import demo_middleware
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.seed import seed_if_empty
from app.services.curriculum_sync import sync_curriculum
from app.services.llm.base import LLMError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时建表并在演示模式填充种子数据。"""
    init_db()
    if get_settings().demo_mode:
        db = SessionLocal()
        try:
            seed_if_empty(db)
            sync_curriculum(db)
        finally:
            db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="面向高校计算机学科的教学研一体化智能平台 API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Demo 预置响应：带 X-Demo-Session 的关键 AI 端点返回稳定结果
    app.middleware("http")(demo_middleware)

    @app.exception_handler(LLMError)
    async def llm_error_handler(_request: Request, exc: LLMError):
        """AI 模块异常统一返回 503 + 可读信息（例如 DeepSeek 未配置 Key）。"""
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "app": settings.app_name,
            "providers": {
                "llm": settings.llm_provider,
                "rag": settings.rag_provider,
                "judge": settings.judge_provider,
            },
        }

    for router in (
        auth.router,
        courses.router,
        course_invitations.router,
        curriculum.router,
        assignments.router,
        submissions.router,
        grading.router,
        analytics.router,
        learning.router,
        playground.router,
        planning.router,
        demo.router,
        research.router,
        roundtable.router,
        knowledge.router,
        ai.router,
        activities.router,
        session.router,
        workflows.router,
    ):
        app.include_router(router)
    return app


app = create_app()
