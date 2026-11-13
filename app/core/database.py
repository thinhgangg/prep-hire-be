from __future__ import annotations

import logging
from typing import Generator
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

_supabase_client: Client | None = None
_engine = None
_SessionLocal = None

Base = declarative_base()


def get_supabase() -> Client | None:
    """Trả về Supabase client (anon key - dùng cho user requests)."""
    global _supabase_client
    if create_client is None:
        logger.warning("Thư viện 'supabase' chưa được cài đặt.")
        return None
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY,
        )
    return _supabase_client


def get_supabase_admin() -> Client | None:
    """Trả về Supabase admin client (service role key - bypass RLS)."""
    if create_client is None:
        logger.warning("Thư viện 'supabase' chưa được cài đặt.")
        return None
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )


def get_engine():
    """Khởi tạo hoặc trả về SQLAlchemy engine tái sử dụng connection pool."""
    global _engine
    if _engine is None:
        db_url = settings.DATABASE_URL
        if db_url:
            try:
                _engine = create_engine(
                    db_url,
                    pool_pre_ping=True,
                    pool_recycle=300,
                    pool_size=5,
                    max_overflow=10,
                )
            except Exception as e:
                logger.error(f"Lỗi khởi tạo SQLAlchemy engine: {e}")
                return None
    return _engine


def get_session_factory():
    """Trả về sessionmaker factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        if engine is not None:
            _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db() -> Generator[Session | None, None, None]:
    """Dependency cung cấp SQLAlchemy session cho FastAPI router."""
    factory = get_session_factory()
    if factory is None:
        yield None
        return

    db = factory()
    try:
        yield db
    finally:
        db.close()
