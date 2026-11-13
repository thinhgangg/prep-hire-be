from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

MOCK_PASSWORD = "123456"


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
    role: Optional[str] = "CANDIDATE"


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    current_role: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None


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


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


# ============================================================================
# Helper Functions
# ============================================================================

def _normalize_role_for_fe(db_role: Optional[str]) -> str:
    """Chuyển đổi role từ database (user, admin, recruiter) sang FE (CANDIDATE, ADMIN, RECRUITER)."""
    if not db_role:
        return "CANDIDATE"
    r = db_role.strip().lower()
    if r == "admin":
        return "ADMIN"
    if r == "recruiter":
        return "RECRUITER"
    return "CANDIDATE"


def _normalize_role_for_db(fe_role: Optional[str]) -> str:
    """Chuyển đổi role từ frontend sang database role."""
    if not fe_role:
        return "user"
    r = fe_role.strip().lower()
    if r in ("admin",):
        return "admin"
    if r in ("recruiter",):
        return "recruiter"
    return "user"


def _db_user_to_user_info(user: User) -> UserInfo:
    email = (user.email or "").strip()
    username = email.split("@")[0] if "@" in email else (user.name or f"user{user.user_id}")
    fe_role = _normalize_role_for_fe(user.role)
    
    return UserInfo(
        id=f"user-{user.user_id:03d}",
        user_id_num=user.user_id,
        username=username,
        name=user.name or username,
        email=email,
        role=fe_role,
        avatar=user.avatar,
        phone=user.phone,
        current_role=user.current_role,
        location=user.location,
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT access token chuẩn với thời hạn hết hạn."""
    to_encode = data.copy()
    expire_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 1440)
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _resolve_mock_user(raw_username: str) -> Optional[UserInfo]:
    """Hỗ trợ fallback cho các tài khoản demo (user1..user100, admin, recruiter)."""
    uname = raw_username.strip().lower()
    
    if uname == "admin":
        return UserInfo(
            id="admin-01",
            user_id_num=0,
            username="admin",
            name="Hoàng Nam (Admin)",
            email="admin@prephire.vn",
            role="ADMIN",
            phone="+84 901 234 567",
            current_role="System Administrator",
            location="Đà Nẵng",
        )
    
    if uname == "recruiter":
        return UserInfo(
            id="recruiter-01",
            user_id_num=0,
            username="recruiter",
            name="Hoàng Nam (Recruiter)",
            email="recruiter@prephire.vn",
            role="RECRUITER",
            phone="+84 902 345 678",
            current_role="Talent Acquisition Lead",
            location="TP. Hồ Chí Minh",
        )
        
    if uname == "user":
        uname = "user1"
        
    match = re.match(r"^user([1-9]|[1-9][0-9]|100)$", uname)
    if match:
        num = int(match.group(1))
        return UserInfo(
            id=f"user-{num:03d}",
            user_id_num=num,
            username=f"user{num}",
            name=f"Ứng viên {num}",
            email=f"user{num}@prephire.vn",
            role="CANDIDATE",
            phone="+84 912 345 678",
            current_role="Senior Frontend Developer",
            location="Hà Nội",
        )
    
    return None


# ============================================================================
# Auth Endpoints
# ============================================================================

@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Đăng ký tài khoản người dùng mới vào hệ thống cơ sở dữ liệu."""
    email_clean = payload.email.strip().lower()
    
    # Kiểm tra tính hợp lệ của email
    email_regex = r"^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$"
    if not re.match(email_regex, email_clean):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Địa chỉ email không đúng định dạng.",
        )
        
    if len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu phải có ít nhất 6 ký tự.",
        )

    # Kiểm tra email đã tồn tại trong database chưa
    if db is not None:
        try:
            existing_user = db.query(User).filter(func.lower(User.email) == email_clean).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email này đã được đăng ký. Vui lòng đăng nhập hoặc sử dụng email khác.",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Lỗi truy vấn database khi đăng ký: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi kết nối cơ sở dữ liệu khi kiểm tra tài khoản.",
            )

    # Xác định họ tên hiển thị
    display_name = (payload.name or "").strip()
    if not display_name:
        display_name = email_clean.split("@")[0].replace(".", " ").capitalize()

    # Mã hoá mật khẩu bằng bcrypt
    salt = bcrypt.gensalt(rounds=10)
    hashed_password = bcrypt.hashpw(payload.password.encode("utf-8"), salt).decode("utf-8")

    db_role = _normalize_role_for_db(payload.role)

    # Lưu người dùng vào PostgreSQL
    if db is not None:
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
        except Exception as e:
            db.rollback()
            logger.error(f"Lỗi khi thêm người dùng mới: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Không thể tạo tài khoản người dùng: {str(e)}",
            )
    else:
        # Fallback offline
        user_info = UserInfo(
            id="user-demo-registered",
            user_id_num=999,
            username=email_clean.split("@")[0],
            name=display_name,
            email=email_clean,
            role=_normalize_role_for_fe(db_role),
        )

    # Sinh JWT access token
    token_payload = {
        "sub": str(user_info.user_id_num),
        "id": user_info.id,
        "user_id_num": user_info.user_id_num,
        "email": user_info.email,
        "role": user_info.role,
        "name": user_info.name,
    }
    access_token = create_access_token(token_payload)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_info,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Đăng nhập hệ thống: Kiểm tra cơ sở dữ liệu trước, fallback sang tài khoản mẫu nếu cần."""
    raw_identifier = payload.username.strip()
    identifier_lower = raw_identifier.lower()
    plain_password = payload.password

    # 1. Tìm kiếm trong Database (Email hoặc tên đăng nhập)
    if db is not None:
        try:
            db_user = db.query(User).filter(
                (func.lower(User.email) == identifier_lower) |
                (func.lower(User.name) == identifier_lower)
            ).first()

            if db_user:
                if not db_user.password:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Tài khoản này chưa thiết lập mật khẩu (đăng nhập bằng Google).",
                    )
                
                # Kiểm tra mật khẩu bcrypt
                try:
                    password_matches = bcrypt.checkpw(
                        plain_password.encode("utf-8"),
                        db_user.password.encode("utf-8")
                    )
                except Exception as e:
                    logger.warning(f"Lỗi so khớp mật khẩu bcrypt: {e}")
                    password_matches = False

                if not password_matches:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Mật khẩu không chính xác.",
                    )

                user_info = _db_user_to_user_info(db_user)
                token_payload = {
                    "sub": str(user_info.user_id_num),
                    "id": user_info.id,
                    "user_id_num": user_info.user_id_num,
                    "email": user_info.email,
                    "role": user_info.role,
                    "name": user_info.name,
                }
                access_token = create_access_token(token_payload)

                return LoginResponse(
                    access_token=access_token,
                    token_type="bearer",
                    user=user_info,
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Lỗi truy vấn database khi đăng nhập: {e}")

    # 2. Fallback sang mock accounts dành cho Demo
    mock_user = _resolve_mock_user(raw_identifier)
    if mock_user:
        if plain_password != MOCK_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mật khẩu không chính xác. Mật khẩu cho tài khoản mẫu là 123456.",
            )

        token_payload = {
            "sub": str(mock_user.user_id_num),
            "id": mock_user.id,
            "user_id_num": mock_user.user_id_num,
            "email": mock_user.email,
            "role": mock_user.role,
            "name": mock_user.name,
        }
        access_token = create_access_token(token_payload)

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=mock_user,
        )

    # 3. Không tìm thấy tài khoản nào
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tên đăng nhập hoặc email không tồn tại. Vui lòng đăng ký tài khoản mới hoặc dùng tài khoản mẫu.",
    )


@router.get("/me", response_model=UserInfo)
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Lấy thông tin người dùng hiện tại từ JWT Bearer token hoặc Mock token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu đăng nhập (thiếu Header Authorization).",
        )

    token = authorization.replace("Bearer ", "").strip()

    # 1. Kiểm tra định dạng mock token cũ
    match = re.match(r"^mock-token-(user\d+|admin|recruiter)", token)
    if match:
        user = _resolve_mock_user(match.group(1))
        if user:
            return user

    # 2. Giải mã JWT token
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id_str = payload.get("sub")
        email = payload.get("email")

        # Thử lấy thông tin mới nhất từ database
        if db is not None:
            db_user = None
            if user_id_str and user_id_str.isdigit():
                db_user = db.query(User).filter(User.user_id == int(user_id_str)).first()
            if not db_user and email:
                db_user = db.query(User).filter(func.lower(User.email) == email.lower()).first()
            if db_user:
                return _db_user_to_user_info(db_user)

        # Fallback từ payload claims của token
        if email or user_id_str:
            num = int(user_id_str) if (user_id_str and user_id_str.isdigit()) else 0
            return UserInfo(
                id=payload.get("id") or f"user-{num:03d}",
                user_id_num=num,
                username=payload.get("email", "").split("@")[0] or "user",
                name=payload.get("name") or "Người dùng",
                email=payload.get("email") or "",
                role=payload.get("role") or "CANDIDATE",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
        )
    except Exception as e:
        logger.warning(f"Lỗi giải mã JWT token: {e}")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token xác thực không hợp lệ.",
    )


@router.get("/profile", response_model=UserInfo)
def get_profile(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Lấy thông tin hồ sơ người dùng hiện tại (alias của /me)."""
    return get_current_user(authorization=authorization, db=db)


