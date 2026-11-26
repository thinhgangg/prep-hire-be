from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from app.core.config import settings

router = APIRouter(tags=["AI Service Proxy"])

_HOP_BY_HOP_HEADERS = {
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "content-encoding",
}

_shared_client = httpx.AsyncClient(
    timeout=60.0,
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
)


async def _forward(ai_url: str, request: Request) -> Response:
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP_HEADERS
    }
    body = await request.body()
    try:
        resp = await _shared_client.request(
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
        )


@router.api_route("/api/v1/interview/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_interview(path: str, request: Request):
    ai_url = f"{settings.AI_SERVICE_URL.rstrip('/')}/api/v1/interview/{path}"
    return await _forward(ai_url, request)


@router.api_route("/api/v1/cv/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_cv(path: str, request: Request):
    ai_url = f"{settings.AI_SERVICE_URL.rstrip('/')}/api/v1/cv/{path}"
    return await _forward(ai_url, request)
