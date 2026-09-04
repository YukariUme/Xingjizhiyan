"""学习画像、推荐与对话 Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KnowledgeMastery(BaseModel):
    knowledge_point_id: int
    knowledge_point: str = ""
    subject: str = ""
    mastery: float = 0.0
    attempts: int = 0
    errors: int = 0
    level: str = "未掌握"


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    knowledge_point_id: int | None = None
    knowledge_point: str = ""
    reason: str = ""
    resource_title: str
    resource_type: str
    resource_ref: dict = {}
    priority: int = 5
    created_at: datetime


class TutorChatIn(BaseModel):
    message: str
    mode: str = "hint"  # hint | detail
    history: list[dict] = []


class TutorReply(BaseModel):
    answer: str
    mode: str
    knowledge_points: list = []
    references: list = []
    conversation_id: int | None = None


class DiagnosisIn(BaseModel):
    question_title: str = ""
    question_description: str = ""
    source_code: str = ""
    language: str = "python"
    judge_report: list = []
    error_message: str = ""
    mode: str = "hint"


class DiagnosisOut(BaseModel):
    error_reason: str
    knowledge_points: list
    thinking: list
    advice: list
    suggestion: str = ""

