import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_db
from app import app
from database.models import Document, Report
from database.repositories.report_repository import ReportRepository


def _signup(client, name, role="USER"):
    response = client.post(
        "/auth/signup",
        json={
            "name": name,
            "email": f"{name.replace(' ', '.').lower()}@example.com",
            "password": "super-secret-password",
            "role": role,
        },
    )
    assert response.status_code == 201
    return response.json()


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _document(owner_id, suffix):
    return Document(
        id=str(uuid4()),
        filename=f"audit-{suffix}.txt",
        stored_filename=f"{uuid4()}.txt",
        file_type="text/plain",
        file_size=12,
        storage_path=f"storage/uploads/{uuid4()}.txt",
        status="COMPLETED",
        owner_id=owner_id,
    )


def _create_report(db_session, tmp_path, document, audit, suffix):
    relative_path = f"storage/reports/{suffix}.json"
    artifact_path = tmp_path / relative_path
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(
            {
                "document_id": document.id,
                "llm_candidate_audit": audit,
            }
        ),
        encoding="utf-8",
    )
    return ReportRepository(db_session).create(
        Report(
            id=str(uuid4()),
            document_id=document.id,
            report_type="AUDIT",
            report_path=relative_path,
            gemma_invoked=True,
        )
    )


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


def test_audit_persists_reloads_across_sessions_roles_and_documents(
    api_client,
    db_session,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    owner_auth = _signup(api_client, "Audit Owner")
    reviewer_auth = _signup(api_client, "Audit Reviewer", role="REVIEWER")
    admin_auth = _signup(api_client, "Audit Admin", role="ADMIN")
    other_auth = _signup(api_client, "Other Owner")

    first_document = _document(owner_auth["user"]["id"], "first")
    second_document = _document(owner_auth["user"]["id"], "second")
    empty_document = _document(owner_auth["user"]["id"], "empty")
    db_session.add_all([first_document, second_document, empty_document])
    db_session.commit()

    first_audit = {
        "accepted": [
            {
                "entity_value": "Synthetic Candidate A",
                "entity_type": "PERSON",
                "decision": "CONFIRM",
                "confidence": 0.93,
                "detector": "Gemma4:e4b",
                "reasoning": "Synthetic context supports a person entity.",
            }
        ],
        "rejected": [
            {
                "entity_value": "Synthetic Candidate B",
                "entity_type": "ORGANIZATION",
                "decision": "REJECT",
                "confidence": 0.31,
                "detector": "Gemma4:e4b",
                "reasoning": "Synthetic context indicates a section label.",
            }
        ],
    }
    second_audit = {
        "accepted": [
            {
                "entity_value": "Second Document Candidate",
                "entity_type": "ADDRESS",
                "decision": "RECLASSIFY",
                "confidence": 0.86,
                "detector": "Gemma4:e4b",
                "reasoning": "Synthetic location context supports an address.",
            }
        ],
        "rejected": [],
    }

    first_report = _create_report(
        db_session, tmp_path, first_document, first_audit, "first"
    )
    second_report = _create_report(
        db_session, tmp_path, second_document, second_audit, "second"
    )
    _create_report(
        db_session,
        tmp_path,
        empty_document,
        {"accepted": [], "rejected": []},
        "empty",
    )

    assert first_report.llm_candidate_audit == first_audit
    assert second_report.llm_candidate_audit == second_audit

    report_detail = api_client.get(
        f"/reports/{first_report.id}",
        headers=_headers(owner_auth["access_token"]),
    )
    assert report_detail.status_code == 200
    assert report_detail.json()["llm_candidate_audit"] == first_audit
    assert report_detail.json()["payload"]["llm_candidate_audit"] == first_audit

    (tmp_path / first_report.report_path).unlink()

    first_response = api_client.get(
        f"/documents/{first_document.id}/reports",
        headers=_headers(owner_auth["access_token"]),
    )
    assert first_response.status_code == 200
    first_payload = first_response.json()[0]
    assert first_payload["document_id"] == first_document.id
    assert first_payload["gemma_invoked"] is True
    assert first_payload["llm_candidate_audit"] == first_audit
    assert first_payload["llm_candidate_accepted_count"] == 1
    assert first_payload["llm_candidate_rejected_count"] == 1

    refresh_response = api_client.get(
        f"/documents/{first_document.id}/reports",
        headers=_headers(owner_auth["access_token"]),
    )
    assert refresh_response.json()[0]["llm_candidate_audit"] == first_audit
    assert (
        db_session.query(Report)
        .filter(Report.document_id == first_document.id)
        .count()
        == 1
    )

    assert api_client.post(
        "/auth/logout",
        headers=_headers(owner_auth["access_token"]),
    ).status_code == 204
    login_response = api_client.post(
        "/auth/login",
        json={
            "email": "audit.owner@example.com",
            "password": "super-secret-password",
        },
    )
    assert login_response.status_code == 200
    owner_token = login_response.json()["access_token"]
    assert api_client.get(
        f"/documents/{first_document.id}/reports",
        headers=_headers(owner_token),
    ).json()[0]["llm_candidate_audit"] == first_audit

    for role in ("REVIEWER", "ADMIN", "USER"):
        role_update = api_client.patch(
            f"/admin/users/{owner_auth['user']['id']}/role",
            headers=_headers(admin_auth["access_token"]),
            json={"role": role},
        )
        assert role_update.status_code == 200
        role_response = api_client.get(
            f"/documents/{first_document.id}/reports",
            headers=_headers(owner_token),
        )
        assert role_response.status_code == 200
        assert role_response.json()[0]["llm_candidate_audit"] == first_audit

    for auth in (reviewer_auth, admin_auth):
        role_response = api_client.get(
            f"/documents/{first_document.id}/reports",
            headers=_headers(auth["access_token"]),
        )
        assert role_response.status_code == 200
        assert role_response.json()[0]["llm_candidate_audit"] == first_audit

    second_payload = api_client.get(
        f"/documents/{second_document.id}/reports",
        headers=_headers(owner_token),
    ).json()[0]
    assert second_payload["document_id"] == second_document.id
    assert second_payload["llm_candidate_audit"] == second_audit
    assert second_payload["llm_candidate_audit"] != first_audit

    empty_payload = api_client.get(
        f"/documents/{empty_document.id}/reports",
        headers=_headers(owner_token),
    ).json()[0]
    assert empty_payload["llm_candidate_audit"] == {
        "accepted": [],
        "rejected": [],
    }
    assert empty_payload["llm_candidate_accepted_count"] == 0
    assert empty_payload["llm_candidate_rejected_count"] == 0

    denied = api_client.get(
        f"/documents/{first_document.id}/reports",
        headers=_headers(other_auth["access_token"]),
    )
    assert denied.status_code == 403


def test_legacy_report_audit_backfill_rejects_wrong_document_payload(
    api_client,
    db_session,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    owner_auth = _signup(api_client, "Legacy Audit Owner")
    document = _document(owner_auth["user"]["id"], "legacy")
    db_session.add(document)
    db_session.commit()

    relative_path = "storage/reports/legacy-mismatch.json"
    artifact_path = tmp_path / relative_path
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(
            {
                "document_id": str(uuid4()),
                "llm_candidate_audit": {
                    "accepted": [{"entity_value": "Wrong document"}],
                    "rejected": [],
                },
            }
        ),
        encoding="utf-8",
    )
    report = Report(
        id=str(uuid4()),
        document_id=document.id,
        report_type="AUDIT",
        report_path=relative_path,
        llm_candidate_audit=None,
    )
    db_session.add(report)
    db_session.commit()

    response = api_client.get(
        f"/documents/{document.id}/reports",
        headers=_headers(owner_auth["access_token"]),
    )
    assert response.status_code == 200
    assert response.json()[0]["document_id"] == document.id
    assert response.json()[0]["llm_candidate_audit"] is None
