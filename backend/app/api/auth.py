"""认证路由：登录、演示账号切换、当前用户。"""

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import create_token, get_current_user, require_roles
from app.database import get_db
from app.models import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import LoginIn, LoginOut, RegisterIn, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(username: str, password: str) -> str:
    return hashlib.sha256(f"{username}:{password}".encode()).hexdigest()


@router.post("/login", response_model=LoginOut)
def login(data: LoginIn, db: Session = Depends(get_db)) -> LoginOut:
    user = UserRepository.get_by_username(db, data.username)
    if not user or user.password_hash != hash_password(data.username, data.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return LoginOut(token=create_token(user.id), user=UserOut.model_validate(user))


@router.post("/register", response_model=LoginOut)
def register(data: RegisterIn, db: Session = Depends(get_db)) -> LoginOut:
    """注册新账号（身份：教师/本科生/研究生），注册后自动登录。"""
    username = data.username.strip()
    display_name = data.display_name.strip()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少 3 个字符")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    if not display_name:
        raise HTTPException(status_code=400, detail="请填写姓名")
    if UserRepository.get_by_username(db, username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    identity = data.identity
    role = "teacher" if identity == "teacher" else "student"
    modes = (
        ["teaching", "learning", "research"]
        if identity == "teacher"
        else ["learning", "research"]
    )
    user = User(
        username=username,
        display_name=display_name,
        password_hash=hash_password(username, data.password),
        role=role,
        identity=identity,
        modes=modes,
        title="",
        bio="",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return LoginOut(token=create_token(user.id), user=UserOut.model_validate(user))


@router.get("/demo/{role}", response_model=LoginOut)
def demo_login(role: str, db: Session = Depends(get_db)) -> LoginOut:
    """一键切换演示角色：teacher / student / researcher。"""
    user = db.query(User).filter(User.role == role).order_by(User.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="演示账号不存在")
    return LoginOut(token=create_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/students", response_model=list[UserOut])
def list_students(
    q: str = "",
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    """列出全部注册学生（供教师邀请进课程），支持按用户名/姓名搜索。"""
    students = UserRepository.list_by_role(db, "student")
    kw = q.strip().lower()
    if kw:
        students = [
            s
            for s in students
            if kw in s.username.lower() or kw in s.display_name.lower()
        ]
    return [UserOut.model_validate(s) for s in students]
