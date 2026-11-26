from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import (
    AuthenticatedUser,
    get_current_user_dep,
    rate_limit,
    require_user_or_internal_service,
)
from app.services.tts_service import tts_service


router = APIRouter(prefix="/api/v1/tts", tags=["Text to Speech"])


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=settings.TTS_MAX_TEXT_LENGTH)


@router.get("/health")
def tts_health() -> dict[str, object]:
    return {
        "status": "ok",
        "engine": "korvatts",
        "voice": settings.KORVA_VOICE,
        "loaded": tts_service.loaded,
        "lazy_load": True,
        "total_steps": settings.KORVA_TOTAL_STEPS,
    }


@router.post(
    "/speech",
    dependencies=[Depends(rate_limit("tts_speech", settings.RATE_LIMIT_API_PER_MIN))],
)
async def synthesize_speech(
    payload: SpeechRequest,
    _: AuthenticatedUser = Depends(get_current_user_dep),
) -> Response:
    text = tts_service.normalize_text(payload.text)
    if not text:
        raise HTTPException(status_code=400, detail="Nội dung cần đọc không được để trống")
    try:
        wav_bytes, cached = await run_in_threadpool(tts_service.synthesize, text)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"KorvaTTS không thể tạo âm thanh: {exc}") from exc
    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "Cache-Control": "private, max-age=86400",
            "X-TTS-Voice": settings.KORVA_VOICE,
            "X-TTS-Cache": "hit" if cached else "miss",
        },
    )


@router.post("/prewarm", status_code=status.HTTP_202_ACCEPTED)
def prewarm_speech(
    payload: SpeechRequest,
    background_tasks: BackgroundTasks,
    _: AuthenticatedUser | None = Depends(require_user_or_internal_service),
) -> dict[str, object]:
    """Start synthesis as soon as AI selects a question, without blocking AI."""
    text = tts_service.normalize_text(payload.text)
    if not text:
        raise HTTPException(status_code=400, detail="Nội dung cần đọc không được để trống")
    background_tasks.add_task(tts_service.prewarm, text)
    return {"accepted": True, "voice": settings.KORVA_VOICE}
