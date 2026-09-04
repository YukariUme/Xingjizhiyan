"""课程与备课 Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: str = ""
    semester: str = ""
    teacher_id: int
    created_at: datetime
    student_count: int = 0
    assignment_count: int = 0
    pending_count: int = 0


class CourseIn(BaseModel):
    name: str
    code: str
    description: str = ""
    semester: str = "2026 春季"


class CourseInvitationOut(BaseModel):
    id: int
    course_id: int
    course_name: str = ""
    course_code: str = ""
    semester: str = ""
    teacher_name: str = ""
    student_id: int
    student_name: str = ""
    student_username: str = ""
    status: str = "pending"
    created_at: datetime


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    student_id: int


class LessonPlanIn(BaseModel):
    course: str
    chapter: str
    topic: str
    grade: str = ""
    objective: str = ""


class LessonPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    course: str
    chapter: str
    topic: str
    grade: str = ""
    objectives: str = ""
    knowledge_points: list = []
    key_points: list = []
    difficulties: list = []
    flow: list = []
    cases: list = []
    exercises: list = []
    homework: list = []
    created_at: datetime
