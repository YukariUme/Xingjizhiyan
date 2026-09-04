"""活动 Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    role: str
    kind: str
    title: str
    detail: dict = {}
    created_at: datetime

