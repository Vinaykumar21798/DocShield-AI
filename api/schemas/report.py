from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ReportResponse(BaseModel):
    report_id: str
    document_id: str
    report_type: str
    total_entities: int = 0
    total_redactions: int = 0
    report_path: Optional[str] = None
    generated_by: Optional[str] = None
    processing_duration_ms: Optional[int] = None
    detectors_used: Optional[str] = None
    qwen_invoked: bool = False
    total_pii: int = 0
    total_phi: int = 0
    review_completion: bool = False
    redaction_completion: bool = False
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReportDetailResponse(ReportResponse):
    payload: Optional[Dict[str, Any]] = None