"""提交与批改 Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CodeSubmitIn(BaseModel):
    source_code: str
    language: str = "python"


class SubjectiveSubmitIn(BaseModel):
    content: str


class CodeResult(BaseModel):
    verdict: str
    passed_tests: int = 0
    total_tests: int = 0
    runtime_ms: int = 0
    error_message: str = ""
    judge_report: list = []


class AIReview(BaseModel):
    suggestion_score: float
    reasoning: str
    knowledge_points: list
    errors: str
    improvement: str


class TeacherReviewIn(BaseModel):
    final_score: float
    comment: str = ""


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    question_id: int
    student_id: int
    qtype: str
    status: str
    created_at: datetime
    updated_at: datetime
    student_name: str = ""
    question_title: str = ""
    code: CodeResult | None = None
    subjective: dict | None = None
    score: float | None = None


class GradingWorkItem(BaseModel):
    """教师批改工作台单条数据。"""

    submission_id: int
    assignment_id: int
    assignment_title: str = ""
    question_title: str = ""
    qtype: str
    student_id: int
    student_name: str = ""
    status: str
    submitted_at: datetime
    ai_suggestion_score: float | None = None
    teacher_score: float | None = None
    ai_reviewed: bool = False

