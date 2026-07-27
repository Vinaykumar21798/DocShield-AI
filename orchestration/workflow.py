import logging
from pathlib import Path
from typing import Callable, Dict, Optional

from sqlalchemy.orm import Session

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
from modules.classification.service import (
    ClassificationResult,
    DocumentClassificationService,
    DocumentType,
    document_classification_service,
)
from modules.extraction.evaluation import (
    OCRConfidenceEvaluator,
    ocr_confidence_evaluator,
)
from modules.extraction.native import (
    NativePDFExtractionService,
    NativeTextExtractionService,
    TextExtractionResult,
)
from modules.extraction.ocr import OCRDecisionEngine, OCREngine
from modules.extraction.paddle import PaddleOCRExtractionService
from orchestration.execution_plan import WorkflowStep
from orchestration.planner import WorkflowPlanner
from orchestration.state import WorkflowState


DOCUMENT_STATUS_PROCESSING = "PROCESSING"
DOCUMENT_STATUS_COMPLETED = "COMPLETED"
DOCUMENT_STATUS_FAILED = "FAILED"

JOB_STATUS_PROCESSING = "PROCESSING"

DOCUMENT_TYPE_UNKNOWN = DocumentType.UNKNOWN.value
OCR_ENGINE_PLACEHOLDER = "PLACEHOLDER"
OCR_PLACEHOLDER_TEXT = "TODO - OCR not implemented"
DEFAULT_WORKER_ID = "document-processing-worker"
EXTRACTED_TEXT_DIR = Path("storage/extracted_text")


class DocumentWorkflowError(Exception):
    """
    Base exception for document processing workflow failures.
    """


class DocumentNotFoundError(DocumentWorkflowError):
    """
    Raised when a workflow cannot find the target document.
    """


class ProcessingJobNotFoundError(DocumentWorkflowError):
    """
    Raised when a workflow cannot find a processing job for the document.
    """


