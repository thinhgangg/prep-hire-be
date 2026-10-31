import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.stt import router as stt_router
from app.api.ai_proxy import router as ai_proxy_router
from app.api.tts import router as tts_router
from app.services.stt_service import stt_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        stt_service.warmup()
    except Exception:
        pass
    yield


app = FastAPI(
    title="NextStepAI API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stt_router)
app.include_router(ai_proxy_router)
app.include_router(tts_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "NextStepAI API is running",
        "env": settings.APP_ENV,
        "ai_service_url": settings.AI_SERVICE_URL,
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
