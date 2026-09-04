"""用户相关 Schema。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: str
    identity: str = "student"
    modes: list = []
    title: str = ""
    bio: str = ""


class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    user: UserOut


class RegisterIn(BaseModel):
    username: str
    password: str
    display_name: str
    identity: Literal["teacher", "undergraduate", "graduate"] = "undergraduate"
