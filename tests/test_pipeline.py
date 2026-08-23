import datetime
import uuid
from database.models.document import Document
from database.models.entity import Entity
from database.models.confidence import ConfidenceScore
from database.models.report import Report
from database.models.review import Review

from database.repositories.entity_repository import EntityRepository
from database.repositories.confidence_repository import ConfidenceRepository
from database.repositories.report_repository import ReportRepository
from database.repositories.review_repository import ReviewRepository
from modules.detection.service import DetectionService


def test_pipeline_integration(db_session):
    sample_text = """Invoice no: 12847181
Date of issue: 03/03/2012
Seller: Fitzpatrick and Sons    Client: Duncan PLC
Tax Id: 998-99-5253    Tax Id: 911-82-7132
IBAN: GB92PBPQ73499358975916
Total: $ 6 860,45
"""
    service = DetectionService()
    results = service.detect(sample_text)
    assert len(results) > 0

    doc_id = str(uuid.uuid4())
    db = db_session
    try:
        doc = Document(
            id=doc_id,
            filename="test_invoice.txt",
            stored_filename=f"{doc_id}.txt",
            file_type="text/plain",
            file_size=len(sample_text),
            storage_path=f"storage/uploads/{doc_id}.txt",
            document_type="financial",
            status="UPLOADED",
        )
        db.add(doc)
        db.commit()

        entity_repo = EntityRepository(db)
        confidence_repo = ConfidenceRepository(db)
        report_repo = ReportRepository(db)
        review_repo = ReviewRepository(db)

        for item in results:
            db_entity = Entity(
                id=str(uuid.uuid4()),
                document_id=doc_id,
                ocr_result_id="ocr-poc-001",
                entity_type=item.entity_type,
                entity_value=item.entity_value,
                page_number=str(item.page_number),
                confidence_score=item.confidence_score,
                detector=item.detector,
                start_char=item.start,
                end_char=item.end,
                privacy_category=item.privacy_category,
                entity_owner=item.detector,
                canonical_type=item.entity_type,
                processing_stage="DETECTION",
                is_review_required=(item.confidence_score < 0.8),
                is_redacted=True,
                final_confidence=item.confidence_score
            )
            entity_repo.create(db_entity)

            db_score = ConfidenceScore(
                id=str(uuid.uuid4()),
                entity_id=db_entity.id,
                confidence_score=item.confidence_score,
                confidence_level="HIGH" if item.confidence_score >= 0.8 else "LOW",
                threshold=0.8
            )
            confidence_repo.create(db_score)

            if item.confidence_score < 0.8:
                db_review = Review(
                    id=str(uuid.uuid4()),
                    entity_id=db_entity.id,
                    reviewer="SystemAutoReviewer",
                    review_status="PENDING",
                    review_comment="Flagged for manual review due to low confidence score.",
                    reviewed_at=datetime.datetime.now(datetime.timezone.utc)
                )
                review_repo.create(db_review)

        total_pii = sum(1 for item in results if item.privacy_category == "PII")
        total_phi = sum(1 for item in results if item.privacy_category == "PHI")
        db_report = Report(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            report_type="AUDIT",
            total_entities=len(results),
            total_redactions=len(results),
            report_path=f"/reports/{doc_id}_audit_report.json",
            generated_by="SystemPipeline",
            processing_duration_ms=180,
            detectors_used=",".join(list(set(item.detector for item in results))),
            gemma_invoked=False,
            total_pii=total_pii,
            total_phi=total_phi,
            review_completion=True,
            redaction_completion=True
        )
        report_repo.create(db_report)
        assert report_repo.get_by_document_id(doc_id) is not None
    finally:
        db.rollback()
