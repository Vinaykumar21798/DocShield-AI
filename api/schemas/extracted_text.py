from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ExtractedTextResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    document_type: Optional[str] = None
    document_status: str
    processing_status: Optional[str] = None
    workflow_stage: Optional[str] = None

    ocr_result_id: str
    extraction_method: str
    is_searchable: bool
    extracted_text: Optional[str] = None
    extracted_text_path: Optional[str] = None
    structured_output: Optional[Dict[str, Any]] = None
    page_count: Optional[int] = None
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
