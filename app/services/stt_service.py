from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings


class STTService:
    """Lazy-loaded Whisper engine plus conservative terminology correction."""

    def __init__(self) -> None:
        self._model: Any | None = None
        self._model_lock = threading.Lock()
        self._alias_patterns: list[tuple[re.Pattern[str], str, dict[str, Any]]] | None = None
        self._alias_lock = threading.Lock()
        self._alias_loaded_at = 0.0

    def warmup(self) -> None:
        """Load the model and terminology matcher before the first answer."""
        if not settings.STT_REMOTE_BASE_URL:
            self._get_model()
        self._get_alias_patterns()

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is None:
                try:
                    from faster_whisper import WhisperModel
                except ImportError as exc:
                    raise RuntimeError(
                        "faster-whisper chưa được cài. Chạy: pip install -r requirements.txt"
                    ) from exc
                self._model = WhisperModel(
                    settings.STT_MODEL,
                    device=settings.STT_DEVICE,
                    compute_type=settings.STT_COMPUTE_TYPE,
                )
        return self._model

    def transcribe(self, audio_path: Path, context: str = "") -> dict[str, Any]:
        if settings.STT_REMOTE_BASE_URL:
            return self._transcribe_remote(audio_path, context)

        started = time.perf_counter()
        model = self._get_model()
        inference_started = time.perf_counter()
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=settings.STT_LANGUAGE,
            task="transcribe",
            beam_size=settings.STT_BEAM_SIZE,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 400, "speech_pad_ms": 200},
            initial_prompt=context.strip() or None,
            condition_on_previous_text=False,
        )
        segments = [
            {
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "text": segment.text.strip(),
            }
            for segment in segments_iter
        ]
        raw = " ".join(segment["text"] for segment in segments).strip()
        inference_ms = round((time.perf_counter() - inference_started) * 1000, 3)
        correction_started = time.perf_counter()
        correction = self.correct_terminology(raw)
        correction_ms = round((time.perf_counter() - correction_started) * 1000, 3)
        datastore_source = (
            "supabase"
            if settings.SUPABASE_URL
            and (settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY)
            else "jsonl"
        )
        return {
            "raw_transcript": raw,
            **correction,
            "segments": segments,
            "language": getattr(info, "language", settings.STT_LANGUAGE),
            "language_probability": getattr(info, "language_probability", None),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "inference_ms": inference_ms,
            "correction_ms": correction_ms,
            "model": settings.STT_MODEL,
        }

    def _transcribe_remote(self, audio_path: Path, context: str) -> dict[str, Any]:
        started = time.perf_counter()
        base_url = settings.STT_REMOTE_BASE_URL.rstrip("/")
        headers = {"ngrok-skip-browser-warning": "true"}
        timeout = httpx.Timeout(settings.STT_REMOTE_TIMEOUT_SECONDS)
        with httpx.Client(timeout=timeout, headers=headers) as client:
            with audio_path.open("rb") as audio_stream:
                response = client.post(
                    f"{base_url}/api/v1/stt/jobs",
                    files={
                        "audio": (
                            audio_path.name,
                            audio_stream,
                            self._audio_content_type(audio_path),
                        )
                    },
                    data={
                        "interview_id": "local-proxy",
                        "question_id": audio_path.stem,
                        "context": context,
                    },
                )
            response.raise_for_status()
            remote_job = response.json()
            remote_job_id = remote_job["id"]
            deadline = time.monotonic() + settings.STT_REMOTE_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                response = client.get(f"{base_url}/api/v1/stt/jobs/{remote_job_id}")
                response.raise_for_status()
                remote_job = response.json()
                if remote_job.get("status") == "completed":
                    break
                if remote_job.get("status") == "failed":
                    raise RuntimeError(
                        remote_job.get("error") or "Whisper GPU worker failed"
                    )
                time.sleep(settings.STT_REMOTE_POLL_INTERVAL_SECONDS)
            else:
                raise TimeoutError("Whisper GPU worker timed out")

        remote_result = remote_job.get("result") or {}
        raw = str(remote_result.get("raw_transcript") or "").strip()
        correction_started = time.perf_counter()
        correction = self.correct_terminology(raw)
        correction_ms = round((time.perf_counter() - correction_started) * 1000, 3)
        datastore_source = (
            "supabase"
            if settings.SUPABASE_URL
            and (settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY)
            else "jsonl"
        )
        return {
            **remote_result,
            "raw_transcript": raw,
            **correction,
            "correction_ms": correction_ms,
            "remote_roundtrip_ms": round((time.perf_counter() - started) * 1000, 3),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "datastore_source": datastore_source,
            "model": f"{remote_result.get('model', 'whisper')}-{datastore_source}-corrected",
        }

    @staticmethod
    def _audio_content_type(audio_path: Path) -> str:
        return {
            ".webm": "audio/webm",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
        }.get(audio_path.suffix.lower(), "application/octet-stream")

    def correct_terminology(self, text: str) -> dict[str, Any]:
        candidates: list[tuple[int, int, str, dict[str, Any]]] = []
        for pattern, canonical, item in self._get_alias_patterns():
            for match in pattern.finditer(text):
                candidates.append((match.start(), match.end(), canonical, item))

        candidates.sort(key=lambda value: (value[0], -(value[1] - value[0])))
        accepted: list[tuple[int, int, str, dict[str, Any]]] = []
        cursor = -1
        needs_review = False
        for start, end, canonical, item in candidates:
            if start < cursor:
                needs_review = True
                continue
            accepted.append((start, end, canonical, item))
            cursor = end

        corrected = text
        edits: list[dict[str, Any]] = []
        for start, end, canonical, item in reversed(accepted):
            before = text[start:end]
            corrected = corrected[:start] + canonical + corrected[end:]
            edits.append(
                {
                    "start": start,
                    "end": end,
                    "before": before,
                    "after": canonical,
                    "method": "exact_verified_alias",
                    "evidence": item.get("evidence", "verified datastore alias"),
                }
            )
        edits.reverse()
        return {
            "corrected_transcript": corrected,
            "edits": edits,
            "needs_review": needs_review,
        }

    def refresh_datastore(self) -> int:
        with self._alias_lock:
            self._alias_patterns = None
            self._alias_loaded_at = 0.0
        return len(self._get_alias_patterns())

    def _get_alias_patterns(self) -> list[tuple[re.Pattern[str], str, dict[str, Any]]]:
        cache_age = time.monotonic() - self._alias_loaded_at
        if self._alias_patterns is not None and cache_age < settings.STT_DATASTORE_CACHE_SECONDS:
            return self._alias_patterns
        with self._alias_lock:
            cache_age = time.monotonic() - self._alias_loaded_at
            if self._alias_patterns is None or cache_age >= settings.STT_DATASTORE_CACHE_SECONDS:
                patterns: list[tuple[re.Pattern[str], str, dict[str, Any]]] = []
                for item in self._load_verified_aliases():
                    canonical = item["canonical"]
                    for alias in item["aliases"]:
                        if alias.casefold() == canonical.casefold():
                            continue
                        pattern = re.compile(
                            r"(?<!\w)" + re.escape(alias) + r"(?!\w)",
                            re.IGNORECASE,
                        )
                        patterns.append((pattern, canonical, item))
                self._alias_patterns = patterns
                self._alias_loaded_at = time.monotonic()
        return self._alias_patterns

    def _load_verified_aliases(self) -> list[dict[str, Any]]:
        if settings.SUPABASE_URL and (
            settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        ):
            try:
                rows = self._load_supabase_aliases()
                if rows:
                    return rows
            except Exception as exc:
                print(f"--- STT DATASTORE SUPABASE FALLBACK: {exc} ---")

        path = self._resolve_datastore_path()
        if path is None:
            return []
        rows = []
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                row = json.loads(line)
                aliases = list(row.get("aliases", []))
                for observation in row.get("observed_asr_variants", []):
                    if observation.get("verified"):
                        aliases.append(observation["text"])
                if row.get("verified") or aliases:
                    rows.append(
                        {
                            "canonical": row["canonical"],
                            "aliases": list(dict.fromkeys(aliases)),
                            "evidence": row.get("evidence", f"datastore:{row.get('term_id', 'unknown')}"),
                        }
                    )
        return rows

    @staticmethod
    def _load_supabase_aliases() -> list[dict[str, Any]]:
        from supabase import create_client

        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        client = create_client(settings.SUPABASE_URL, key)
        terms = client.table("stt_terms").select(
            "id,canonical_text,normalized_key,auto_correct,ambiguity_level"
        ).execute().data or []
        pronunciations = client.table("stt_term_pronunciations").select(
            "term_id,pronunciation_text,is_verified"
        ).execute().data or []

        aliases_by_term: dict[Any, list[str]] = {}
        for row in pronunciations:
            value = str(row.get("pronunciation_text") or "").strip()
            if value:
                aliases_by_term.setdefault(row.get("term_id"), []).append(value)

        try:
            variants = client.table("stt_asr_variants").select("*").execute().data or []
        except Exception:
            variants = []
        for row in variants:
            if row.get("is_verified") is False:
                continue
            value = next(
                (
                    str(row.get(key) or "").strip()
                    for key in ("variant_text", "observed_text", "asr_text", "text")
                    if row.get(key)
                ),
                "",
            )
            if value:
                aliases_by_term.setdefault(row.get("term_id"), []).append(value)

        result = []
        for term in terms:
            canonical = str(term.get("canonical_text") or "").strip()
            if not canonical:
                continue
            aliases = [canonical, *aliases_by_term.get(term.get("id"), [])]
            result.append(
                {
                    "canonical": canonical,
                    "aliases": list(dict.fromkeys(aliases)),
                    "evidence": f"supabase:stt_terms:{term.get('id')}",
                }
            )
        return result

    @staticmethod
    def _resolve_datastore_path() -> Path | None:
        if settings.STT_DATASTORE_PATH:
            configured = Path(settings.STT_DATASTORE_PATH).expanduser()
            if configured.is_file():
                return configured
            raise RuntimeError(f"Không tìm thấy STT_DATASTORE_PATH: {configured}")

        bundled = Path(__file__).resolve().parents[2] / "data" / "verified_aliases.jsonl"
        return bundled if bundled.is_file() else None


stt_service = STTService()