@router.put("/profile", response_model=UserInfo)
def update_profile(
    payload: ProfileUpdateRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Cập nhật thông tin hồ sơ người dùng trong cơ sở dữ liệu."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu đăng nhập để cập nhật hồ sơ.",
        )

    token = authorization.replace("Bearer ", "").strip()

    # 1. Fallback nếu dùng mock token
    match = re.match(r"^mock-token-(user\d+|admin|recruiter)", token)
    if match:
        mock_user = _resolve_mock_user(match.group(1))
        if mock_user:
            if payload.name:
                mock_user.name = payload.name.strip()
            if payload.phone is not None:
                mock_user.phone = payload.phone.strip()
            if payload.current_role is not None:
                mock_user.current_role = payload.current_role.strip()
            if payload.location is not None:
                mock_user.location = payload.location.strip()
            if payload.email is not None:
                mock_user.email = payload.email.strip()
            return mock_user

    # 2. Giải mã JWT token
    try:
        token_data = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
        )
    except Exception as e:
        logger.warning(f"Lỗi giải mã token khi cập nhật hồ sơ: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token xác thực không hợp lệ.",
        )

    user_id_str = token_data.get("sub")
    email = token_data.get("email")

    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể kết nối đến cơ sở dữ liệu.",
        )

    db_user = None
    if user_id_str and user_id_str.isdigit():
        db_user = db.query(User).filter(User.user_id == int(user_id_str)).first()
    if not db_user and email:
        db_user = db.query(User).filter(func.lower(User.email) == email.lower()).first()

    if not db_user:
        num = int(user_id_str) if (user_id_str and user_id_str.isdigit()) else 0
        return UserInfo(
            id=token_data.get("id") or f"user-{num:03d}",
            user_id_num=num,
            username=token_data.get("email", "").split("@")[0] or "user",
            name=payload.name or token_data.get("name") or "Người dùng",
            email=payload.email or token_data.get("email") or "",
            role=token_data.get("role") or "CANDIDATE",
            phone=payload.phone,
            current_role=payload.current_role,
            location=payload.location,
        )

    # Cập nhật các trường
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
            email_regex = r"^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$"
            if not re.match(email_regex, new_email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Địa chỉ email mới không đúng định dạng.",
                )
            dup = db.query(User).filter(
                (func.lower(User.email) == new_email) & (User.user_id != db_user.user_id)
            ).first()
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
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi commit cập nhật profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể lưu thông tin vào cơ sở dữ liệu.",
        )

    return _db_user_to_user_info(db_user)


@router.get("/mock-accounts")
def list_mock_accounts():
    """Danh sách các tài khoản mẫu dành cho việc thu thập dữ liệu thử nghiệm."""
    accounts = [
        {"username": f"user{i}", "name": f"Ứng viên {i}", "password": MOCK_PASSWORD, "role": "CANDIDATE"}
        for i in range(1, 101)
    ]
    accounts.insert(0, {"username": "admin", "name": "Quản trị viên", "password": MOCK_PASSWORD, "role": "ADMIN"})
    return {"total": len(accounts), "default_password": MOCK_PASSWORD, "accounts": accounts}
