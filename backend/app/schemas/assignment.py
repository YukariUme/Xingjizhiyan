"""作业 Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    qtype: str
    title: str
    description: str = ""
    language: str = "python"
    code_template: str = ""
    test_cases: list = []
    max_score: float = 10.0
    knowledge_point_ids: list = []


class QuestionIn(BaseModel):
    qtype: str
    title: str
    description: str = ""
    language: str = "python"
    code_template: str = ""
    test_cases: list = []
    max_score: float = 10.0
    knowledge_point_ids: list = []


class AssignmentIn(BaseModel):
    title: str
    description: str = ""
    course_id: int
    due_at: datetime
    questions: list[QuestionIn] = []


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str = ""
    course_id: int
    teacher_id: int
    due_at: datetime
    status: str = "published"
    created_at: datetime
    questions: list[QuestionOut] = []
    course_name: str = ""
    submitted_count: int = 0
    student_count: int = 0

