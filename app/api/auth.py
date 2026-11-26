from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    EMAIL_REGEX,
    AuthenticatedUser,
    create_access_token,
    get_current_user_dep,
    normalize_role_for_db,
    normalize_role_for_fe,
    rate_limit,
    require_roles,
)
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# ============================================================================
# Schemas
# ============================================================================


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    # Note: Public registration NEVER trusts client-supplied roles.


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    current_role: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


class AdminRoleUpdateRequest(BaseModel):
    role: str = Field(..., description="CANDIDATE | RECRUITER | ADMIN")


class AdminCreateUserRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field(..., min_length=1, max_length=120)
    role: str = Field(default="CANDIDATE")


class UserInfo(BaseModel):
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
    created_at: Optional[datetime] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class AdminUserListResponse(BaseModel):
    total: int
    users: list[UserInfo]


# ============================================================================
# Helpers
# ============================================================================


def _db_user_to_user_info(user: User) -> UserInfo:
    email = (user.email or "").strip()
    username = email.split("@")[0] if "@" in email else (user.name or f"user{user.user_id}")
    return UserInfo(
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
        created_at=getattr(user, "created_at", None),
    )


def _auth_user_to_user_info(auth_user: AuthenticatedUser) -> UserInfo:
    return UserInfo(
        id=auth_user.id,
        user_id_num=auth_user.user_id_num,
        username=auth_user.username,
        name=auth_user.name,
        email=auth_user.email,
        role=auth_user.role,
        avatar=auth_user.avatar,
        phone=auth_user.phone,
        current_role=auth_user.current_role,
        location=auth_user.location,
    )


def _issue_login_response(user_info: UserInfo) -> LoginResponse:
    token_payload = {
        "sub": str(user_info.user_id_num),
        "id": user_info.id,
        "user_id_num": user_info.user_id_num,
        "email": user_info.email,
        "role": user_info.role,
        "name": user_info.name,
    }
    return LoginResponse(
        access_token=create_access_token(token_payload),
        token_type="bearer",
        user=user_info,
    )


# ============================================================================
# Auth Endpoints
# ============================================================================


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("auth_register", settings.RATE_LIMIT_AUTH_PER_MIN))],
)
def register(payload: RegisterRequest, db: Optional[Session] = Depends(get_db)):
    """Đăng ký tài khoản ứng viên mới (luôn gán quyền CANDIDATE)."""
    email_clean = payload.email.strip().lower()
    if not EMAIL_REGEX.match(email_clean):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Địa chỉ email không đúng định dạng.",
        )

    if len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu phải có ít nhất 6 ký tự.",
        )

    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể kết nối đến cơ sở dữ liệu.",
        )

    try:
        existing_user = (
            db.query(User).filter(func.lower(User.email) == email_clean).first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email này đã được đăng ký. Vui lòng đăng nhập hoặc sử dụng email khác.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("DB query failed during register: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi kết nối cơ sở dữ liệu khi kiểm tra tài khoản.",
        ) from exc

    display_name = (payload.name or "").strip()
    if not display_name:
        display_name = email_clean.split("@")[0].replace(".", " ").capitalize()

    hashed_password = bcrypt.hashpw(
        payload.password.encode("utf-8"),
        bcrypt.gensalt(rounds=10),
    ).decode("utf-8")

    # Security: Public self-registration ALWAYS creates a standard CANDIDATE ("user")
    db_role = "user"

    try:
        new_user = User(
            email=email_clean,
            password=hashed_password,
            name=display_name,
            role=db_role,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user_info = _db_user_to_user_info(new_user)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to create new user: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tạo tài khoản người dùng.",
        ) from exc

    return _issue_login_response(user_info)


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(rate_limit("auth_login", settings.RATE_LIMIT_AUTH_PER_MIN))],
)
def login(payload: LoginRequest, db: Optional[Session] = Depends(get_db)):
    """Đăng nhập hệ thống bằng JWT."""
    raw_identifier = payload.username.strip()
    identifier_lower = raw_identifier.lower()
    plain_password = payload.password

    if db is not None:
        try:
            candidate_emails = [identifier_lower]
            if "@" not in identifier_lower:
                candidate_emails.append(f"{identifier_lower}@prephire.vn")
            db_user = (
                db.query(User)
                .filter(
                    (func.lower(User.email).in_(candidate_emails))
                    | (func.lower(User.name) == identifier_lower)
                )
                .first()
            )
            if db_user:
                if not db_user.password:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Tài khoản này chưa thiết lập mật khẩu (đăng nhập bằng Google).",
                    )
                try:
                    password_matches = bcrypt.checkpw(
                        plain_password.encode("utf-8"),
                        db_user.password.encode("utf-8"),
                    )
                except Exception as exc:
                    logger.warning("bcrypt check failed: %s", exc)
                    password_matches = False

                if not password_matches:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Mật khẩu không chính xác.",
                    )
                return _issue_login_response(_db_user_to_user_info(db_user))
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("DB query failed during login: %s", exc)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tên đăng nhập hoặc mật khẩu không chính xác.",
    )


