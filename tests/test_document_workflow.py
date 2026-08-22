import json
from uuid import uuid4

import pytest

from database.models import (
    ConfidenceScore,
    Document,
    Entity,
    OCRResult,
    ProcessingJob,
    Redaction,
    Report,
    Run,
)
from modules.classification.service import DocumentType
from modules.detection.models.detection_result import DetectionResult
from modules.extraction.native import TextExtractionResult
from modules.extraction.ocr import OCRDecision, OCREngine
from modules.extraction.service import ExtractionService
from modules.upload.storage import StorageService
from orchestration.workflow import DocumentProcessingWorkflow
from types import SimpleNamespace


def create_document_with_job(
    db_session,
    storage_path,
    filename="invoice.txt",
    file_type="text/plain",
    retry_count=0,
):
    run = Run(
        id=str(uuid4()),
        run_id=f"RUN-{uuid4().hex[:6].upper()}",
        status="QUEUED",
        total_files=1,
    )
    document = Document(
        id=str(uuid4()),
        filename=filename,
        stored_filename=f"{uuid4()}.txt",
        file_type=file_type,
        file_size=100,
        storage_path=str(storage_path),
        status="PENDING",
        run_id=run.id,
    )
    processing_job = ProcessingJob(
        id=str(uuid4()),
        document_id=document.id,
        job_status="PENDING",
        workflow_stage="UPLOAD",
        queue_name="document_processing",
        retry_count=retry_count,
    )

    db_session.add(run)
    db_session.add(document)
    db_session.add(processing_job)
    db_session.commit()

    return document, processing_job


