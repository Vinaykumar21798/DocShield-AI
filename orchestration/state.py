from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from database.models import Document, OCRResult, ProcessingJob


@dataclass
class WorkflowState:
    """
    Mutable state carried across document processing workflow steps.
    """

    document_id: str
    document: Optional[Document] = None
    processing_job: Optional[ProcessingJob] = None
    status: Optional[str] = None
    document_type: Optional[str] = None
    ocr_engine: Optional[str] = None
    is_searchable: Optional[bool] = None
    ocr_result: Optional[OCRResult] = None
    extracted_text: Optional[str] = None
    extracted_text_path: Optional[str] = None
    structured_output: Optional[Dict[str, Any]] = None
    page_count: int = 0
    confidence_score: float = 0.0
    raw_confidence_score: float = 0.0
    confidence_evaluation_method: Optional[str] = None
    processing_time: float = 0.0
    detected_entities: list[Any] = field(default_factory=list)
    persisted_entity_ids: list[str] = field(default_factory=list)
    review_count: int = 0
    redacted_file_path: Optional[str] = None
    report_path: Optional[str] = None
    error: Optional[str] = None