@router.get("/me", response_model=UserInfo)
def get_current_user(
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
):
    """Lấy thông tin người dùng hiện tại từ JWT Bearer token hợp lệ."""
    return _auth_user_to_user_info(current_user)


@router.get("/profile", response_model=UserInfo)
def get_profile(
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
):
    """Lấy thông tin hồ sơ người dùng hiện tại (alias của /me)."""
    return _auth_user_to_user_info(current_user)


@router.put("/profile", response_model=UserInfo)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
    db: Optional[Session] = Depends(get_db),
):
    """Cập nhật thông tin hồ sơ người dùng trong PostgreSQL."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể kết nối đến cơ sở dữ liệu.",
        )

    db_user = None
    if current_user.email:
        db_user = (
            db.query(User)
            .filter(func.lower(User.email) == current_user.email.lower())
            .first()
        )
    if not db_user and current_user.user_id_num > 0:
        db_user = (
            db.query(User).filter(User.user_id == current_user.user_id_num).first()
        )

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản trong cơ sở dữ liệu.",
        )

    if payload.name is not None and payload.name.strip():
        db_user.name = payload.name.strip()
    if payload.phone is not None:
        db_user.phone = payload.phone.strip()
    if payload.current_role is not None:
        db_user.current_role = payload.current_role.strip()
    if payload.location is not None:
        db_user.location = payload.location.strip()
    if payload.avatar is not None:
        db_user.avatar = payload.avatar.strip()

    if payload.email is not None and payload.email.strip():
        new_email = payload.email.strip().lower()
        if new_email != (db_user.email or "").lower():
            if not EMAIL_REGEX.match(new_email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Địa chỉ email mới không đúng định dạng.",
                )
            dup = (
                db.query(User)
                .filter(
                    (func.lower(User.email) == new_email)
                    & (User.user_id != db_user.user_id)
                )
                .first()
            )
            if dup:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email này đã được sử dụng bởi tài khoản khác.",
                )
            db_user.email = new_email

    db_user.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(db_user)
    except Exception as exc:
        db.rollback()
        logger.error("Commit failed on profile update: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể lưu thông tin vào cơ sở dữ liệu.",
        ) from exc

    return _db_user_to_user_info(db_user)


@router.post(
    "/change-password",
    dependencies=[Depends(rate_limit("auth_change_pw", settings.RATE_LIMIT_AUTH_PER_MIN))],
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
    db: Optional[Session] = Depends(get_db),
):
    """Đổi mật khẩu cho người dùng đang đăng nhập."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể kết nối đến cơ sở dữ liệu.",
        )

    db_user = (
        db.query(User)
        .filter(func.lower(User.email) == current_user.email.lower())
        .first()
        if current_user.email
        else None
    )
    if not db_user and current_user.user_id_num > 0:
        db_user = db.query(User).filter(User.user_id == current_user.user_id_num).first()

    if not db_user or not db_user.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy tài khoản mật khẩu hợp lệ.",
        )

    if not bcrypt.checkpw(
        payload.current_password.encode("utf-8"),
        db_user.password.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không chính xác.",
        )

    db_user.password = bcrypt.hashpw(
        payload.new_password.encode("utf-8"),
        bcrypt.gensalt(rounds=10),
    ).decode("utf-8")
    db_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ok", "message": "Đổi mật khẩu thành công."}