def test_workflow_completes_native_text_document(
    db_session,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    document_path = tmp_path / "invoice.txt"
    document_text = (
        "Invoice Number INV-1001\n"
        "Bill To: Jane Patient\n"
        "Amount Due: 125.00\n"
        "Email: jane.patient@example.com\n"
        "Payment terms: due on receipt."
    )
    document_path.write_text(document_text, encoding="utf-8")
    document, _ = create_document_with_job(db_session, document_path)

    state = DocumentProcessingWorkflow(db_session).execute(document.id)

    saved_document = db_session.get(Document, document.id)
    saved_job = (
        db_session.query(ProcessingJob)
        .filter(ProcessingJob.document_id == document.id)
        .one()
    )
    ocr_result = (
        db_session.query(OCRResult)
        .filter(OCRResult.document_id == document.id)
        .one()
    )

    assert state.status == "COMPLETED"
    assert saved_document.status == "COMPLETED"
    assert saved_document.document_type == DocumentType.INVOICE.value
    assert saved_job.job_status == "COMPLETED"
    assert saved_job.workflow_stage == "COMPLETE_WORKFLOW"
    assert saved_job.last_completed_stage == "COMPLETE_WORKFLOW"
    assert ocr_result.extraction_method == OCREngine.NATIVE_TEXT.value
    assert ocr_result.is_searchable is True
    assert "Invoice Number INV-1001" in ocr_result.extracted_text
    assert ocr_result.confidence_score > 0

    expected_text_path = StorageService.extracted_path(
        document.run_id,
        document.id,
    )
    assert ocr_result.extracted_text_path == expected_text_path.as_posix()
    assert state.extracted_text_path == expected_text_path.as_posix()

    extracted_text_file = tmp_path / expected_text_path
    assert extracted_text_file.exists()
    assert extracted_text_file.read_text(encoding="utf-8") == (
        ocr_result.extracted_text
    )

    extraction_service = ExtractionService(db_session)
    status_response = extraction_service.get_processing_status(document.id)
    text_response = extraction_service.get_extracted_text(document.id)

    assert status_response.has_extracted_text is True
    assert status_response.processing_status == "COMPLETED"
    assert text_response.extracted_text == ocr_result.extracted_text

    entities = (
        db_session.query(Entity)
        .filter(Entity.document_id == document.id)
        .all()
    )
    confidence_scores = db_session.query(ConfidenceScore).all()
    redaction = (
        db_session.query(Redaction)
        .filter(Redaction.document_id == document.id)
        .one()
    )
    report = (
        db_session.query(Report)
        .filter(Report.document_id == document.id)
        .one()
    )

    assert any(entity.entity_type == "EMAIL" for entity in entities)
    assert len(confidence_scores) == len(entities)
    assert redaction.redaction_type == "PII_PHI_TEXT_REDACTION"
    assert report.total_entities == len(entities)
    assert report.total_redactions == len(entities)

    redacted_text_file = tmp_path / redaction.redacted_file_path
    report_file = tmp_path / report.report_path
    assert redacted_text_file.exists()
    assert report_file.exists()
    report_payload = json.loads(report_file.read_text(encoding="utf-8"))
    assert any(
        entity["entity_type"] == "EMAIL"
        and entity["entity_value"] == "jane.patient@example.com"
        for entity in report_payload["entities"]
    )
    report_order = [
        (
            int(entity["page_number"]),
            entity["start_char"],
            entity["end_char"],
        )
        for entity in report_payload["entities"]
    ]
    assert report_order == sorted(report_order)

    assert "[REDACTED_EMAIL]" in redacted_text_file.read_text(
        encoding="utf-8",
    )


def test_workflow_marks_document_and_job_failed_when_file_is_missing(
    db_session,
    tmp_path,
):
    missing_path = tmp_path / "missing.txt"
    document, _ = create_document_with_job(db_session, missing_path)

    with pytest.raises(Exception, match="Stored document file not found"):
        DocumentProcessingWorkflow(db_session).execute(document.id)

    saved_document = db_session.get(Document, document.id)
    saved_job = (
        db_session.query(ProcessingJob)
        .filter(ProcessingJob.document_id == document.id)
        .one()
    )
    ocr_results = (
        db_session.query(OCRResult)
        .filter(OCRResult.document_id == document.id)
        .all()
    )

    assert saved_document.status == "FAILED"
    assert saved_job.job_status == "FAILED"
    assert saved_job.workflow_stage == "OCR_DECISION"
    assert saved_job.last_completed_stage == "DOCUMENT_CLASSIFICATION"
    assert "Stored document file not found" in saved_job.error_message
    assert saved_job.completed_at is not None
    assert ocr_results == []


class FakePaddleExtractor:
    def __init__(self, structured_output):
        self.structured_output = structured_output

    def extract(self, document):
        return TextExtractionResult(
            extracted_text="Invoice Number INV-3003\nTotal 10.00",
            page_count=1,
            confidence_score=0.90,
            processing_time=0.01,
            structured_output=self.structured_output,
        )


class FakeMixedPDFDecisionEngine:
    def decide(self, document):
        return OCRDecision(
            engine=OCREngine.MIXED_PDF,
            is_searchable=False,
            reason="Synthetic mixed PDF for workflow test.",
        )


class FakeMixedPDFExtractor:
    def __init__(self):
        self.document = None

    def extract(self, document):
        self.document = document
        return TextExtractionResult(
            extracted_text=(
                "Invoice Number INV-4004\n"
                "Email: jane.patient@example.com\n"
            ),
            page_count=2,
            confidence_score=0.92,
            processing_time=0.02,
            structured_output={
                "engine": "MIXED_PDF",
                "searchable_pages": [1],
                "ocr_pages": [2],
                "pages": [],
            },
        )


class FailingTextExtractor:
    def extract(self, document):
        raise AssertionError("OCR extraction should not run during resume")


class FakeDetectionService:
    last_llm_candidate_audit = {
        "accepted": [
            {
                "entity_value": "Synthetic Candidate",
                "entity_type": "PERSON",
                "decision": "CONFIRM",
                "confidence": 0.91,
                "detector": "Gemma4:e4b",
                "reasoning": "Synthetic context supports the candidate.",
            }
        ],
        "rejected": [],
    }

    def detect(self, text, document_type=None):
        self.document_type = document_type
        email = "jane.patient@example.com"
        start = text.index(email)
        return [
            DetectionResult(
                entity_type="EMAIL",
                entity_value=email,
                privacy_category="PII",
                confidence_score=0.95,
                start_char=start,
                end_char=start + len(email),
                page_number=1,
                detector="fake-detector",
            )
        ]


def test_workflow_persists_structured_ocr_output(
    db_session,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    image_path = tmp_path / "invoice.png"
    image_path.write_bytes(b"fake image bytes")
    document, _ = create_document_with_job(
        db_session,
        image_path,
        filename="invoice.png",
        file_type="image/png",
    )
    structured_output = {
        "schema_version": "layout_ocr_v1",
        "engine": "PADDLEOCR",
        "pages": [
            {
                "page_number": 1,
                "layout_source": "ocr_bounding_boxes",
                "blocks": [
                    {
                        "block_type": "text",
                        "text": "Invoice Number INV-3003",
                    }
                ],
            }
        ],
    }

    DocumentProcessingWorkflow(
        db_session,
        paddle_ocr_extractor=FakePaddleExtractor(structured_output),
    ).execute(document.id)

    ocr_result = (
        db_session.query(OCRResult)
        .filter(OCRResult.document_id == document.id)
        .one()
    )
    text_response = ExtractionService(db_session).get_extracted_text(
        document.id,
    )

    assert ocr_result.extraction_method == OCREngine.PADDLEOCR.value
    assert ocr_result.structured_output == structured_output
    assert text_response.structured_output == structured_output


def test_workflow_resumes_from_stored_ocr_checkpoint(
    db_session,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    missing_path = tmp_path / "missing.txt"
    document, processing_job = create_document_with_job(
        db_session,
        missing_path,
    )
    document.document_type = DocumentType.INVOICE.value
    processing_job.job_status = "PENDING"
    processing_job.workflow_stage = "RETRY_QUEUED"
    processing_job.last_completed_stage = "STORE_OCR_RESULTS"
    processing_job.retry_count = 1

    text = (
        "Invoice Number INV-1001\n"
        "Email: jane.patient@example.com\n"
    )
    db_session.add(
        OCRResult(
            document_id=document.id,
            extraction_method=OCREngine.NATIVE_TEXT.value,
            is_searchable=True,
            extracted_text=text,
            extracted_text_path=(
                StorageService.extracted_path(
                    document.run_id,
                    document.id,
                )
            ).as_posix(),
            page_count=1,
            confidence_score=0.99,
            processing_time=0.01,
        )
    )
    db_session.commit()

    state = DocumentProcessingWorkflow(
        db_session,
        native_text_extractor=FailingTextExtractor(),
        detection_service=FakeDetectionService(),
    ).execute(document.id)

    saved_job = (
        db_session.query(ProcessingJob)
        .filter(ProcessingJob.document_id == document.id)
        .one()
    )
    ocr_result_count = (
        db_session.query(OCRResult)
        .filter(OCRResult.document_id == document.id)
        .count()
    )

    assert state.status == "COMPLETED"
    assert saved_job.job_status == "COMPLETED"
    assert saved_job.workflow_stage == "COMPLETE_WORKFLOW"
    assert saved_job.last_completed_stage == "COMPLETE_WORKFLOW"
    assert ocr_result_count == 1
    report = (
        db_session.query(Report)
        .filter(Report.document_id == document.id)
        .one()
    )
    assert report.llm_candidate_audit == (
        FakeDetectionService.last_llm_candidate_audit
    )

    redacted_text_file = tmp_path / state.redacted_file_path
    assert redacted_text_file.exists()
    assert "[REDACTED_EMAIL]" in redacted_text_file.read_text(
        encoding="utf-8",
    )


def test_workflow_uses_mixed_pdf_extractor(
    db_session,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    pdf_path = tmp_path / "mixed.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    document, _ = create_document_with_job(
        db_session,
        pdf_path,
        filename="mixed.pdf",
        file_type="application/pdf",
    )
    fake_mixed_extractor = FakeMixedPDFExtractor()
    fake_detection = FakeDetectionService()

    state = DocumentProcessingWorkflow(
        db_session,
        ocr_decision_engine=FakeMixedPDFDecisionEngine(),
        mixed_pdf_extractor=fake_mixed_extractor,
        detection_service=fake_detection,
    ).execute(document.id)

    ocr_result = (
        db_session.query(OCRResult)
        .filter(OCRResult.document_id == document.id)
        .one()
    )

    assert state.status == "COMPLETED"
    assert fake_mixed_extractor.document.id == document.id
    assert ocr_result.extraction_method == OCREngine.MIXED_PDF.value
    assert ocr_result.is_searchable is False
    assert ocr_result.page_count == 2
    assert ocr_result.structured_output["engine"] == "MIXED_PDF"
    assert ocr_result.structured_output["searchable_pages"] == [1]
    assert ocr_result.structured_output["ocr_pages"] == [2]
    assert fake_detection.document_type == DocumentType.INVOICE.value


def test_post_redaction_verification_passes_when_all_values_are_removed():
    source = "Email: synthetic.user@example.test"
    value = "synthetic.user@example.test"
    start = source.index(value)
    entity = SimpleNamespace(
        entity_type="EMAIL",
        entity_value=value,
        start_char=start,
        end_char=start + len(value),
    )

    redacted = DocumentProcessingWorkflow._apply_redactions(source, [entity])

    assert DocumentProcessingWorkflow._redaction_verification_issues(
        source,
        redacted,
        [entity],
    ) == []


def test_post_redaction_verification_blocks_an_unredacted_duplicate():
    value = "synthetic.user@example.test"
    source = f"Primary: {value}\nBackup: {value}"
    start = source.index(value)
    entity = SimpleNamespace(
        entity_type="EMAIL",
        entity_value=value,
        start_char=start,
        end_char=start + len(value),
    )

    redacted = DocumentProcessingWorkflow._apply_redactions(source, [entity])
    issues = DocumentProcessingWorkflow._redaction_verification_issues(
        source,
        redacted,
        [entity],
    )

    assert "DETECTED_VALUE_REMAINS" in issues
    assert "DETERMINISTIC_PII_REMAINS" in issues


def test_occurrence_expansion_redacts_all_three_occurrences():
    value = "HealthGuard Insurance Company"
    source = f"Header: {value}\nBody: {value}\nFooter: {value}"
    start = source.index(value)
    initial_det = DetectionResult(
        entity_type="INSURANCE_PROVIDER",
        entity_value=value,
        start_char=start,
        end_char=start + len(value),
        confidence_score=0.95,
        detector="presidio",
        privacy_category="PHI",
    )

    expanded = DocumentProcessingWorkflow._expand_entity_occurrences(source, [initial_det])
    assert len(expanded) == 3
    spans = [(d.start_char, d.end_char) for d in expanded]
    assert len(set(spans)) == 3

    redacted = DocumentProcessingWorkflow._apply_redactions(source, expanded)
    assert value not in redacted
    issues = DocumentProcessingWorkflow._redaction_verification_issues(source, redacted, expanded)
    assert "DETECTED_VALUE_REMAINS" not in issues


def test_occurrence_expansion_preserves_span_deduplication():
    value = "123-45-6789"
    source = f"First: {value}\nSecond: {value}"
    start1 = source.find(value)

    det1 = DetectionResult(
        entity_type="SSN",
        entity_value=value,
        start_char=start1,
        end_char=start1 + len(value),
        confidence_score=1.0,
        detector="Regex",
    )
    det2 = DetectionResult(
        entity_type="SSN",
        entity_value=value,
        start_char=start1,
        end_char=start1 + len(value),
        confidence_score=0.85,
        detector="presidio",
    )

    expanded = DocumentProcessingWorkflow._expand_entity_occurrences(source, [det1, det2])
    assert len(expanded) == 3
    spans = [(d.start_char, d.end_char) for d in expanded]
    assert len(set(spans)) == 2


def test_occurrence_expansion_avoids_partial_word_matches():
    source = "Patient Med requested Medical evaluation from Dr. Johnson (John)."
    med_det = DetectionResult(
        entity_type="MEDICATION",
        entity_value="Med",
        start_char=source.find("Med "),
        end_char=source.find("Med ") + 3,
        confidence_score=0.90,
        detector="medspacy",
    )
    john_det = DetectionResult(
        entity_type="PERSON",
        entity_value="John",
        start_char=source.find("John)"),
        end_char=source.find("John)") + 4,
        confidence_score=0.88,
        detector="presidio",
    )

    expanded = DocumentProcessingWorkflow._expand_entity_occurrences(source, [med_det, john_det])
    expanded_values = [d.entity_value for d in expanded]
    assert "Medical" not in expanded_values
    assert "Johnson" not in expanded_values
    assert all(d.entity_value in {"Med", "John"} for d in expanded)

