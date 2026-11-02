from __future__ import annotations

import re
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

MOCK_PASSWORD = "123456"

class LoginRequest(BaseModel):
    username: str
    password: str

class UserInfo(BaseModel):
    id: str
    user_id_num: int
    username: str
    name: str
    email: str
    role: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo

def _resolve_user(raw_username: str) -> Optional[UserInfo]:
    uname = raw_username.strip().lower()
    
    if uname == "admin":
        return UserInfo(
            id="admin-01",
            user_id_num=0,
            username="admin",
            name="Hoàng Nam (Admin)",
            email="admin@prephire.vn",
            role="ADMIN",
        )
    
    if uname == "recruiter":
        return UserInfo(
            id="recruiter-01",
            user_id_num=0,
            username="recruiter",
            name="Hoàng Nam (Recruiter)",
            email="recruiter@prephire.vn",
            role="RECRUITER",
        )
        
    if uname == "user":
        uname = "user1"
        
    # Match user1 to user100
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
        )
    
    return None

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    user = _resolve_user(payload.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập không tồn tại. Vui lòng sử dụng tài khoản từ user1 đến user100 (hoặc admin).",
        )
    
    if payload.password != MOCK_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mật khẩu không chính xác. Mật khẩu cho tất cả tài khoản mẫu là 123456.",
        )
        
    token = f"mock-token-{user.username}-{user.user_id_num}"
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=user,
    )

@router.get("/me", response_model=UserInfo)
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chưa đăng nhập")
    
    token = authorization.replace("Bearer ", "").strip()
    match = re.match(r"^mock-token-(user\d+|admin|recruiter)", token)
    if match:
        user = _resolve_user(match.group(1))
        if user:
            return user
            
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ")

@router.get("/mock-accounts")
def list_mock_accounts():
    """Danh sách 100 tài khoản mẫu dành cho việc thu thập dữ liệu thử nghiệm."""
    accounts = [
        {"username": f"user{i}", "name": f"Ứng viên {i}", "password": MOCK_PASSWORD, "role": "CANDIDATE"}
        for i in range(1, 101)
    ]
    accounts.insert(0, {"username": "admin", "name": "Quản trị viên", "password": MOCK_PASSWORD, "role": "ADMIN"})
    return {"total": len(accounts), "default_password": MOCK_PASSWORD, "accounts": accounts}

