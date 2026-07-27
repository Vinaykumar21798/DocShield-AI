from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentStatusResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    document_type: Optional[str] = None
    document_status: str

    processing_job_id: Optional[str] = None
    processing_status: Optional[str] = None
    workflow_stage: Optional[str] = None
    queue_name: Optional[str] = None
    worker_id: Optional[str] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    has_extracted_text: bool = False
    ocr_result_id: Optional[str] = None
    extraction_method: Optional[str] = None
    is_searchable: Optional[bool] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
