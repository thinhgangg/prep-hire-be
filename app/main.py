import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.api.stt import router as stt_router, shutdown_stt_executor
from app.api.ai_proxy import router as ai_proxy_router, close_proxy_client
from app.api.tts import router as tts_router
from app.api.auth import router as auth_router
from app.api.notifications import router as notifications_router
from app.services.stt_service import stt_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_production_security()
    if settings.STT_PREWARM_ENABLED:
        try:
            stt_service.warmup()
        except Exception:
            pass
    try:
        yield
    finally:
        await close_proxy_client()
        shutdown_stt_executor()


app = FastAPI(
    title="PrepHire AI API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(notifications_router)
app.include_router(stt_router)
app.include_router(ai_proxy_router)
app.include_router(tts_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "PrepHire AI API is running",
        "env": settings.APP_ENV,
        "ai_service_url": settings.AI_SERVICE_URL,
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
