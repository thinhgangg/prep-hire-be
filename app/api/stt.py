from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.security import (
    AuthenticatedUser,
    get_current_user_dep,
    rate_limit,
    require_roles,
)
from app.services.stt_service import stt_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stt", tags=["Speech to text"])
_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()
_executor_lock = threading.Lock()
_executor: ThreadPoolExecutor | None = None

_ALLOWED_AUDIO_EXTENSIONS = {".webm", ".ogg", ".wav", ".mp3", ".m4a", ".mp4", ".flac"}


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=max(1, int(settings.STT_MAX_WORKERS)),
                thread_name_prefix="stt",
            )
        return _executor


def shutdown_stt_executor() -> None:
    global _executor
    with _executor_lock:
        if _executor is not None:
            _executor.shutdown(wait=False, cancel_futures=False)
            _executor = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _public_job(job: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in job.items()
        if key not in {"audio_path", "_expires_at", "owner_id"}
    }


def _prune_expired_jobs() -> int:
    """Evict expired finished jobs from RAM to prevent unbounded memory growth."""
    now_mono = time.monotonic()
    removed = 0
    with _jobs_lock:
        expired_ids = [
            jid
            for jid, j in _jobs.items()
            if j.get("status") in {"completed", "failed"}
            and float(j.get("_expires_at") or 0) <= now_mono
        ]
        for jid in expired_ids:
            _jobs.pop(jid, None)
            removed += 1
    return removed


def _update(job_id: str, **values: Any) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(values, updated_at=_now())


def _safe_remove_audio(audio_path_str: str) -> None:
    if not settings.STT_CLEANUP_AUDIO or not audio_path_str:
        return
    try:
        path = Path(audio_path_str)
        if path.exists():
            path.unlink()
    except OSError as exc:
        logger.warning("Failed to delete temporary STT audio %s: %s", audio_path_str, exc)


def _run_job(job_id: str) -> None:
    with _jobs_lock:
        job = dict(_jobs.get(job_id) or {})
    if not job:
        return
    audio_path_str = job.get("audio_path", "")
    ttl_seconds = max(60, int(settings.STT_JOB_TTL_SECONDS))
    try:
        _update(job_id, status="processing", stage="loading_model", progress=15)
        _update(job_id, stage="transcribing", progress=35)
        result = stt_service.transcribe(Path(audio_path_str), job["context"])
        _update(job_id, stage="correcting_text", progress=85)
        _update(
            job_id,
            status="completed",
            stage="completed",
            progress=100,
            result=result,
            completed_at=_now(),
            _expires_at=time.monotonic() + ttl_seconds,
        )
    except Exception as exc:
        _update(
            job_id,
            status="failed",
            stage="failed",
            error=str(exc),
            progress=100,
            _expires_at=time.monotonic() + ttl_seconds,
        )
    finally:
        _safe_remove_audio(audio_path_str)


@router.post(
    "/jobs",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("stt_upload", settings.RATE_LIMIT_API_PER_MIN))],
)
async def create_job(
    audio: UploadFile = File(...),
    interview_id: str = Form("session"),
    question_id: str = Form("question-04"),
    context: str = Form(""),
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
) -> dict[str, Any]:
    _prune_expired_jobs()
    content = await audio.read()
    max_bytes = settings.STT_MAX_UPLOAD_MB * 1024 * 1024
    if not content:
        raise HTTPException(status_code=400, detail="Tệp audio rỗng")
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Audio vượt quá {settings.STT_MAX_UPLOAD_MB} MB",
        )

    job_id = uuid.uuid4().hex
    raw_suffix = Path(audio.filename or "answer.webm").suffix.lower() or ".webm"
    suffix = raw_suffix if raw_suffix in _ALLOWED_AUDIO_EXTENSIONS else ".webm"

    upload_dir = Path(settings.STT_UPLOAD_DIR)
    if not upload_dir.is_absolute():
        upload_dir = Path(__file__).resolve().parents[2] / upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    audio_path = upload_dir / f"{job_id}{suffix}"
    audio_path.write_bytes(content)

    job = {
        "id": job_id,
        "owner_id": current_user.user_id_num,
        "interview_id": interview_id,
        "question_id": question_id,
        "status": "queued",
        "stage": "queued",
        "progress": 5,
        "context": context,
        "audio_path": str(audio_path),
        "created_at": _now(),
        "updated_at": _now(),
        "result": None,
        "error": None,
        "_expires_at": None,
    }
    with _jobs_lock:
        _jobs[job_id] = job
    _get_executor().submit(_run_job, job_id)
    return _public_job(job)


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
) -> dict[str, Any]:
    _prune_expired_jobs()
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy STT job")
        if (
            current_user.role.upper() not in {"ADMIN", "RECRUITER"}
            and job.get("owner_id") != current_user.user_id_num
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập STT job này.",
            )
        return _public_job(dict(job))


@router.get("/config")
def get_stt_config(
    _: AuthenticatedUser = Depends(get_current_user_dep),
) -> dict[str, Any]:
    supabase_datastore = bool(
        settings.SUPABASE_URL
        and (settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY)
    )
    return {
        "model": "remote-whisper" if settings.STT_REMOTE_BASE_URL else settings.STT_MODEL,
        "device": "remote-gpu" if settings.STT_REMOTE_BASE_URL else settings.STT_DEVICE,
        "compute_type": "float16" if settings.STT_REMOTE_BASE_URL else settings.STT_COMPUTE_TYPE,
        "language": settings.STT_LANGUAGE,
        "max_workers": settings.STT_MAX_WORKERS,
        "remote_worker_configured": bool(settings.STT_REMOTE_BASE_URL),
        "datastore_source": (
            "supabase"
            if supabase_datastore
            else "jsonl" if stt_service._resolve_datastore_path() is not None else "none"
        ),
        "datastore_configured": supabase_datastore
        or stt_service._resolve_datastore_path() is not None,
    }


@router.post("/datastore/refresh")
def refresh_datastore(
    _: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> dict[str, Any]:
    pattern_count = stt_service.refresh_datastore()
    return {"status": "ok", "alias_pattern_count": pattern_count}