# ============================================================================
# Admin User Management Endpoints
# ============================================================================


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    role: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: AuthenticatedUser = Depends(require_roles("ADMIN", "RECRUITER")),
    db: Optional[Session] = Depends(get_db),
):
    """Danh sách tài khoản người dùng (chỉ Admin/Recruiter)."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể kết nối đến cơ sở dữ liệu.",
        )

    query = db.query(User)
    if role and role.strip().upper() in {"CANDIDATE", "RECRUITER", "ADMIN"}:
        query = query.filter(func.lower(User.role) == normalize_role_for_db(role))
    if search and search.strip():
        pattern = f"%{search.strip().lower()}%"
        query = query.filter(
            func.lower(User.name).like(pattern) | func.lower(User.email).like(pattern)
        )

    total = query.count()
    rows = query.order_by(User.user_id.desc()).limit(limit).all()
    return AdminUserListResponse(
        total=total,
        users=[_db_user_to_user_info(u) for u in rows],
    )


@router.post("/users", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: AdminCreateUserRequest,
    _: AuthenticatedUser = Depends(require_roles("ADMIN")),
    db: Optional[Session] = Depends(get_db),
):
    """Tạo tài khoản với quyền chỉ định (chỉ ADMIN)."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể kết nối đến cơ sở dữ liệu.",
        )
    email_clean = payload.email.strip().lower()
    if not EMAIL_REGEX.match(email_clean):
        raise HTTPException(status_code=400, detail="Địa chỉ email không đúng định dạng.")
    if payload.role.strip().upper() not in {"CANDIDATE", "RECRUITER", "ADMIN"}:
        raise HTTPException(status_code=400, detail="Vai trò phải là CANDIDATE, RECRUITER hoặc ADMIN.")
    if db.query(User).filter(func.lower(User.email) == email_clean).first():
        raise HTTPException(status_code=400, detail="Email này đã tồn tại.")

    hashed = bcrypt.hashpw(
        payload.password.encode("utf-8"), bcrypt.gensalt(rounds=10)
    ).decode("utf-8")
    new_user = User(
        email=email_clean,
        password=hashed,
        name=payload.name.strip(),
        role=normalize_role_for_db(payload.role),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return _db_user_to_user_info(new_user)


@router.patch("/users/{user_id}/role", response_model=UserInfo)
def admin_update_user_role(
    user_id: int,
    payload: AdminRoleUpdateRequest,
    current_admin: AuthenticatedUser = Depends(require_roles("ADMIN")),
    db: Optional[Session] = Depends(get_db),
):
    """Cập nhật quyền của tài khoản (chỉ ADMIN)."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể kết nối đến cơ sở dữ liệu.",
        )
    desired_role = payload.role.strip().upper()
    if desired_role not in {"CANDIDATE", "RECRUITER", "ADMIN"}:
        raise HTTPException(status_code=400, detail="Vai trò không hợp lệ.")
    if user_id == current_admin.user_id_num and desired_role != "ADMIN":
        raise HTTPException(
            status_code=400,
            detail="Không thể tự hạ quyền ADMIN của chính bạn.",
        )

    target = db.query(User).filter(User.user_id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    target.role = normalize_role_for_db(desired_role)
    target.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(target)
    return _db_user_to_user_info(target)
