import json
import logging
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from core.config import settings
from database.models import (
    ConfidenceScore,
    Document,
    Entity,
    OCRResult,
    ProcessingJob,
    Redaction,
    Report,
    Review,
)
from database.repositories.confidence_repository import ConfidenceRepository
from database.repositories.document_repository import (
    DocumentRepository,
    document_repository,
)
from database.repositories.entity_repository import EntityRepository
from database.repositories.ocr_result_repository import (
    OCRResultRepository,
    ocr_result_repository,
)
from database.repositories.processing_job_repository import (
    ProcessingJobRepository,
    processing_job_repository,
)
from database.repositories.redaction_repository import RedactionRepository
from database.repositories.report_repository import ReportRepository
from database.repositories.review_repository import ReviewRepository
from modules.classification.service import (
    ClassificationResult,
    DocumentClassificationService,
    DocumentType,
    document_classification_service,
)
from modules.detection.service import DetectionService
from modules.extraction.evaluation import (
    OCRConfidenceEvaluator,
    ocr_confidence_evaluator,
)
from modules.extraction.native import (
    NativePDFExtractionService,
    NativeTextExtractionService,
    TextExtractionResult,
)
from modules.extraction.mixed_pdf import MixedPDFExtractionService
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
REDACTED_TEXT_DIR = Path("storage/redacted")
REPORTS_DIR = Path("storage/reports")
HUMAN_REVIEW_THRESHOLD = 0.80

STARTUP_WORKFLOW_STEPS = {
    WorkflowStep.LOAD_DOCUMENT,
    WorkflowStep.UPDATE_PROCESSING_STATUS,
}

RESUME_START_STEP_BY_CHECKPOINT = {
    WorkflowStep.LOAD_DOCUMENT: WorkflowStep.DOCUMENT_CLASSIFICATION,
    WorkflowStep.UPDATE_PROCESSING_STATUS: WorkflowStep.DOCUMENT_CLASSIFICATION,
    WorkflowStep.DOCUMENT_CLASSIFICATION: WorkflowStep.OCR_DECISION,
    WorkflowStep.OCR_DECISION: WorkflowStep.OCR_DECISION,
    WorkflowStep.OCR_EXECUTION: WorkflowStep.OCR_DECISION,
    WorkflowStep.STORE_OCR_RESULTS: WorkflowStep.DETECTION_EXECUTION,
    WorkflowStep.DETECTION_EXECUTION: WorkflowStep.DETECTION_EXECUTION,
    WorkflowStep.STORE_DETECTION_RESULTS: WorkflowStep.HUMAN_REVIEW,
    WorkflowStep.HUMAN_REVIEW: WorkflowStep.REDACTION,
    WorkflowStep.REDACTION: WorkflowStep.REPORT_GENERATION,
    WorkflowStep.REPORT_GENERATION: WorkflowStep.COMPLETE_WORKFLOW,
    WorkflowStep.COMPLETE_WORKFLOW: WorkflowStep.COMPLETE_WORKFLOW,
}

OCR_RESTORE_CHECKPOINTS = {
    WorkflowStep.STORE_OCR_RESULTS,
    WorkflowStep.DETECTION_EXECUTION,
    WorkflowStep.STORE_DETECTION_RESULTS,
    WorkflowStep.HUMAN_REVIEW,
    WorkflowStep.REDACTION,
}

REDACTION_RESTORE_CHECKPOINTS = {
    WorkflowStep.REDACTION,
}


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


