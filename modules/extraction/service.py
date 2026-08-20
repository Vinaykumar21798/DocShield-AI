from typing import Optional

from sqlalchemy.orm import Session

from api.schemas.document_status import DocumentStatusResponse
from api.schemas.extracted_text import ExtractedTextResponse
from database.models import Document, OCRResult, ProcessingJob
from database.repositories.document_repository import (
    DocumentRepository,
    document_repository,
)
from database.repositories.ocr_result_repository import (
    OCRResultRepository,
    ocr_result_repository,
)
from database.repositories.processing_job_repository import (
    ProcessingJobRepository,
    processing_job_repository,
)


class ExtractionServiceError(Exception):
    """
    Base exception for extracted text service errors.
    """


class DocumentNotFoundError(ExtractionServiceError):
    """
    Raised when a document cannot be found.
    """


class ExtractedTextNotFoundError(ExtractionServiceError):
    """
    Raised when no OCR result exists for a document.
    """


class ExtractionService:
    """
    Provides read access to document text extraction outputs.
    """

    def __init__(
        self,
        db: Session,
        document_repo: DocumentRepository = document_repository,
        ocr_result_repo: OCRResultRepository = ocr_result_repository,
        processing_job_repo: ProcessingJobRepository = (
            processing_job_repository
        ),
    ):
        self.db = db
        self.document_repository = document_repo
        self.ocr_result_repository = ocr_result_repo
        self.processing_job_repository = processing_job_repo

    def get_extracted_text(
        self,
        document_id: str,
    ) -> ExtractedTextResponse:
        document = self._get_document_or_raise(document_id)
        ocr_result = self._get_latest_ocr_result_or_raise(document_id)
        processing_job = self._get_latest_processing_job(document_id)

        return self._build_extracted_text_response(
            document=document,
            ocr_result=ocr_result,
            processing_job=processing_job,
        )

    def get_processing_status(
        self,
        document_id: str,
    ) -> DocumentStatusResponse:
        document = self._get_document_or_raise(document_id)
        processing_job = self._get_latest_processing_job(document_id)
        ocr_result = self.ocr_result_repository.get_latest_by_document_id(
            self.db,
            document_id,
        )

        return self._build_status_response(
            document=document,
            processing_job=processing_job,
            ocr_result=ocr_result,
        )

    def _get_document_or_raise(
        self,
        document_id: str,
    ) -> Document:
        document = self.document_repository.get_document_by_id(
            self.db,
            document_id,
        )

        if document is None:
            raise DocumentNotFoundError(
                f"Document not found: {document_id}"
            )

        return document

    def _get_latest_processing_job(
        self,
        document_id: str,
    ) -> Optional[ProcessingJob]:
        return self.processing_job_repository.get_latest_job_by_document(
            self.db,
            document_id,
        )

    def _get_latest_ocr_result_or_raise(
        self,
        document_id: str,
    ) -> OCRResult:
        ocr_result = self.ocr_result_repository.get_latest_by_document_id(
            self.db,
            document_id,
        )

        if ocr_result is None:
            raise ExtractedTextNotFoundError(
                "Extracted text not found for document_id="
                f"{document_id}"
            )

        return ocr_result

    @staticmethod
    def _build_extracted_text_response(
        document: Document,
        ocr_result: OCRResult,
        processing_job: Optional[ProcessingJob],
    ) -> ExtractedTextResponse:
        return ExtractedTextResponse(
            document_id=document.id,
            filename=document.filename,
            owner=(
                document.owner.name
                if document.owner is not None
                else document.uploaded_by
            ),
            file_type=document.file_type,
            document_type=document.document_type,
            document_status=document.status,
            processing_status=(
                processing_job.job_status if processing_job else None
            ),
            workflow_stage=(
                processing_job.workflow_stage if processing_job else None
            ),
            last_completed_stage=(
                processing_job.last_completed_stage if processing_job else None
            ),
            ocr_result_id=ocr_result.id,
            extraction_method=ocr_result.extraction_method,
            is_searchable=ocr_result.is_searchable,
            extracted_text=ocr_result.extracted_text,
            extracted_text_path=ocr_result.extracted_text_path,
            structured_output=ocr_result.structured_output,
            page_count=ocr_result.page_count,
            confidence_score=ocr_result.confidence_score,
            processing_time=ocr_result.processing_time,
            created_at=ocr_result.created_at,
            updated_at=ocr_result.updated_at,
        )

    @staticmethod
    def _build_status_response(
        document: Document,
        processing_job: Optional[ProcessingJob],
        ocr_result: Optional[OCRResult],
    ) -> DocumentStatusResponse:
        has_extracted_text = bool(
            ocr_result
            and ocr_result.extracted_text
            and ocr_result.extracted_text.strip()
        )

        return DocumentStatusResponse(
            document_id=document.id,
            filename=document.filename,
            file_type=document.file_type,
            document_type=document.document_type,
            document_status=document.status,
            processing_job_id=(processing_job.id if processing_job else None),
            processing_status=(
                processing_job.job_status if processing_job else None
            ),
            workflow_stage=(
                processing_job.workflow_stage if processing_job else None
            ),
            last_completed_stage=(
                processing_job.last_completed_stage if processing_job else None
            ),
            queue_name=(processing_job.queue_name if processing_job else None),
            worker_id=(processing_job.worker_id if processing_job else None),
            retry_count=(processing_job.retry_count if processing_job else 0),
            error_message=(
                processing_job.error_message if processing_job else None
            ),
            started_at=(processing_job.started_at if processing_job else None),
            completed_at=(
                processing_job.completed_at if processing_job else None
            ),
            has_extracted_text=has_extracted_text,
            ocr_result_id=(ocr_result.id if ocr_result else None),
            extraction_method=(
                ocr_result.extraction_method if ocr_result else None
            ),
            is_searchable=(ocr_result.is_searchable if ocr_result else None),
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
