from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.stt import router as stt_router
from app.api.ai_proxy import router as ai_proxy_router

app = FastAPI(
    title="NextStepAI API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
