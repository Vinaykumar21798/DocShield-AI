from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EntityResponse(BaseModel):
    entity_id: str
    document_id: str
    ocr_result_id: Optional[str] = None
    entity_type: str
    entity_value: str
    privacy_category: Optional[str] = None
    confidence_score: Optional[float] = None
    final_confidence: Optional[float] = None
    detector: Optional[str] = None
    page_number: Optional[str] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    is_review_required: bool = False
    is_redacted: bool = False
    ai_decision: Optional[str] = None
    ai_reasoning: Optional[str] = None
    is_accepted_by_ai: Optional[bool] = True
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
