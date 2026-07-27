from pathlib import Path

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
                        b"Invoice Number INV-2002\nBill To: Jane Patient\nAmount Due: 75.00",
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

            expected_text_path = (
                Path("storage/extracted_text") / f"{document_id}.txt"
            )
            assert text_response.json()["extracted_text_path"] == (
                expected_text_path.as_posix()
            )
            assert (tmp_path / expected_text_path).read_text(
                encoding="utf-8"
            ) == text_response.json()["extracted_text"]
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