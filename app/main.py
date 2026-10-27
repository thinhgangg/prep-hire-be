from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.stt import router as stt_router
from app.services.stt_service import stt_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stt_service.warmup()
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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stt_router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "NextStepAI API is running", "env": settings.APP_ENV}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
