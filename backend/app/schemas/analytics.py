"""学情分析 Schema。"""

from pydantic import BaseModel


class KnowledgeAccuracy(BaseModel):
    knowledge_point_id: int
    name: str
    subject: str = ""
    attempts: int = 0
    correct: int = 0
    accuracy: float = 0.0


class ClassAnalytics(BaseModel):
    course_id: int
    course_name: str = ""
    total_students: int = 0
    submission_count: int = 0
    graded_count: int = 0
    avg_accuracy: float = 0.0
    knowledge_accuracy: list[KnowledgeAccuracy] = []
    high_frequency_errors: list[dict] = []
    ability_distribution: list[dict] = []
    weak_points: list[str] = []

