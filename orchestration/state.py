from dataclasses import dataclass
from typing import Any, Dict, Optional

from database.models import Document, ProcessingJob


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
    extracted_text: Optional[str] = None
    extracted_text_path: Optional[str] = None
    structured_output: Optional[Dict[str, Any]] = None
    page_count: int = 0
    confidence_score: float = 0.0
    raw_confidence_score: float = 0.0
    confidence_evaluation_method: Optional[str] = None
    processing_time: float = 0.0
    error: Optional[str] = None