class DocumentProcessingWorkflow:
    """
    Coordinates document processing steps using existing repositories.
    """

    def __init__(
        self,
        db: Session,
        document_repo: DocumentRepository = document_repository,
        processing_job_repo: ProcessingJobRepository = (
            processing_job_repository
        ),
        ocr_result_repo: OCRResultRepository = ocr_result_repository,
        ocr_decision_engine: Optional[OCRDecisionEngine] = None,
        native_pdf_extractor: Optional[NativePDFExtractionService] = None,
        native_text_extractor: Optional[NativeTextExtractionService] = None,
        paddle_ocr_extractor: Optional[PaddleOCRExtractionService] = None,
        classification_service: Optional[
            DocumentClassificationService
        ] = None,
        confidence_evaluator: Optional[OCRConfidenceEvaluator] = None,
        planner: Optional[WorkflowPlanner] = None,
        worker_id: str = DEFAULT_WORKER_ID,
        logger: Optional[logging.Logger] = None,
    ):
        self.db = db
        self.document_repository = document_repo
        self.processing_job_repository = processing_job_repo
        self.ocr_result_repository = ocr_result_repo
        self.classification_service = (
            classification_service or document_classification_service
        )
        self.confidence_evaluator = (
            confidence_evaluator or ocr_confidence_evaluator
        )
        self.ocr_decision_engine = (
            ocr_decision_engine or OCRDecisionEngine()
        )
        self.native_pdf_extractor = (
            native_pdf_extractor or NativePDFExtractionService()
        )
        self.native_text_extractor = (
            native_text_extractor or NativeTextExtractionService()
        )
        self.paddle_ocr_extractor = (
            paddle_ocr_extractor or PaddleOCRExtractionService()
        )
        self.planner = planner or WorkflowPlanner()
        self.worker_id = worker_id
        self.logger = logger or logging.getLogger(__name__)

        self._step_handlers: Dict[
            WorkflowStep,
            Callable[[WorkflowState], None],
        ] = {
            WorkflowStep.LOAD_DOCUMENT: self._load_document_context,
            WorkflowStep.UPDATE_PROCESSING_STATUS: (
                self._update_processing_status
            ),
            WorkflowStep.DOCUMENT_CLASSIFICATION: (
                self._classify_document
            ),
            WorkflowStep.OCR_DECISION: self._decide_ocr_engine,
            WorkflowStep.OCR_EXECUTION: self._execute_ocr,
            WorkflowStep.STORE_OCR_RESULTS: self._store_ocr_results,
            WorkflowStep.COMPLETE_WORKFLOW: self._complete_workflow,
        }

    def execute(self, document_id: str) -> WorkflowState:
        state = WorkflowState(document_id=str(document_id))
        plan = self.planner.create_plan()

        self.logger.info(
            "Starting document processing workflow for document_id=%s",
            state.document_id,
        )

        try:
            for step in plan.steps:
                self._run_step(state, step)

            self.logger.info(
                "Completed document processing workflow for document_id=%s",
                state.document_id,
            )
            return state

        except Exception as exc:
            self._handle_failure(state, exc)
            raise

    def _run_step(
        self,
        state: WorkflowState,
        step: WorkflowStep,
    ) -> None:
        self.logger.info(
            "Starting workflow step=%s document_id=%s",
            step.value,
            state.document_id,
        )

        if state.processing_job is not None:
            self._update_workflow_stage(state.processing_job, step)

        handler = self._step_handlers[step]
        handler(state)

        if (
            step == WorkflowStep.LOAD_DOCUMENT
            and state.processing_job is not None
        ):
            self._update_workflow_stage(state.processing_job, step)

        self.logger.info(
            "Completed workflow step=%s document_id=%s",
            step.value,
            state.document_id,
        )

    def _load_document_context(self, state: WorkflowState) -> None:
        document = self.document_repository.get_document_by_id(
            self.db,
            state.document_id,
        )
        processing_job = (
            self.processing_job_repository.get_latest_job_by_document(
                self.db,
                state.document_id,
            )
        )

        if document is None:
            raise DocumentNotFoundError(
                f"Document not found: {state.document_id}"
            )

        if processing_job is None:
            raise ProcessingJobNotFoundError(
                "Processing job not found for document_id="
                f"{state.document_id}"
            )

        state.document = document
        state.processing_job = processing_job
        state.status = document.status
        state.document_type = document.document_type

    def _update_processing_status(self, state: WorkflowState) -> None:
        document = self._require_document(state)
        processing_job = self._require_processing_job(state)

        state.document = self.document_repository.update_status(
            self.db,
            document,
            DOCUMENT_STATUS_PROCESSING,
        )
        state.processing_job = self.processing_job_repository.assign_worker(
            self.db,
            processing_job,
            self.worker_id,
        )
        state.processing_job = (
            self.processing_job_repository.update_job_status(
                self.db,
                state.processing_job,
                JOB_STATUS_PROCESSING,
            )
        )
        state.status = DOCUMENT_STATUS_PROCESSING

    def _classify_document(self, state: WorkflowState) -> None:
        document = self._require_document(state)
        classification = self.classification_service.classify(document)

        self._save_classification_result(
            state,
            classification,
            source="metadata",
        )

    def _decide_ocr_engine(self, state: WorkflowState) -> None:
        document = self._require_document(state)
        decision = self.ocr_decision_engine.decide(document)
        state.ocr_engine = decision.engine.value
        state.is_searchable = decision.is_searchable

        self.logger.info(
            "OCR decision completed for document_id=%s engine=%s "
            "is_searchable=%s reason=%s",
            state.document_id,
            decision.engine.value,
            decision.is_searchable,
            decision.reason,
        )

    def _execute_ocr(self, state: WorkflowState) -> None:
        document = self._require_document(state)
        ocr_engine = state.ocr_engine or OCR_ENGINE_PLACEHOLDER

        if ocr_engine == OCREngine.NATIVE_PDF.value:
            extraction_result = self.native_pdf_extractor.extract(document)
            self._apply_extraction_result(state, extraction_result)
            self._evaluate_ocr_confidence(state)
            self._refine_document_classification(state)
            return

        if ocr_engine == OCREngine.NATIVE_TEXT.value:
            extraction_result = self.native_text_extractor.extract(document)
            self._apply_extraction_result(state, extraction_result)
            self._evaluate_ocr_confidence(state)
            self._refine_document_classification(state)
            return

        if ocr_engine == OCREngine.PADDLEOCR.value:
            extraction_result = self.paddle_ocr_extractor.extract(document)
            self._apply_extraction_result(state, extraction_result)
            self._evaluate_ocr_confidence(state)
            self._refine_document_classification(state)
            return

        state.extracted_text = self._ocr_execution_placeholder(
            document,
            ocr_engine,
        )
        self._evaluate_ocr_confidence(state)
        self._refine_document_classification(state)

    def _store_ocr_results(self, state: WorkflowState) -> None:
        document = self._require_document(state)

        extracted_text = state.extracted_text or OCR_PLACEHOLDER_TEXT
        extraction_method = state.ocr_engine or OCR_ENGINE_PLACEHOLDER
        state.extracted_text_path = self._save_extracted_text_file(
            document.id,
            extracted_text,
        )

        ocr_result = OCRResult(
            document_id=document.id,
            extraction_method=extraction_method,
            is_searchable=self._get_searchable_status(
                state,
                extraction_method,
            ),
            extracted_text=extracted_text,
            extracted_text_path=state.extracted_text_path,
            page_count=state.page_count,
            confidence_score=state.confidence_score,
            processing_time=state.processing_time,
        )

        self.ocr_result_repository.create_result(
            self.db,
            ocr_result,
        )
        state.extracted_text = extracted_text

    @staticmethod
    def _save_extracted_text_file(
        document_id: str,
        extracted_text: str,
    ) -> str:
        text_path = EXTRACTED_TEXT_DIR / f"{document_id}.txt"
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(extracted_text, encoding="utf-8")
        return text_path.as_posix()

    def _complete_workflow(self, state: WorkflowState) -> None:
        document = self._require_document(state)
        processing_job = self._require_processing_job(state)

        state.document = self.document_repository.update_status(
            self.db,
            document,
            DOCUMENT_STATUS_COMPLETED,
        )
        state.processing_job = self.processing_job_repository.mark_completed(
            self.db,
            processing_job,
        )
        state.status = DOCUMENT_STATUS_COMPLETED

    def _handle_failure(
        self,
        state: WorkflowState,
        exc: Exception,
    ) -> None:
        error_message = str(exc)
        state.error = error_message
        state.status = DOCUMENT_STATUS_FAILED

        self.logger.exception(
            "Document processing workflow failed for document_id=%s",
            state.document_id,
        )

        try:
            self.db.rollback()
        except Exception:
            self.logger.exception(
                "Failed to rollback workflow transaction for document_id=%s",
                state.document_id,
            )

        if state.processing_job is None:
            state.processing_job = (
                self.processing_job_repository.get_latest_job_by_document(
                    self.db,
                    state.document_id,
                )
            )

        if state.processing_job is not None:
            state.processing_job = self.processing_job_repository.mark_failed(
                self.db,
                state.processing_job,
                error_message,
            )

        if state.document is None:
            state.document = self.document_repository.get_document_by_id(
                self.db,
                state.document_id,
            )

        if state.document is not None:
            state.document = self.document_repository.update_status(
                self.db,
                state.document,
                DOCUMENT_STATUS_FAILED,
            )

    def _update_workflow_stage(
        self,
        processing_job: ProcessingJob,
        step: WorkflowStep,
    ) -> None:
        self.processing_job_repository.update_workflow_stage(
            self.db,
            processing_job,
            step.value,
        )

    def _refine_document_classification(
        self,
        state: WorkflowState,
    ) -> None:
        if not state.extracted_text:
            return

        document = self._require_document(state)
        classification = self.classification_service.classify(
            document,
            state.extracted_text,
        )
        current_type = (
            state.document_type
            or document.document_type
            or DOCUMENT_TYPE_UNKNOWN
        )

        if (
            classification.document_type == DOCUMENT_TYPE_UNKNOWN
            and current_type != DOCUMENT_TYPE_UNKNOWN
        ):
            self.logger.info(
                "Skipping document classification refinement for "
                "document_id=%s current_type=%s",
                state.document_id,
                current_type,
            )
            return

        self._save_classification_result(
            state,
            classification,
            source="extracted_text",
        )

    def _save_classification_result(
        self,
        state: WorkflowState,
        classification: ClassificationResult,
        source: str,
    ) -> None:
        document = self._require_document(state)

        if document.document_type != classification.document_type:
            state.document = self.document_repository.update_document_type(
                self.db,
                document,
                classification.document_type,
            )
        else:
            state.document = document

        state.document_type = classification.document_type
        self.logger.info(
            "Document classification completed for document_id=%s "
            "document_type=%s confidence_score=%s source=%s "
            "matched_signals=%s",
            state.document_id,
            classification.document_type,
            classification.confidence_score,
            source,
            ",".join(classification.matched_signals),
        )

    def _evaluate_ocr_confidence(
        self,
        state: WorkflowState,
    ) -> None:
        evaluation = self.confidence_evaluator.evaluate(
            extracted_text=state.extracted_text,
            raw_confidence_score=state.confidence_score,
            page_count=state.page_count,
            extraction_method=state.ocr_engine or OCR_ENGINE_PLACEHOLDER,
        )

        state.raw_confidence_score = evaluation.raw_engine_confidence
        state.confidence_score = evaluation.confidence_score
        state.confidence_evaluation_method = evaluation.evaluation_method

        self.logger.info(
            "OCR confidence evaluated for document_id=%s "
            "method=%s raw_engine_confidence=%s text_quality=%s "
            "coverage=%s final_confidence=%s signals=%s",
            state.document_id,
            evaluation.evaluation_method,
            evaluation.raw_engine_confidence,
            evaluation.text_quality_score,
            evaluation.coverage_score,
            evaluation.confidence_score,
            ",".join(evaluation.signals),
        )

    @staticmethod
    def _apply_extraction_result(
        state: WorkflowState,
        extraction_result: TextExtractionResult,
    ) -> None:
        state.extracted_text = extraction_result.extracted_text
        state.extracted_text_path = extraction_result.extracted_text_path
        state.page_count = extraction_result.page_count
        state.confidence_score = extraction_result.confidence_score
        state.raw_confidence_score = extraction_result.confidence_score
        state.processing_time = extraction_result.processing_time

    def _get_searchable_status(
        self,
        state: WorkflowState,
        extraction_method: str,
    ) -> bool:
        if state.is_searchable is not None:
            return state.is_searchable

        return self._is_searchable_extraction_method(extraction_method)

    @staticmethod
    def _is_searchable_extraction_method(
        extraction_method: str,
    ) -> bool:
        return extraction_method in {
            OCREngine.NATIVE_PDF.value,
            OCREngine.NATIVE_TEXT.value,
        }

    def _ocr_execution_placeholder(
        self,
        document: Document,
        ocr_engine: str,
    ) -> str:
        return OCR_PLACEHOLDER_TEXT

    @staticmethod
    def _require_document(state: WorkflowState) -> Document:
        if state.document is None:
            raise DocumentNotFoundError(
                f"Document not loaded: {state.document_id}"
            )
        return state.document

    @staticmethod
    def _require_processing_job(state: WorkflowState) -> ProcessingJob:
        if state.processing_job is None:
            raise ProcessingJobNotFoundError(
                "Processing job not loaded for document_id="
                f"{state.document_id}"
            )
        return state.processing_job



