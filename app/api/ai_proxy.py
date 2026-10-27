from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from app.core.config import settings

router = APIRouter(tags=["AI Service Proxy"])


@router.api_route("/api/v1/interview/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_interview(path: str, request: Request):
    ai_url = f"{settings.AI_SERVICE_URL.rstrip('/')}/api/v1/interview/{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}}
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.request(
                method=request.method,
                url=ai_url,
                params=request.query_params,
                content=body,
                headers=headers,
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                media_type=resp.headers.get("content-type"),
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Cannot reach AI server at {settings.AI_SERVICE_URL}: {exc}",
        )


@router.api_route("/api/v1/cv/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_cv(path: str, request: Request):
    ai_url = f"{settings.AI_SERVICE_URL.rstrip('/')}/api/v1/cv/{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}}
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.request(
                method=request.method,
                url=ai_url,
                params=request.query_params,
                content=body,
                headers=headers,
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                media_type=resp.headers.get("content-type"),
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Cannot reach AI server at {settings.AI_SERVICE_URL}: {exc}",
        )
