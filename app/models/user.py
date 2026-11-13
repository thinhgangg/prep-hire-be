from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=True)
    name = Column(String, nullable=False)
    role = Column(Text, nullable=False, default="user")
    avatar = Column(String, nullable=True)
    google_id = Column(String, nullable=True)
    base_cv_id = Column(Integer, nullable=True)
    current_role = Column(String, nullable=True)
    location = Column(String, nullable=True)
    experience_years = Column(Float, nullable=True)
    target_salary_min = Column(Float, nullable=True)
    target_salary_max = Column(Float, nullable=True)
    phone = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

