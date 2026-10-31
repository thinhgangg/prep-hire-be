from __future__ import annotations

import hashlib
import io
import os
import threading
import wave
from pathlib import Path

import numpy as np

from app.core.config import settings


class KorvaTtsService:
    """Lazy-loaded KorvaTTS engine with a local WAV cache."""

    SAMPLE_RATE = 44_100

    def __init__(self) -> None:
        self._model = None
        self._model_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._project_root = Path(__file__).resolve().parents[2]
        self._cache_dir = self._resolve_path(settings.KORVA_CACHE_DIR)
        self._hf_home = self._resolve_path(settings.KORVA_HF_HOME)
        os.environ.setdefault("HF_HOME", str(self._hf_home))
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    def _resolve_path(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else self._project_root / path

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _get_model(self):
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    from korvatts import TTS

                    self._model = TTS()
        return self._model

    @staticmethod
    def normalize_text(text: str) -> str:
        return " ".join((text or "").split())

    @classmethod
    def _to_wav_bytes(cls, audio: np.ndarray) -> bytes:
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        samples = np.nan_to_num(samples, nan=0.0, posinf=1.0, neginf=-1.0)
        peak = float(np.max(np.abs(samples))) if samples.size else 0.0
        if peak > 1.0:
            samples = samples / peak
        pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(cls.SAMPLE_RATE)
            wav.writeframes(pcm.tobytes())
        return output.getvalue()

    def synthesize(self, text: str) -> tuple[bytes, bool]:
        normalized = self.normalize_text(text)
        cache_key = hashlib.sha256(
            (
                f"korva-v1|{settings.KORVA_VOICE}|{settings.KORVA_TOTAL_STEPS}|"
                f"{settings.KORVA_SPEED}|{normalized}"
            ).encode("utf-8")
        ).hexdigest()
        cache_file = self._cache_dir / f"{cache_key}.wav"
        if cache_file.exists():
            return cache_file.read_bytes(), True

        with self._inference_lock:
            if cache_file.exists():
                return cache_file.read_bytes(), True
            model = self._get_model()
            audio, _duration = model.synthesize(
                normalized,
                voice=settings.KORVA_VOICE,
                lang="vi",
                total_steps=settings.KORVA_TOTAL_STEPS,
                speed=settings.KORVA_SPEED,
            )
            wav_bytes = self._to_wav_bytes(audio)
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(wav_bytes)
            return wav_bytes, False

    def prewarm(self, text: str) -> None:
        try:
            self.synthesize(text)
        except Exception as exc:
            # Prewarm is an optimization; failures are retried by /speech and
            # must not affect delivery of the interview question.
            print(f"[TTS PREWARM] failed: {exc}")


tts_service = KorvaTtsService()

