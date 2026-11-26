from __future__ import annotations

import re
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.config import settings
from app.core.security import AuthenticatedUser, get_current_user_dep, rate_limit

router = APIRouter(tags=["AI Service Proxy"])

_HOP_BY_HOP_HEADERS = {
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "content-encoding",
}

# Never allow external clients to spoof gateway identity headers
_STRIP_CLIENT_HEADERS = {
    "x-internal-service-key",
    "x-user-id",
    "x-user-role",
    "x-user-email",
}

_shared_client: httpx.AsyncClient | None = None


def _get_proxy_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
    return _shared_client


async def close_proxy_client() -> None:
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
    _shared_client = None


_STAFF_ROLES = {"ADMIN", "RECRUITER"}
_USER_SESSIONS_RE = re.compile(r"^users/(\d+)/sessions/?$")
_STAFF_ONLY_INTERVIEW_PATHS = (
    re.compile(r"^sessions/?$"),
    re.compile(r"^sessions/[^/]+/expert-annotations/?$"),
    re.compile(r"^sessions/[^/]+/expert-consensus/?$"),
    re.compile(r"^sessions/[^/]+/review/?$"),
    re.compile(r"^benchmarks(?:/.*)?$"),
)


def _enforce_interview_rbac(path: str, method: str, user: AuthenticatedUser) -> None:
    clean_path = path.strip("/")
    role = user.role.upper()
    is_staff = role in _STAFF_ROLES

    # 1. GET /interview/sessions lists all users' sessions -> staff only
    if method.upper() == "GET" and clean_path == "sessions":
        if not is_staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên hoặc Nhà tuyển dụng mới được xem toàn bộ phiên phỏng vấn.",
            )
        return

    # 2. GET /interview/users/{uid}/sessions -> owner or staff
    user_match = _USER_SESSIONS_RE.match(clean_path)
    if user_match:
        target_uid = int(user_match.group(1))
        if not is_staff and target_uid != user.user_id_num:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn chỉ được xem phiên phỏng vấn của chính mình.",
            )
        return

    # 3. Staff-only management / review / benchmark paths (GET review is allowed for staff; write ops staff only)
    for pattern in _STAFF_ONLY_INTERVIEW_PATHS[1:]:
        if pattern.match(clean_path):
            if not is_staff:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền thực hiện thao tác quản trị này.",
                )
            return


def _enforce_jobs_rbac(method: str, user: AuthenticatedUser) -> None:
    if method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        if user.role.upper() not in _STAFF_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên hoặc Nhà tuyển dụng mới được chỉnh sửa tin tuyển dụng.",
            )


async def _forward(
    ai_url: str,
    request: Request,
    current_user: AuthenticatedUser,
) -> Response:
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP_HEADERS
        and k.lower() not in _STRIP_CLIENT_HEADERS
    }
    if settings.INTERNAL_SERVICE_SECRET:
        headers["X-Internal-Service-Key"] = settings.INTERNAL_SERVICE_SECRET
    headers["X-User-Id"] = str(current_user.user_id_num)
    headers["X-User-Role"] = current_user.role.upper()
    headers["X-User-Email"] = current_user.email or ""

    body = await request.body()
    try:
        resp = await _get_proxy_client().request(
            method=request.method,
            url=ai_url,
            params=request.query_params,
            content=body,
            headers=headers,
        )
        resp_headers = {
            k: v
            for k, v in resp.headers.items()
            if k.lower() not in _HOP_BY_HOP_HEADERS
        }
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=resp_headers,
            media_type=resp.headers.get("content-type"),
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Cannot reach AI server at {settings.AI_SERVICE_URL}: {exc}",
        ) from exc


@router.api_route(
    "/api/v1/interview/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    dependencies=[Depends(rate_limit("ai_interview", settings.RATE_LIMIT_API_PER_MIN))],
)
async def proxy_interview(
    path: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
):
    _enforce_interview_rbac(path, request.method, current_user)
    ai_url = f"{settings.AI_SERVICE_URL.rstrip('/')}/api/v1/interview/{path}"
    return await _forward(ai_url, request, current_user)


@router.api_route(
    "/api/v1/cv/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    dependencies=[Depends(rate_limit("ai_cv", settings.RATE_LIMIT_API_PER_MIN))],
)
async def proxy_cv(
    path: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
):
    ai_url = f"{settings.AI_SERVICE_URL.rstrip('/')}/api/v1/cv/{path}"
    return await _forward(ai_url, request, current_user)


@router.api_route(
    "/api/v1/jobs/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    dependencies=[Depends(rate_limit("ai_jobs", settings.RATE_LIMIT_API_PER_MIN))],
)
async def proxy_jobs(
    path: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
):
    _enforce_jobs_rbac(request.method, current_user)
    ai_url = f"{settings.AI_SERVICE_URL.rstrip('/')}/api/v1/jobs/{path}"
    return await _forward(ai_url, request, current_user)
