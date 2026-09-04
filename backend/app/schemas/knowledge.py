"""知识库 Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KnowledgePointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    subject: str
    chapter: str = ""
    difficulty: str = "中"
    description: str = ""
    prerequisites: list = []


class KnowledgeDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source: str = ""
    course: str
    topic: str = ""
    chapter: str = ""
    difficulty: str = "中"
    type: str = "讲义"
    year: int = 2026
    content: str = ""
    course_id: int | None = None
    source_level: str = "S"
    visibility: str = "official"
    owner_id: int | None = None
    page: str = ""
    document_type: str = "讲义"
    size_chars: int = 0
    chunk_count: int = 0
    created_at: datetime | None = None


class KnowledgeChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    chunk_index: int
    text: str
    metadata_json: dict = {}


class SearchResult(BaseModel):
    chunk: KnowledgeChunkOut
    document: KnowledgeDocumentOut
    score: float = 0.0
