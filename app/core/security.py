from __future__ import annotations

import logging
import re
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,24}$")


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    user_id_num: int
    username: str
    name: str
    email: str
    role: str
    avatar: Optional[str] = None
    phone: Optional[str] = None
    current_role: Optional[str] = None
    location: Optional[str] = None


def normalize_role_for_fe(db_role: Optional[str]) -> str:
    """Convert database role (user, admin, recruiter) to frontend role."""
    if not db_role:
        return "CANDIDATE"
    r = db_role.strip().lower()
    if r == "admin":
        return "ADMIN"
    if r == "recruiter":
        return "RECRUITER"
    return "CANDIDATE"


def normalize_role_for_db(fe_role: Optional[str]) -> str:
    """Convert frontend role to database role."""
    if not fe_role:
        return "user"
    r = fe_role.strip().lower()
    if r == "admin":
        return "admin"
    if r == "recruiter":
        return "recruiter"
    return "user"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token with expiration."""
    to_encode = data.copy()
    expire_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 1440)
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=expire_minutes)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu đăng nhập (thiếu Header Authorization).",
        )
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Định dạng Authorization Bearer token không hợp lệ.",
        )
    return parts[1].strip()


def decode_access_token(token: str) -> dict:
    """Strictly validate JWT signature & expiry. Never accept unsigned mock tokens."""
    if token.startswith("mock-token-"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mock token không còn được hỗ trợ. Vui lòng đăng nhập lại.",
        )
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("Invalid JWT token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token xác thực không hợp lệ.",
        ) from exc


def _db_user_to_authenticated_user(user: User) -> AuthenticatedUser:
    email = (user.email or "").strip()
    username = email.split("@")[0] if "@" in email else (user.name or f"user{user.user_id}")
    return AuthenticatedUser(
        id=f"user-{user.user_id:03d}",
        user_id_num=user.user_id,
        username=username,
        name=user.name or username,
        email=email,
        role=normalize_role_for_fe(user.role),
        avatar=user.avatar,
        phone=user.phone,
        current_role=user.current_role,
        location=user.location,
    )


def get_current_user_dep(
    authorization: Optional[str] = Header(None),
    db: Optional[Session] = Depends(get_db),
) -> AuthenticatedUser:
    """Authenticate caller from Bearer JWT and load latest user profile from DB."""
    token = extract_bearer_token(authorization)
    payload = decode_access_token(token)

    user_id_str = str(payload.get("sub") or "").strip()
    email = (payload.get("email") or "").strip()

    if db is not None:
        db_user = None
        try:
            if email:
                db_user = (
                    db.query(User)
                    .filter(func.lower(User.email) == email.lower())
                    .first()
                )
            if not db_user and user_id_str.isdigit() and int(user_id_str) > 0:
                db_user = (
                    db.query(User)
                    .filter(User.user_id == int(user_id_str))
                    .first()
                )
        except Exception as exc:
            logger.warning("DB lookup during token auth failed: %s", exc)
            db_user = None
        if db_user:
            return _db_user_to_authenticated_user(db_user)

    if email or user_id_str:
        num = int(user_id_str) if user_id_str.isdigit() else 0
        return AuthenticatedUser(
            id=str(payload.get("id") or f"user-{num:03d}"),
            user_id_num=num,
            username=(email.split("@")[0] if "@" in email else str(payload.get("username") or "user")),
            name=str(payload.get("name") or "Người dùng"),
            email=email,
            role=normalize_role_for_fe(payload.get("role")),
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không chứa thông tin người dùng hợp lệ.",
    )


def require_roles(*allowed_roles: str) -> Callable:
    allowed = {r.upper() for r in allowed_roles}

    def _dependency(
        current_user: AuthenticatedUser = Depends(get_current_user_dep),
    ) -> AuthenticatedUser:
        if current_user.role.upper() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác này.",
            )
        return current_user

    return _dependency


def verify_internal_service_key(provided: Optional[str]) -> bool:
    expected = (settings.INTERNAL_SERVICE_SECRET or "").strip()
    if not expected or not provided:
        return False
    return secrets.compare_digest(provided.strip(), expected)


def require_user_or_internal_service(
    authorization: Optional[str] = Header(None),
    x_internal_service_key: Optional[str] = Header(None, alias="X-Internal-Service-Key"),
    db: Optional[Session] = Depends(get_db),
) -> Optional[AuthenticatedUser]:
    """Allow either a trusted internal service (prep-hire-ai) or an authenticated user."""
    if verify_internal_service_key(x_internal_service_key):
        return None
    return get_current_user_dep(authorization=authorization, db=db)


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter."""

    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        if limit <= 0:
            return True, 0
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            dq = self._buckets.setdefault(key, deque())
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if len(dq) >= limit:
                retry_after = max(1, int(window_seconds - (now - dq[0])))
                return False, retry_after
            dq.append(now)
            return True, 0


rate_limiter = SlidingWindowRateLimiter()


def rate_limit(bucket: str, max_requests: int, window_seconds: int = 60) -> Callable:
    def _dep(request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        client_host = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        ip = forwarded or client_host
        allowed, retry_after = rate_limiter.check(
            f"{bucket}:{ip}",
            limit=max_requests,
            window_seconds=window_seconds,
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Quá nhiều yêu cầu. Vui lòng thử lại sau giây lát.",
                headers={"Retry-After": str(retry_after)},
            )

    return _dep

