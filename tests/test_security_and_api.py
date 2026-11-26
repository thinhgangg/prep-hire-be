from __future__ import annotations

import io
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, rate_limiter
from app.main import app
from app.models.notification import UserNotification
from app.models.user import User


@pytest.fixture()
def client(tmp_path: Path):
    """Isolated FastAPI TestClient backed by an in-memory SQLite database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": {"public": None}},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    rate_limiter.reset()

    old_upload_dir = settings.STT_UPLOAD_DIR
    old_cleanup = settings.STT_CLEANUP_AUDIO
    old_internal = settings.INTERNAL_SERVICE_SECRET
    settings.STT_UPLOAD_DIR = str(tmp_path / "stt_uploads")
    settings.STT_CLEANUP_AUDIO = True
    settings.INTERNAL_SERVICE_SECRET = "test-internal-secret-123"

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal

    app.dependency_overrides.clear()
    settings.STT_UPLOAD_DIR = old_upload_dir
    settings.STT_CLEANUP_AUDIO = old_cleanup
    settings.INTERNAL_SERVICE_SECRET = old_internal


def _make_admin_token() -> str:
    return create_access_token(
        {
            "sub": "9001",
            "id": "admin-9001",
            "user_id_num": 9001,
            "email": "admin@prephire.vn",
            "role": "ADMIN",
            "name": "Admin User",
        }
    )


def test_register_locks_role_to_candidate_and_allows_long_tld(client):
    test_client, _ = client
    resp = test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "attacker@prephire.technology",
            "password": "password123",
            "name": "Attempt Admin",
            "role": "ADMIN",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["role"] == "CANDIDATE"
    assert body["user"]["email"] == "attacker@prephire.technology"
    assert body["access_token"]


def test_mock_token_backdoor_rejected(client):
    test_client, _ = client
    headers = {"Authorization": "Bearer mock-token-admin"}
    assert test_client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        test_client.put(
            "/api/v1/auth/profile",
            headers=headers,
            json={"name": "Hacked"},
        ).status_code
        == 401
    )
    assert (
        test_client.get("/api/v1/interview/sessions", headers=headers).status_code
        == 401
    )


def test_ai_proxy_enforces_auth_and_rbac(client):
    test_client, _ = client

    # Unauthenticated blocked
    assert test_client.get("/api/v1/interview/sessions").status_code == 401

    # Register a candidate
    reg = test_client.post(
        "/api/v1/auth/register",
        json={"email": "cand1@prephire.studio", "password": "password123", "name": "Cand 1"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    uid = reg.json()["user"]["user_id_num"]
    cand_headers = {"Authorization": f"Bearer {token}"}

    # Candidate cannot list all sessions
    assert (
        test_client.get("/api/v1/interview/sessions", headers=cand_headers).status_code
        == 403
    )
    # Candidate cannot list another user's sessions
    other_uid = uid + 99
    assert (
        test_client.get(
            f"/api/v1/interview/users/{other_uid}/sessions",
            headers=cand_headers,
        ).status_code
        == 403
    )
    # Candidate cannot mutate jobs or write HR reviews
    assert (
        test_client.post("/api/v1/jobs/", headers=cand_headers, json={}).status_code
        == 403
    )
    assert (
        test_client.put(
            "/api/v1/interview/sessions/s1/review",
            headers=cand_headers,
            json={"shortlisted": True},
        ).status_code
        == 403
    )


def test_change_password_flow(client):
    test_client, _ = client
    reg = test_client.post(
        "/api/v1/auth/register",
        json={"email": "pw@prephire.vn", "password": "oldpassword", "name": "PW User"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Wrong current password rejected
    bad = test_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "wrong", "new_password": "newpassword1"},
    )
    assert bad.status_code == 400

    # Correct change succeeds
    ok = test_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "oldpassword", "new_password": "newpassword1"},
    )
    assert ok.status_code == 200

    # Old password fails, new password works
    assert (
        test_client.post(
            "/api/v1/auth/login",
            json={"username": "pw@prephire.vn", "password": "oldpassword"},
        ).status_code
        == 401
    )
    assert (
        test_client.post(
            "/api/v1/auth/login",
            json={"username": "pw@prephire.vn", "password": "newpassword1"},
        ).status_code
        == 200
    )


def test_admin_user_management_rbac(client):
    test_client, _ = client
    reg = test_client.post(
        "/api/v1/auth/register",
        json={"email": "member@prephire.vn", "password": "password123", "name": "Member"},
    )
    cand_token = reg.json()["access_token"]
    member_id = reg.json()["user"]["user_id_num"]

    # Candidate blocked from /users
    assert (
        test_client.get(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {cand_token}"},
        ).status_code
        == 403
    )

    admin_headers = {"Authorization": f"Bearer {_make_admin_token()}"}
    list_resp = test_client.get("/api/v1/auth/users", headers=admin_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    patch_resp = test_client.patch(
        f"/api/v1/auth/users/{member_id}/role",
        headers=admin_headers,
        json={"role": "RECRUITER"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["role"] == "RECRUITER"


def test_stt_auth_ownership_and_audio_cleanup(client, tmp_path: Path):
    test_client, _ = client

    # Anonymous rejected
    anon = test_client.post(
        "/api/v1/stt/jobs",
        files={"audio": ("a.webm", io.BytesIO(b"fake-audio-bytes"), "audio/webm")},
    )
    assert anon.status_code == 401

    reg1 = test_client.post(
        "/api/v1/auth/register",
        json={"email": "stt1@prephire.vn", "password": "password123"},
    )
    reg2 = test_client.post(
        "/api/v1/auth/register",
        json={"email": "stt2@prephire.vn", "password": "password123"},
    )
    h1 = {"Authorization": f"Bearer {reg1.json()['access_token']}"}
    h2 = {"Authorization": f"Bearer {reg2.json()['access_token']}"}

    fake_result = {
        "raw_transcript": "xin chao",
        "corrected_transcript": "Xin chào",
        "segments": [],
        "edits": [],
        "needs_review": False,
        "language": "vi",
        "latency_ms": 10,
        "model": "small",
    }

    with patch("app.api.stt.stt_service.transcribe", return_value=fake_result):
        created = test_client.post(
            "/api/v1/stt/jobs",
            headers=h1,
            files={"audio": ("sample.webm", io.BytesIO(b"webm-data"), "audio/webm")},
        )
        assert created.status_code == 202
        job_id = created.json()["id"]

        # Wait briefly for worker thread to complete and clean up file
        for _ in range(30):
            polled = test_client.get(f"/api/v1/stt/jobs/{job_id}", headers=h1)
            assert polled.status_code == 200
            if polled.json()["status"] == "completed":
                break
            time.sleep(0.05)

        assert polled.json()["status"] == "completed"
        assert polled.json()["result"]["corrected_transcript"] == "Xin chào"

        # Temporary uploaded audio file must be cleaned up
        upload_dir = tmp_path / "stt_uploads"
        assert list(upload_dir.glob("*")) == []

        # Another candidate must not access this STT job
        forbidden = test_client.get(f"/api/v1/stt/jobs/{job_id}", headers=h2)
        assert forbidden.status_code == 403


def test_tts_prewarm_internal_service_auth(client):
    test_client, _ = client
    assert (
        test_client.post("/api/v1/tts/prewarm", json={"text": "Xin chào"}).status_code
        == 401
    )
    with patch("app.api.tts.tts_service.prewarm") as mock_prewarm:
        ok = test_client.post(
            "/api/v1/tts/prewarm",
            headers={"X-Internal-Service-Key": "test-internal-secret-123"},
            json={"text": "Xin chào ứng viên"},
        )
        assert ok.status_code == 202
        mock_prewarm.assert_called_once()


def test_notifications_and_read_all(client):
    test_client, _ = client
    reg = test_client.post(
        "/api/v1/auth/register",
        json={"email": "notif@prephire.vn", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    # Force table init check skipped because SQLite fixture already created table
    with patch("app.api.notifications._ensure_notifications_table"):
        res = test_client.get("/api/v1/notifications", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["unread_count"] >= 1
        assert len(data["items"]) >= 1

        read_all = test_client.post("/api/v1/notifications/read-all", headers=headers)
        assert read_all.status_code == 200

        after = test_client.get("/api/v1/notifications", headers=headers).json()
        assert after["unread_count"] == 0


def test_production_security_rejects_weak_secrets():
    weak = Settings(
        APP_ENV="production",
        JWT_SECRET="local-demo-only-change-me",
        DATABASE_URL="",
        INTERNAL_SERVICE_SECRET="",
    )
    with pytest.raises(RuntimeError):
        weak.validate_production_security()

