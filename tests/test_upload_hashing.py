import asyncio
import hashlib
import io

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from database.models import Document, ProcessingJob
from database.repositories.document_repository import DocumentRepository
from modules.upload.hashing import compute_sha256, stream_file_sha256
from modules.upload.service import UploadService
from modules.upload.storage import StorageService


class FakeRedisProducer:
    def __init__(self):
        self.published = []

    def publish(self, job):
        self.published.append(job)
        return True


def make_upload(filename, data, content_type="text/plain"):
    return UploadFile(
        file=io.BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.fixture()
def upload_service(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "modules.upload.service.RedisProducer",
        lambda redis_client: FakeRedisProducer(),
    )
    storage_root = tmp_path / "storage"
    monkeypatch.setattr(StorageService, "STORAGE_DIR", storage_root)
    monkeypatch.setattr(StorageService, "RUNS_DIR", storage_root / "runs")
    monkeypatch.setattr(
        StorageService, "UPLOAD_DIR", storage_root / "uploads"
    )
    return UploadService(db_session)


def test_sha256_deterministic():
    data = b"invoice content example 123"
    assert compute_sha256(data) == compute_sha256(data)
    assert compute_sha256(data) == hashlib.sha256(data).hexdigest()


def test_sha256_changes_with_content():
    assert compute_sha256(b"original") != compute_sha256(b"modified")


def test_stream_sha256_matches_standard():
    data = b"x" * (2 * 1024 * 1024 + 123)
    expected = hashlib.sha256(data).hexdigest()
    assert stream_file_sha256(io.BytesIO(data)) == expected
    assert stream_file_sha256(io.BytesIO(data), chunk_size=7) == expected


def test_get_document_by_content_hash(db_session, upload_service):
    content = b"hello world hash lookup"
    expected = compute_sha256(content)
    _, docs = asyncio.run(
        upload_service.upload_documents([make_upload("a.txt", content)])
    )
    assert docs[0].content_hash == expected

    found = DocumentRepository().get_document_by_content_hash(
        db_session, expected
    )
    assert found is not None
    assert found.id == docs[0].id

    assert (
        DocumentRepository().get_document_by_content_hash(
            db_session, "0" * 64
        )
        is None
    )
    assert DocumentRepository().get_document_by_content_hash(
        db_session, None
    ) is None


def test_identical_files_detected_as_duplicate(db_session, upload_service):
    content = b"same content abc 123"
    _, first = asyncio.run(
        upload_service.upload_documents([make_upload("a.txt", content)])
    )
    _, second = asyncio.run(
        upload_service.upload_documents([make_upload("b.txt", content)])
    )

    assert second[0].id == first[0].id
    assert getattr(second[0], "_upload_is_duplicate", False) is True
    assert db_session.query(Document).count() == 1
    assert (
        db_session.query(ProcessingJob)
        .filter(ProcessingJob.document_id == first[0].id)
        .count()
        == 1
    )


def test_same_filename_different_content_not_duplicate(upload_service):
    c1 = b"alpha content"
    c2 = b"beta content different"
    _, first = asyncio.run(
        upload_service.upload_documents([make_upload("a.txt", c1)])
    )
    _, second = asyncio.run(
        upload_service.upload_documents([make_upload("a.txt", c2)])
    )

    assert second[0].id != first[0].id
    assert getattr(second[0], "_upload_is_duplicate", False) is False


def test_different_filename_identical_content_is_duplicate(upload_service):
    content = b"same bytes across names"
    _, first = asyncio.run(
        upload_service.upload_documents([make_upload("one.txt", content)])
    )
    _, second = asyncio.run(
        upload_service.upload_documents([make_upload("two.txt", content)])
    )

    assert second[0].id == first[0].id
    assert getattr(second[0], "_upload_is_duplicate", False) is True


def test_modified_content_not_duplicate(upload_service):
    c1 = b"v1 original"
    c2 = b"v1 original plus extra"
    _, first = asyncio.run(
        upload_service.upload_documents([make_upload("a.txt", c1)])
    )
    _, second = asyncio.run(
        upload_service.upload_documents([make_upload("b.txt", c2)])
    )

    assert second[0].id != first[0].id
    assert getattr(second[0], "_upload_is_duplicate", False) is False


def test_duplicate_upload_skips_ocr_detection(db_session, upload_service):
    content = b"patient record with sensitive pii content"
    _, first = asyncio.run(
        upload_service.upload_documents([make_upload("a.txt", content)])
    )
    jobs_before = db_session.query(ProcessingJob).count()

    _, second = asyncio.run(
        upload_service.upload_documents([make_upload("a.txt", content)])
    )

    assert second[0].id == first[0].id
    assert getattr(second[0], "_upload_is_duplicate", False) is True
    assert db_session.query(ProcessingJob).count() == jobs_before


def test_bulk_upload_mixed_duplicates(upload_service, db_session):
    content_a = b"bulk duplicate content a"
    content_b = b"bulk unique content b"
    _, first = asyncio.run(
        upload_service.upload_documents([make_upload("a.txt", content_a)])
    )

    _, docs = asyncio.run(
        upload_service.upload_documents(
            [
                make_upload("a2.txt", content_a),
                make_upload("b.txt", content_b),
            ]
        )
    )

    ids = [d.id for d in docs]
    assert len(set(ids)) == 2
    duplicate_flags = [
        getattr(d, "_upload_is_duplicate", False) for d in docs
    ]
    assert duplicate_flags.count(True) == 1
    assert duplicate_flags.count(False) == 1
    assert docs[0].id == first[0].id
    assert docs[1].id != first[0].id
