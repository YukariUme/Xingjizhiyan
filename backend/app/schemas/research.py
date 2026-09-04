"""科研模块 Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PaperOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    authors: list = []
    abstract: str = ""
    venue: str = ""
    year: int
    topics: list = []
    keywords: list = []
    citations: int = 0
    url: str = ""
    is_hot: bool = False
    status: str = ""  # reading | read | favorite


class PaperAnalysis(BaseModel):
    paper_id: int
    title: str = ""
    summary: str = ""
    research_question: str = ""
    method: str = ""
    experiments: str = ""
    conclusion: str = ""
    limitations: str = ""
    future: str = ""
    references: list = []
    knowledge_points: list = []


class ResearchTopicIn(BaseModel):
    name: str
    description: str = ""


class ResearchTopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    description: str = ""
    created_at: datetime


class FrontierIn(BaseModel):
    topic: str


class FrontierOut(BaseModel):
    topic: str
    directions: list = []
    papers: list = []
    hot_topics: list = []
    methods: list = []
    trend: list = []
    references: list = []

