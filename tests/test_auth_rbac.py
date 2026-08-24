from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_db
from api.routes.admin import canonical_llm_provider
from app import app
from core.security import hash_token
from database.models import AuthSession, Document, Entity, User
from database.repositories.user_repository import UserRepository


def signup_user(client, name, role="USER", password="super-secret-password"):
    response = client.post(
        "/auth/signup",
        json={
            "name": name,
            "email": f"{name.replace(' ', '.').lower()}@example.com",
            "password": password,
            "role": role,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["access_token"], payload["user"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def api_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


# ============================================================
# Signup / Login
# ============================================================


def test_signup_creates_user_with_hashed_password(api_client, db_session):
    token, user = signup_user(api_client, "Alice User")

    assert token
    assert user["email"] == "alice.user@example.com"
    assert user["role"] == "USER"

    stored = db_session.query(User).filter(User.email == "alice.user@example.com").first()
    assert stored is not None
    assert stored.password_hash != "super-secret-password"
    assert stored.password_hash.startswith("pbkdf2_sha256$")


def test_signup_rejects_duplicate_email(api_client):
    signup_user(api_client, "Duplicate Person")
    response = api_client.post(
        "/auth/signup",
        json={
            "name": "Duplicate Person",
            "email": "duplicate.person@example.com",
            "password": "super-secret-password",
            "role": "USER",
        },
    )
    assert response.status_code == 409


def test_signup_rejects_invalid_role(api_client):
    response = api_client.post(
        "/auth/signup",
        json={
            "name": "Bad Role",
            "email": "bad.role@example.com",
            "password": "super-secret-password",
            "role": "SUPERHERO",
        },
    )
    assert response.status_code == 422


def test_signup_rejects_short_password(api_client):
    response = api_client.post(
        "/auth/signup",
        json={
            "name": "Short Pass",
            "email": "short.pass@example.com",
            "password": "short",
            "role": "USER",
        },
    )
    assert response.status_code == 422


def test_login_success(api_client):
    signup_user(api_client, "Login Tester")
    response = api_client.post(
        "/auth/login",
        json={
            "email": "login.tester@example.com",
            "password": "super-secret-password",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["user"]["email"] == "login.tester@example.com"


def test_login_wrong_password(api_client):
    signup_user(api_client, "Wrong Pass")
    response = api_client.post(
        "/auth/login",
        json={
            "email": "wrong.pass@example.com",
            "password": "not-the-password",
        },
    )
    assert response.status_code == 401


def test_login_unknown_email(api_client):
    response = api_client.post(
        "/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "super-secret-password",
        },
    )
    assert response.status_code == 401


# ============================================================
# /auth/me + logout + session lifecycle
# ============================================================


def test_me_returns_current_user(api_client):
    token, user = signup_user(api_client, "Me Tester")
    response = api_client.get("/auth/me", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
    assert response.json()["email"] == "me.tester@example.com"


def test_me_without_token(api_client):
    response = api_client.get("/auth/me")
    assert response.status_code == 401


def test_me_invalid_token(api_client):
    response = api_client.get("/auth/me", headers=auth_headers("not-a-real-token"))
    assert response.status_code == 401


def test_logout_invalidates_session(api_client):
    token, _ = signup_user(api_client, "Logout Tester")
    assert api_client.get("/auth/me", headers=auth_headers(token)).status_code == 200

    logout_response = api_client.post("/auth/logout", headers=auth_headers(token))
    assert logout_response.status_code == 204

    assert api_client.get("/auth/me", headers=auth_headers(token)).status_code == 401


def test_expired_session_rejected(api_client, db_session):
    token, _ = signup_user(api_client, "Expired Tester")
    repo = UserRepository(db_session)
    session = repo.get_session_by_token_hash(hash_token(token))
    assert session is not None
    session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.add(session)
    db_session.commit()

    response = api_client.get("/auth/me", headers=auth_headers(token))
    assert response.status_code == 401


def test_token_survives_across_requests(api_client):
    token, _ = signup_user(api_client, "Persistent Session")
    headers = auth_headers(token)
    assert api_client.get("/auth/me", headers=headers).status_code == 200
    assert api_client.get("/auth/me", headers=headers).status_code == 200


# ============================================================
# RBAC: upload + document access
# ============================================================

def _upload_file(client, headers):
    return client.post(
        "/upload/",
        headers=headers,
        files={
            "file": (
                "note.txt",
                b"Patient: Jane Doe\nSSN: 123-45-6789\n",
                "text/plain",
            ),
        },
    )


def test_unauthenticated_upload_rejected(api_client):
    response = api_client.post(
        "/upload/",
        files={
            "file": ("note.txt", b"hello", "text/plain"),
        },
    )
    assert response.status_code == 401


def test_user_can_upload_and_read_own_document(api_client, db_session):
    token, user = signup_user(api_client, "Doc Owner")
    headers = auth_headers(token)

    upload_response = _upload_file(api_client, headers)
    assert upload_response.status_code == 201
    document_id = upload_response.json()["document"]["document_id"]

    saved = db_session.get(Document, document_id)
    assert saved.owner_id == user["id"]

    assert api_client.get(f"/documents/{document_id}/status", headers=headers).status_code == 200


def test_user_cannot_read_other_users_document(api_client, db_session):
    owner_token, owner = signup_user(api_client, "First Owner")
    other_token, other = signup_user(api_client, "Second Owner")

    upload_response = _upload_file(api_client, auth_headers(owner_token))
    document_id = upload_response.json()["document"]["document_id"]

    other_headers = auth_headers(other_token)
    assert api_client.get(f"/documents/{document_id}/status", headers=other_headers).status_code == 403
    assert api_client.get(f"/documents/{document_id}/text", headers=other_headers).status_code == 403


def test_user_cannot_access_review_endpoints(api_client):
    token, _ = signup_user(api_client, "No Reviews")
    headers = auth_headers(token)
    assert api_client.get("/documents/some-id/reviews", headers=headers).status_code == 403
    assert api_client.patch(
        "/reviews/some-id",
        headers=headers,
        json={"review_status": "APPROVED"},
    ).status_code == 403


def test_user_cannot_list_entities(api_client):
    token, _ = signup_user(api_client, "No Entities")
    assert api_client.get(
        "/documents/some-id/entities",
        headers=auth_headers(token),
    ).status_code == 403


def test_reviewer_can_access_reviews(api_client):
    reviewer_token, _ = signup_user(api_client, "Active Reviewer", role="REVIEWER")
    reviewer_headers = auth_headers(reviewer_token)

    upload_response = _upload_file(api_client, reviewer_headers)
    assert upload_response.status_code == 201
    document_id = upload_response.json()["document"]["document_id"]

    assert api_client.get(
        f"/documents/{document_id}/reviews",
        headers=reviewer_headers,
    ).status_code == 200


def test_reviewer_entity_list_filters_rejected_and_keeps_legacy_rows(
    api_client,
    db_session,
):
    reviewer_token, reviewer = signup_user(
        api_client,
        "Entity Reviewer",
        role="REVIEWER",
    )
    document = Document(
        id=str(uuid4()),
        filename="synthetic.txt",
        stored_filename=f"{uuid4()}.txt",
        file_type="text/plain",
        file_size=10,
        storage_path="synthetic.txt",
        owner_id=reviewer["id"],
    )
    accepted = Entity(
        id=str(uuid4()),
        document_id=document.id,
        entity_type="EMAIL",
        entity_value="synthetic.user@example.test",
        processing_stage="DETECTION",
        is_accepted_by_ai=True,
    )
    rejected = Entity(
        id=str(uuid4()),
        document_id=document.id,
        entity_type="PERSON",
        entity_value="Synthetic Header",
        processing_stage="REJECTED_BY_AI",
        ai_decision="REJECT",
        is_accepted_by_ai=False,
    )
    legacy = Entity(
        id=str(uuid4()),
        document_id=document.id,
        entity_type="DOCUMENT_ID",
        entity_value="SYNTHETIC-LEGACY",
    )
    db_session.add_all([document, accepted, rejected, legacy])
    db_session.commit()
    legacy.processing_stage = None
    legacy.is_accepted_by_ai = None
    db_session.commit()

    headers = auth_headers(reviewer_token)
    default_response = api_client.get(
        f"/documents/{document.id}/entities",
        headers=headers,
    )
    all_response = api_client.get(
        f"/documents/{document.id}/entities?include_rejected=true",
        headers=headers,
    )

    assert default_response.status_code == 200
    assert {item["entity_id"] for item in default_response.json()} == {
        accepted.id,
        legacy.id,
    }
    assert all_response.status_code == 200
    assert {item["entity_id"] for item in all_response.json()} == {
        accepted.id,
        rejected.id,
        legacy.id,
    }


# ============================================================
# RBAC: admin endpoints
# ============================================================


def test_user_cannot_access_admin(api_client):
    token, _ = signup_user(api_client, "Not Admin")
    headers = auth_headers(token)
    assert api_client.get("/admin/users", headers=headers).status_code == 403
    assert api_client.get("/admin/stats", headers=headers).status_code == 403


def test_reviewer_cannot_access_admin(api_client):
    token, _ = signup_user(api_client, "Reviewer Not Admin", role="REVIEWER")
    headers = auth_headers(token)
    assert api_client.get("/admin/users", headers=headers).status_code == 403


def test_admin_can_list_users_and_change_roles(api_client):
    admin_token, admin = signup_user(api_client, "Real Admin", role="ADMIN")
    admin_headers = auth_headers(admin_token)

    user_token, user = signup_user(api_client, "Target User")

    users_response = api_client.get("/admin/users", headers=admin_headers)
    assert users_response.status_code == 200
    emails = [entry["email"] for entry in users_response.json()]
    assert "target.user@example.com" in emails
    assert "real.admin@example.com" in emails

    role_response = api_client.patch(
        f"/admin/users/{user['id']}/role",
        headers=admin_headers,
        json={"role": "REVIEWER"},
    )
    assert role_response.status_code == 200
    assert role_response.json()["role"] == "REVIEWER"

    me_after = api_client.get("/auth/me", headers=auth_headers(user_token))
    assert me_after.json()["role"] == "REVIEWER"


@pytest.mark.parametrize(
    ("stored_provider", "display_provider"),
    [
        ("azure", "Azure"),
        ("azure_openai", "Azure"),
        ("AzureOpenAI", "Azure"),
        ("gemma", "Gemma"),
        ("gemma4:e4b", "Gemma"),
        ("ollama", "Gemma"),
        (None, None),
        ("", None),
    ],
)
def test_canonical_llm_provider(stored_provider, display_provider):
    assert canonical_llm_provider(stored_provider) == display_provider


def test_admin_stats_endpoint(api_client, db_session):
    admin_token, _ = signup_user(api_client, "Stats Admin", role="ADMIN")
    headers = auth_headers(admin_token)
    upload_response = _upload_file(api_client, headers)
    assert upload_response.status_code == 201
    document_id = upload_response.json()["document"]["document_id"]
    document = db_session.get(Document, document_id)
    document.llm_provider = "ollama"
    db_session.commit()

    response = api_client.get("/admin/stats", headers=headers)
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_users"] >= 1
    assert stats["total_documents"] >= 1
    assert "ADMIN" in stats["users_by_role"]
    assert set(stats["processing_overview"]) == {
        "completed",
        "pending_review",
        "failed",
    }
    assert set(stats["privacy_summary"]) == {"pii", "phi"}
    assert 0 <= stats["completion_rate"] <= 100
    assert stats["recent_documents"][0]["filename"] == "note.txt"
    assert stats["recent_documents"][0]["owner"] == "Stats Admin"
    assert stats["recent_documents"][0]["llm_provider"] == "Gemma"


def test_admin_can_deactivate_and_reactivate_user(api_client):
    admin_token, _ = signup_user(api_client, "User Manager", role="ADMIN")
    user_token, user = signup_user(api_client, "Toggle User")
    admin_headers = auth_headers(admin_token)

    deactivate = api_client.patch(
        f"/admin/users/{user['id']}/active",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False

    assert api_client.get("/auth/me", headers=auth_headers(user_token)).status_code == 401
    assert api_client.post(
        "/auth/login",
        json={"email": "toggle.user@example.com", "password": "super-secret-password"},
    ).status_code == 403

    reactivate = api_client.patch(
        f"/admin/users/{user['id']}/active",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert reactivate.status_code == 200
    assert reactivate.json()["is_active"] is True


def test_admin_cannot_set_invalid_role(api_client):
    admin_token, _ = signup_user(api_client, "Strict Admin", role="ADMIN")
    _, user = signup_user(api_client, "Role Victim")
    response = api_client.patch(
        f"/admin/users/{user['id']}/role",
        headers=auth_headers(admin_token),
        json={"role": "BOGUS"},
    )
    assert response.status_code == 422


def test_deactivated_user_token_rejected(api_client):
    admin_token, _ = signup_user(api_client, "Deactivator", role="ADMIN")
    user_token, user = signup_user(api_client, "Soon Disabled")
    api_client.patch(
        f"/admin/users/{user['id']}/active",
        headers=auth_headers(admin_token),
        json={"is_active": False},
    )
    assert api_client.get("/auth/me", headers=auth_headers(user_token)).status_code == 401


# ============================================================
# Security utilities
# ============================================================


def test_password_hashing_roundtrip():
    from core.security import hash_password, verify_password

    hashed = hash_password("correct horse battery staple")
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password("correct horse battery staple", hashed) is True
    assert verify_password("wrong password", hashed) is False
    assert verify_password("correct horse battery staple", "garbage") is False


def test_hash_token_is_deterministic():
    from core.security import generate_session_token, hash_token

    raw = generate_session_token()
    assert len(raw) >= 32
    digest = hash_token(raw)
    assert len(digest) == 64
    assert hash_token(raw) == digest
