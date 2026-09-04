"""认证与 RBAC 依赖。

演示环境使用 HMAC 签名 Token（/api/auth/login 与 /api/auth/demo 签发），
业务接口通过 get_current_user / require_roles 强制角色与数据范围校验。
"""

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.repositories.user_repo import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64url(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_token(user_id: int) -> str:
    """签发演示 Token（HMAC-SHA256 签名，7 天有效）。"""
    settings = get_settings()
    payload = {
        "uid": user_id,
        "exp": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    }
    body = _b64url(json.dumps(payload).encode())
    sig = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64url(sig)}"


def decode_token(token: str) -> int | None:
    """校验并解析 Token，返回用户 ID。"""
    try:
        body, sig = token.split(".")
        settings = get_settings()
        expected = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64url(sig)):
            return None
        payload = json.loads(_unb64url(body))
        exp = datetime.fromisoformat(payload["exp"])
        if datetime.now(timezone.utc) > exp:
            return None
        return int(payload["uid"])
    except Exception:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """解析当前登录用户，失败返回 401。"""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    user_id = decode_token(credentials.credentials)
    user = UserRepository.get_by_id(db, user_id) if user_id else None
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    return user


def require_roles(*roles: str):
    """角色校验依赖工厂。"""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限执行此操作")
        return user

    return checker

