"""Demo Mode 实体：演示场景与会话状态。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DemoScenario(Base):
    """预置演示场景定义（课程、Demo 用户、步骤与初始状态）。"""

    __tablename__ = "demo_scenarios"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    initial_role: Mapped[str] = mapped_column(String(16), default="teacher")
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id"), nullable=True, index=True
    )
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    research_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    demo_step: Mapped[int] = mapped_column(Integer, default=0)
    steps: Mapped[list] = mapped_column(JSON, default=list)  # [{id,label,path}]
    initial_state: Mapped[dict] = mapped_column(JSON, default=dict)
    seed_data_version: Mapped[str] = mapped_column(String(32), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DemoSession(Base):
    """一次演示运行：当前步骤 / 角色 / 状态版本（按 scenario 隔离）。"""

    __tablename__ = "demo_sessions"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(
        ForeignKey("demo_scenarios.id"), index=True
    )
    current_step: Mapped[str] = mapped_column(String(48), default="")
    current_role: Mapped[str] = mapped_column(String(16), default="teacher")
    state_version: Mapped[int] = mapped_column(Integer, default=1)
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
