from fastapi.testclient import TestClient

from api.dependencies import get_db
from database.models import Document
from app import app
from modules.upload.storage import StorageService
from orchestration.workflow import DocumentProcessingWorkflow


class FakeRedisProducer:
    def __init__(self):
        self.published = []

    def publish(self, job):
        self.published.append(job)
        return True


def test_upload_process_and_read_extracted_text_e2e(
    db_session,
    tmp_path,
    monkeypatch,
):
    producer = FakeRedisProducer()
    upload_dir = tmp_path / "uploads"
    monkeypatch.chdir(tmp_path)

    def override_get_db():
        yield db_session

    monkeypatch.setattr(StorageService, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(
        "modules.upload.service.RedisProducer",
        lambda redis_client: producer,
    )

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            upload_response = client.post(
                "/upload/",
                files={
                    "file": (
                        "invoice.txt",
                        (
                            b"Invoice Number INV-2002\n"
                            b"Bill To: Jane Patient\n"
                            b"Email: jane.patient@example.com\n"
                            b"Reference: 998-99-5253\n"
                            b"Amount Due: 75.00"
                        ),
                        "text/plain",
                    ),
                },
            )

            assert upload_response.status_code == 201
            document_id = upload_response.json()["document"]["document_id"]
            assert len(producer.published) == 1
            assert str(producer.published[0].document_id) == document_id

            DocumentProcessingWorkflow(db_session).execute(document_id)

            status_response = client.get(f"/documents/{document_id}/status")
            text_response = client.get(f"/documents/{document_id}/text")

            assert status_response.status_code == 200
            assert text_response.status_code == 200
            assert status_response.json()["document_status"] == "COMPLETED"
            assert status_response.json()["has_extracted_text"] is True
            assert text_response.json()["processing_status"] == "COMPLETED"
            assert "Invoice Number INV-2002" in text_response.json()["extracted_text"]

            saved_document = db_session.get(Document, document_id)
            expected_text_path = StorageService.extracted_path(
                saved_document.run_id,
                document_id,
            )
            assert text_response.json()["extracted_text_path"] == (
                expected_text_path.as_posix()
            )
            assert (tmp_path / expected_text_path).read_text(
                encoding="utf-8"
            ) == text_response.json()["extracted_text"]

            entities_response = client.get(f"/documents/{document_id}/entities")
            assert entities_response.status_code == 200
            entities = entities_response.json()
            assert any(
                entity["entity_type"] == "EMAIL"
                and entity["entity_value"] == "jane.patient@example.com"
                for entity in entities
            )

            reviews_response = client.get(f"/documents/{document_id}/reviews")
            assert reviews_response.status_code == 200
            reviews = reviews_response.json()
            assert reviews
            pending_review = next(
                review for review in reviews
                if review["review_status"] == "PENDING"
                and review["entity"]["entity_type"] == "SSN"
            )

            decision_response = client.patch(
                f"/reviews/{pending_review['review_id']}",
                json={
                    "reviewer": "integration-reviewer",
                    "review_status": "APPROVED",
                    "review_comment": "Confirmed by API integration test.",
                    "final_confidence": 0.91,
                },
            )
            assert decision_response.status_code == 200
            decision = decision_response.json()
            assert decision["review_status"] == "APPROVED"
            assert decision["reviewer"] == "integration-reviewer"
            assert decision["entity"]["is_review_required"] is False
            assert decision["entity"]["final_confidence"] == 0.91

            redactions_response = client.get(
                f"/documents/{document_id}/redactions"
            )
            assert redactions_response.status_code == 200
            redactions = redactions_response.json()
            assert len(redactions) == 1

            redaction_file_response = client.get(
                f"/redactions/{redactions[0]['redaction_id']}/file"
            )
            assert redaction_file_response.status_code == 200
            assert "[REDACTED_EMAIL]" in redaction_file_response.text
            assert "jane.patient@example.com" not in redaction_file_response.text

            reports_response = client.get(f"/documents/{document_id}/reports")
            assert reports_response.status_code == 200
            reports = reports_response.json()
            assert len(reports) == 1
            assert reports[0]["total_entities"] >= 2
            assert reports[0]["redaction_completion"] is True
            assert reports[0]["review_completion"] is True

            report_response = client.get(f"/reports/{reports[0]['report_id']}")
            assert report_response.status_code == 200
            report = report_response.json()
            assert report["payload"]["document_id"] == document_id
            assert report["payload"]["total_entities"] >= 2
            assert any(
                entity["entity_type"] == "EMAIL"
                and entity["entity_value"] == "jane.patient@example.com"
                for entity in report["payload"]["entities"]
            )

            report_file_response = client.get(
                f"/reports/{reports[0]['report_id']}/file"
            )
            assert report_file_response.status_code == 200
            assert report_file_response.json()["document_id"] == document_id
            assert any(
                entity["entity_type"] == "EMAIL"
                and entity["entity_value"] == "jane.patient@example.com"
                for entity in report_file_response.json()["entities"]
            )
    finally:
        app.dependency_overrides.clear()


def test_upload_accepts_docx_mime_type(
    db_session,
    tmp_path,
    monkeypatch,
):
    producer = FakeRedisProducer()
    upload_dir = tmp_path / "uploads"
    monkeypatch.chdir(tmp_path)

    def override_get_db():
        yield db_session

    monkeypatch.setattr(StorageService, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(
        "modules.upload.service.RedisProducer",
        lambda redis_client: producer,
    )

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            upload_response = client.post(
                "/upload/",
                files={
                    "file": (
                        "document.docx",
                        b"docx-placeholder-content",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                },
            )

            assert upload_response.status_code == 201
            document_id = upload_response.json()["document"]["document_id"]
            saved_document = db_session.get(Document, document_id)

            assert saved_document.file_type == (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            assert Document.__table__.c.file_type.type.length == 255
    finally:
        app.dependency_overrides.clear()

