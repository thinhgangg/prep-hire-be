from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db, get_engine
from app.core.security import AuthenticatedUser, get_current_user_dep
from app.models.notification import UserNotification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])

_table_initialized = False


def _ensure_notifications_table() -> None:
    global _table_initialized
    if _table_initialized:
        return
    engine = get_engine()
    if engine is None:
        return
    try:
        UserNotification.__table__.create(bind=engine, checkfirst=True)
        _table_initialized = True
    except Exception as exc:
        logger.warning("Could not ensure user_notifications table: %s", exc)


class NotificationItem(BaseModel):
    id: int
    title: str
    message: str
    category: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    unread_count: int
    items: list[NotificationItem]


class NotificationCreateRequest(BaseModel):
    user_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)
    category: str = Field(default="system", max_length=40)
    link: Optional[str] = Field(default=None, max_length=255)


def _serialize(row: UserNotification) -> NotificationItem:
    return NotificationItem(
        id=row.notification_id,
        title=row.title,
        message=row.message,
        category=row.category,
        link=row.link,
        is_read=bool(row.is_read),
        created_at=row.created_at,
    )


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
    db: Optional[Session] = Depends(get_db),
):
    if db is None:
        return NotificationListResponse(unread_count=0, items=[])
    _ensure_notifications_table()
    try:
        rows = (
            db.query(UserNotification)
            .filter(UserNotification.user_id == current_user.user_id_num)
            .order_by(UserNotification.created_at.desc())
            .limit(limit)
            .all()
        )
        # Seed a helpful welcome notification on first login if empty
        if not rows:
            welcome = UserNotification(
                user_id=current_user.user_id_num,
                title="Chào mừng đến với PrepHire AI",
                message=(
                    "Hệ thống đã sẵn sàng. Bạn có thể quản lý phiên phỏng vấn, shortlist ứng viên và quản trị vị trí tuyển dụng."
                    if current_user.role in {"ADMIN", "RECRUITER"}
                    else "Hãy tải CV lên và bắt đầu phiên phỏng vấn thử AI để nhận phân tích năng lực chi tiết."
                ),
                category="system",
                link="/admin/dashboard" if current_user.role in {"ADMIN", "RECRUITER"} else "/app/interviews/new",
                is_read=False,
                created_at=datetime.now(timezone.utc),
            )
            db.add(welcome)
            db.commit()
            db.refresh(welcome)
            rows = [welcome]

        unread_count = (
            db.query(UserNotification)
            .filter(
                UserNotification.user_id == current_user.user_id_num,
                UserNotification.is_read.is_(False),
            )
            .count()
        )
        return NotificationListResponse(
            unread_count=unread_count,
            items=[_serialize(r) for r in rows],
        )
    except Exception as exc:
        db.rollback()
        logger.warning("Failed to load notifications: %s", exc)
        return NotificationListResponse(unread_count=0, items=[])


@router.post("", response_model=NotificationItem, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
    db: Optional[Session] = Depends(get_db),
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    _ensure_notifications_table()
    target_uid = (
        payload.user_id
        if (payload.user_id is not None and current_user.role in {"ADMIN", "RECRUITER"})
        else current_user.user_id_num
    )
    row = UserNotification(
        user_id=target_uid,
        title=payload.title.strip(),
        message=payload.message.strip(),
        category=payload.category.strip() or "system",
        link=payload.link,
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.post("/{notification_id}/read", response_model=NotificationItem)
def mark_notification_read(
    notification_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
    db: Optional[Session] = Depends(get_db),
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    _ensure_notifications_table()
    row = (
        db.query(UserNotification)
        .filter(
            UserNotification.notification_id == notification_id,
            UserNotification.user_id == current_user.user_id_num,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo.")
    row.is_read = True
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.post("/read-all")
def mark_all_notifications_read(
    current_user: AuthenticatedUser = Depends(get_current_user_dep),
    db: Optional[Session] = Depends(get_db),
):
    if db is None:
        return {"status": "ok", "updated": 0}
    _ensure_notifications_table()
    updated = (
        db.query(UserNotification)
        .filter(
            UserNotification.user_id == current_user.user_id_num,
            UserNotification.is_read.is_(False),
        )
        .update({"is_read": True})
    )
    db.commit()
    return {"status": "ok", "updated": updated}