class ResumeCheckpointUnavailableError(DocumentWorkflowError):
    """
    Raised when persisted data for a checkpoint cannot be restored.
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
        mixed_pdf_extractor: Optional[MixedPDFExtractionService] = None,
        classification_service: Optional[
            DocumentClassificationService
        ] = None,
        confidence_evaluator: Optional[OCRConfidenceEvaluator] = None,
        detection_service: Optional[DetectionService] = None,
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
        self.detection_service = detection_service or DetectionService()
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
            paddle_ocr_extractor
            or PaddleOCRExtractionService(
                use_layout_analysis=(
                    settings.paddleocr_layout_analysis_enabled
                ),
            )
        )
        self.mixed_pdf_extractor = (
            mixed_pdf_extractor
            or MixedPDFExtractionService(self.paddle_ocr_extractor)
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
            WorkflowStep.DETECTION_EXECUTION: self._execute_detection,
            WorkflowStep.STORE_DETECTION_RESULTS: (
                self._store_detection_results
            ),
            WorkflowStep.HUMAN_REVIEW: self._prepare_human_review,
            WorkflowStep.REDACTION: self._redact_document_text,
            WorkflowStep.REPORT_GENERATION: self._generate_report,
            WorkflowStep.COMPLETE_WORKFLOW: self._complete_workflow,
        }

    def execute(self, document_id: str) -> WorkflowState:
        state = WorkflowState(document_id=str(document_id))
        plan = self.planner.create_plan()
        plan_steps = tuple(plan.steps)

        self.logger.info(
            "Starting document processing workflow for document_id=%s",
            state.document_id,
        )

        try:
            self._run_step(
                state,
                WorkflowStep.LOAD_DOCUMENT,
                checkpoint=False,
            )
            checkpoint_step = self._get_checkpoint_step(
                state.processing_job,
                plan_steps,
            )

            if (
                checkpoint_step == WorkflowStep.COMPLETE_WORKFLOW
                and state.processing_job is not None
                and state.processing_job.job_status == "COMPLETED"
            ):
                state.status = DOCUMENT_STATUS_COMPLETED
                self.logger.info(
                    "Workflow already completed for document_id=%s",
                    state.document_id,
                )
                return state

            resume_start_step = self._get_resume_start_step(checkpoint_step)
            is_resuming = self._is_resume_checkpoint(checkpoint_step)

            if is_resuming:
                self.logger.info(
                    "Resuming workflow for document_id=%s "
                    "last_completed_stage=%s resume_step=%s",
                    state.document_id,
                    checkpoint_step.value,
                    resume_start_step.value,
                )

            self._run_step(
                state,
                WorkflowStep.UPDATE_PROCESSING_STATUS,
                checkpoint=not is_resuming,
            )

            if is_resuming:
                try:
                    self._restore_state_for_resume(state, checkpoint_step)
                except ResumeCheckpointUnavailableError as exc:
                    self.logger.warning(
                        "Checkpoint restore failed for document_id=%s "
                        "last_completed_stage=%s: %s. Restarting from "
                        "document classification.",
                        state.document_id,
                        checkpoint_step.value,
                        exc,
                    )
                    resume_start_step = WorkflowStep.DOCUMENT_CLASSIFICATION

            for step in self._steps_from(plan_steps, resume_start_step):
                if step in STARTUP_WORKFLOW_STEPS:
                    continue

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
        checkpoint: bool = True,
    ) -> None:
        self.logger.info(
            "Starting workflow step=%s document_id=%s",
            step.value,
            state.document_id,
        )

        if state.processing_job is not None:
            state.processing_job = self._update_workflow_stage(
                state.processing_job,
                step,
            )

        handler = self._step_handlers[step]
        handler(state)

        if checkpoint and state.processing_job is not None:
            state.processing_job = self._update_last_completed_stage(
                state.processing_job,
                step,
            )

        self.logger.info(
            "Completed workflow step=%s document_id=%s",
            step.value,
            state.document_id,
        )

    @staticmethod
    def _is_resume_checkpoint(
        checkpoint_step: Optional[WorkflowStep],
    ) -> bool:
        return (
            checkpoint_step is not None
            and checkpoint_step not in STARTUP_WORKFLOW_STEPS
        )

    @staticmethod
    def _get_checkpoint_step(
        processing_job: Optional[ProcessingJob],
        plan_steps: Tuple[WorkflowStep, ...],
    ) -> Optional[WorkflowStep]:
        if processing_job is None:
            return None

        checkpoint_value = processing_job.last_completed_stage

        if (
            not checkpoint_value
            and processing_job.job_status == "COMPLETED"
        ):
            checkpoint_value = processing_job.workflow_stage

        if not checkpoint_value:
            return None

        try:
            checkpoint_step = WorkflowStep(checkpoint_value)
        except ValueError:
            return None

        if checkpoint_step not in plan_steps:
            return None

        return checkpoint_step

    @staticmethod
    def _get_resume_start_step(
        checkpoint_step: Optional[WorkflowStep],
    ) -> WorkflowStep:
        if checkpoint_step is None:
            return WorkflowStep.DOCUMENT_CLASSIFICATION

        return RESUME_START_STEP_BY_CHECKPOINT.get(
            checkpoint_step,
            WorkflowStep.DOCUMENT_CLASSIFICATION,
        )

    @staticmethod
    def _steps_from(
        plan_steps: Tuple[WorkflowStep, ...],
        start_step: WorkflowStep,
    ) -> Tuple[WorkflowStep, ...]:
        try:
            start_index = plan_steps.index(start_step)
        except ValueError:
            return tuple()

        return plan_steps[start_index:]

    def _restore_state_for_resume(
        self,
        state: WorkflowState,
        checkpoint_step: WorkflowStep,
    ) -> None:
        if checkpoint_step in OCR_RESTORE_CHECKPOINTS:
            self._restore_ocr_result(state)

        if checkpoint_step in REDACTION_RESTORE_CHECKPOINTS:
            self._restore_redaction_result(state)

    def _restore_ocr_result(self, state: WorkflowState) -> None:
        ocr_result = self.ocr_result_repository.get_latest_by_document_id(
            self.db,
            state.document_id,
        )

        if ocr_result is None:
            raise ResumeCheckpointUnavailableError(
                "No OCR result exists for checkpoint restore."
            )

        extracted_text = ocr_result.extracted_text

        if extracted_text is None and ocr_result.extracted_text_path:
            extracted_text_path = Path(ocr_result.extracted_text_path)
            if extracted_text_path.exists():
                extracted_text = extracted_text_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )

        state.ocr_result = ocr_result
        state.ocr_engine = ocr_result.extraction_method
        state.is_searchable = ocr_result.is_searchable
        state.extracted_text = extracted_text or ""
        state.extracted_text_path = ocr_result.extracted_text_path
        state.structured_output = ocr_result.structured_output
        state.page_count = ocr_result.page_count or 0
        state.confidence_score = ocr_result.confidence_score or 0.0
        state.raw_confidence_score = state.confidence_score
        state.processing_time = ocr_result.processing_time or 0.0

    def _restore_redaction_result(self, state: WorkflowState) -> None:
        redaction = (
            self.db.query(Redaction)
            .filter(Redaction.document_id == state.document_id)
            .order_by(Redaction.created_at.desc())
            .first()
        )

        if redaction is None:
            raise ResumeCheckpointUnavailableError(
                "No redaction result exists for checkpoint restore."
            )

        state.redacted_file_path = redaction.redacted_file_path

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

        if ocr_engine == OCREngine.MIXED_PDF.value:
            extraction_result = self.mixed_pdf_extractor.extract(document)
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
            structured_output=state.structured_output,
            page_count=state.page_count,
            confidence_score=state.confidence_score,
            processing_time=state.processing_time,
        )

        state.ocr_result = self.ocr_result_repository.create_result(
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

    def _execute_detection(self, state: WorkflowState) -> None:
        if not state.extracted_text or not state.extracted_text.strip():
            state.detected_entities = []
            self.logger.info(
                "Detection skipped for document_id=%s because extracted text is empty",
                state.document_id,
            )
            return

        state.detected_entities = self.detection_service.detect(
            state.extracted_text,
            document_type=state.document_type,
        )
        self.logger.info(
            "Detection completed for document_id=%s entity_count=%s",
            state.document_id,
            len(state.detected_entities),
        )

    def _store_detection_results(self, state: WorkflowState) -> None:
        document = self._require_document(state)
        ocr_result = self._require_ocr_result(state)

        entity_repository = EntityRepository(self.db)
        confidence_repository = ConfidenceRepository(self.db)

        self._delete_existing_detection_outputs(document.id)
        state.persisted_entity_ids = []

        for detection in state.detected_entities:
            entity = Entity(
                id=str(uuid4()),
                document_id=document.id,
                ocr_result_id=ocr_result.id,
                entity_type=detection.entity_type,
                entity_value=detection.entity_value,
                page_number=str(detection.page_number),
                confidence_score=detection.confidence_score,
                detector=detection.detector,
                start_char=detection.start_char,
                end_char=detection.end_char,
                privacy_category=detection.privacy_category,
                entity_owner=detection.entity_owner or detection.detector,
                canonical_type=detection.canonical_type or detection.entity_type,
                processing_stage="DETECTION",
                is_review_required=self._is_review_required(detection),
                is_redacted=False,
                final_confidence=detection.confidence_score,
            )
            entity_repository.create(entity)
            state.persisted_entity_ids.append(entity.id)

            confidence_repository.create(
                ConfidenceScore(
                    id=str(uuid4()),
                    entity_id=entity.id,
                    confidence_score=detection.confidence_score,
                    confidence_level=self._confidence_level(detection),
                    threshold=HUMAN_REVIEW_THRESHOLD,
                )
            )

        self.logger.info(
            "Stored detection outputs for document_id=%s entity_count=%s",
            document.id,
            len(state.persisted_entity_ids),
        )

    def _prepare_human_review(self, state: WorkflowState) -> None:
        document = self._require_document(state)
        entity_repository = EntityRepository(self.db)
        review_repository = ReviewRepository(self.db)
        review_count = 0

        for entity in entity_repository.get_by_document_id(document.id):
            if not entity.is_review_required:
                continue

            if review_repository.get_by_entity_id(entity.id) is not None:
                continue

            review_repository.create(
                Review(
                    id=str(uuid4()),
                    entity_id=entity.id,
                    reviewer=None,
                    review_status="PENDING",
                    review_comment=(
                        "Flagged for manual review due to low confidence score."
                    ),
                    reviewed_at=None,
                )
            )
            review_count += 1

        state.review_count = review_count
        self.logger.info(
            "Human review prepared for document_id=%s pending_review_count=%s",
            document.id,
            review_count,
        )

    def _redact_document_text(self, state: WorkflowState) -> None:
        document = self._require_document(state)
        source_text = state.extracted_text or ""
        entity_repository = EntityRepository(self.db)
        redaction_repository = RedactionRepository(self.db)
        entities = entity_repository.get_by_document_id(document.id)

        redaction_repository.delete_by_document_id(document.id)
        redacted_text = self._apply_redactions(source_text, entities)
        redacted_file_path = self._save_redacted_text_file(
            document.id,
            redacted_text,
        )

        redaction_repository.create(
            Redaction(
                id=str(uuid4()),
                document_id=document.id,
                redaction_type="PII_PHI_TEXT_REDACTION",
                redacted_file_path=redacted_file_path,
                redaction_summary=(
                    f"Redacted {len(entities)} sensitive entities."
                ),
                processed_by=self.worker_id,
            )
        )

        for entity in entities:
            entity.is_redacted = True
            self.db.add(entity)
        self.db.commit()

        state.redacted_file_path = redacted_file_path
        self.logger.info(
            "Redaction completed for document_id=%s entity_count=%s",
            document.id,
            len(entities),
        )

    def _generate_report(self, state: WorkflowState) -> None:
        document = self._require_document(state)
        entity_repository = EntityRepository(self.db)
        report_repository = ReportRepository(self.db)
        entities = entity_repository.get_by_document_id(document.id)
        reviews = (
            self.db.query(Review)
            .join(Entity, Review.entity_id == Entity.id)
            .filter(Entity.document_id == document.id)
            .all()
        )

        for existing_report in report_repository.get_by_document_id(document.id):
            self.db.delete(existing_report)
        self.db.commit()

        detectors_used = sorted(
            {entity.detector for entity in entities if entity.detector}
        )
        total_pii = sum(
            1 for entity in entities if entity.privacy_category == "PII"
        )
        total_phi = sum(
            1 for entity in entities if entity.privacy_category == "PHI"
        )
        pending_reviews = [
            review for review in reviews if review.review_status == "PENDING"
        ]
        qwen_invoked = any(
            (entity.detector or "").lower().startswith("qwen")
            for entity in entities
        )

        report_payload = {
            "document_id": document.id,
            "document_type": document.document_type,
            "ocr_result_id": state.ocr_result.id if state.ocr_result else None,
            "total_entities": len(entities),
            "total_pii": total_pii,
            "total_phi": total_phi,
            "pending_reviews": len(pending_reviews),
            "redacted_file_path": state.redacted_file_path,
            "detectors_used": detectors_used,
            "entities": [
                {
                    "entity_id": entity.id,
                    "entity_type": entity.entity_type,
                    "entity_value": entity.entity_value,
                    "privacy_category": entity.privacy_category,
                    "confidence_score": entity.confidence_score,
                    "final_confidence": entity.final_confidence,
                    "is_review_required": entity.is_review_required,
                    "is_redacted": entity.is_redacted,
                    "detector": entity.detector,
                    "page_number": entity.page_number,
                    "start_char": entity.start_char,
                    "end_char": entity.end_char,
                }
                for entity in entities
            ],
        }
        report_path = self._save_report_file(document.id, report_payload)

        report_repository.create(
            Report(
                id=str(uuid4()),
                document_id=document.id,
                report_type="AUDIT",
                total_entities=len(entities),
                total_redactions=len(entities),
                report_path=report_path,
                generated_by=self.worker_id,
                processing_duration_ms=int(state.processing_time * 1000),
                detectors_used=",".join(detectors_used),
                qwen_invoked=qwen_invoked,
                total_pii=total_pii,
                total_phi=total_phi,
                review_completion=(len(pending_reviews) == 0),
                redaction_completion=all(
                    entity.is_redacted for entity in entities
                ) if entities else True,
            )
        )

        state.report_path = report_path
        self.logger.info(
            "Report generated for document_id=%s path=%s",
            document.id,
            report_path,
        )

    def _delete_existing_detection_outputs(self, document_id: str) -> None:
        entities = EntityRepository(self.db).get_by_document_id(document_id)
        if not entities:
            return

        entity_ids = [entity.id for entity in entities]
        self.db.query(Review).filter(Review.entity_id.in_(entity_ids)).delete(
            synchronize_session=False,
        )
        self.db.query(ConfidenceScore).filter(
            ConfidenceScore.entity_id.in_(entity_ids),
        ).delete(synchronize_session=False)
        for entity in entities:
            self.db.delete(entity)
        self.db.commit()

    @staticmethod
    def _confidence_level(detection) -> str:
        confidence_level = detection.metadata.get("confidence_level")
        if confidence_level:
            return confidence_level

        if detection.confidence_score >= 0.85:
            return "HIGH"

        if detection.confidence_score >= 0.60:
            return "MEDIUM"

        return "LOW"

    @staticmethod
    def _is_review_required(detection) -> bool:
        # 1. Regex detector with confidence >= 0.95: Auto Approved
        is_regex = "regex" in detection.detector.lower()
        if is_regex and detection.confidence_score >= 0.95:
            # But check if there was a detector disagreement conflict
            if not detection.metadata.get("conflicting_types"):
                return False

        # 2. Check if multiple detectors disagreed on the entity type
        if detection.metadata.get("conflicting_types") and len(detection.metadata["conflicting_types"]) > 1:
            return True

        # 3. Check if unknown or unregistered entity type
        known_types = {
            "PERSON", "PATIENT", "DOCTOR", "PHYSICIAN", "PROVIDER", "NURSE", "HEALTHCARE_STAFF",
            "ORGANIZATION", "HOSPITAL", "CLINIC", "MEDICAL_FACILITY", "HEALTHCARE_ORGANIZATION",
            "ADDRESS", "LOCATION", "CITY", "STATE", "COUNTRY", "ZIP_CODE",
            "EMAIL", "PHONE_NUMBER", "US_PHONE_NUMBER", "URL", "IP_ADDRESS",
            "AADHAAR_NUMBER", "PAN_NUMBER", "PASSPORT_NUMBER", "DRIVING_LICENSE", "VOTER_ID",
            "BANK_ACCOUNT_NUMBER", "IFSC_CODE", "CREDIT_CARD_NUMBER", "DEBIT_CARD_NUMBER", "UPI_ID",
            "DATE", "DATE_TIME", "VISIT_DATE", "TIME", "AGE", "DATE_OF_BIRTH", "START_DATE",
            "MEDICAL_RECORD_NUMBER", "MRN", "PATIENT_ID", "INSURANCE_ID", "POLICY_NUMBER", "CLAIM_NUMBER",
            "DISEASE", "PROBLEM", "DIAGNOSIS", "MEDICATION", "DRUG", "DOSAGE", "SYMPTOM", "PROCEDURE",
            "LAB", "LAB_RESULT", "LAB_TEST", "ALLERGY", "VITAL_SIGN", "CLINICAL_FINDING",
            "INVOICE_NUMBER", "GSTIN", "DOCUMENT_ID", "NPI_NUMBER", "MEMBER_ID", "GROUP_NUMBER",
            "TAX_ID", "EOB_NUMBER", "CLINICAL_MEASUREMENT", "PO_BOX"
        }
        if detection.entity_type.upper() not in known_types:
            return True

        # 4. Standard threshold check
        return detection.confidence_score < HUMAN_REVIEW_THRESHOLD

    @staticmethod
    def _apply_redactions(
        text: str,
        entities: list[Entity],
    ) -> str:
        redacted_text = text
        valid_entities = [
            entity for entity in entities
            if entity.start_char is not None
            and entity.end_char is not None
            and 0 <= entity.start_char < entity.end_char <= len(text)
        ]
        valid_entities.sort(key=lambda entity: entity.start_char, reverse=True)

        for entity in valid_entities:
            marker = f"[REDACTED_{entity.entity_type}]"
            redacted_text = (
                redacted_text[:entity.start_char]
                + marker
                + redacted_text[entity.end_char:]
            )

        return redacted_text

    @staticmethod
    def _save_redacted_text_file(
        document_id: str,
        redacted_text: str,
    ) -> str:
        redacted_path = REDACTED_TEXT_DIR / f"{document_id}_redacted.txt"
        redacted_path.parent.mkdir(parents=True, exist_ok=True)
        redacted_path.write_text(redacted_text, encoding="utf-8")
        return redacted_path.as_posix()

    @staticmethod
    def _save_report_file(
        document_id: str,
        report_payload: dict,
    ) -> str:
        report_path = REPORTS_DIR / f"{document_id}_audit_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report_payload, indent=2),
            encoding="utf-8",
        )
        return report_path.as_posix()

    @staticmethod
    def _require_ocr_result(state: WorkflowState) -> OCRResult:
        if state.ocr_result is None:
            raise DocumentWorkflowError(
                "OCR result not stored for document_id="
                f"{state.document_id}"
            )
        return state.ocr_result

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
    ) -> ProcessingJob:
        return self.processing_job_repository.update_workflow_stage(
            self.db,
            processing_job,
            step.value,
        )

    def _update_last_completed_stage(
        self,
        processing_job: ProcessingJob,
        step: WorkflowStep,
    ) -> ProcessingJob:
        return self.processing_job_repository.update_last_completed_stage(
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
        state.structured_output = extraction_result.structured_output
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



