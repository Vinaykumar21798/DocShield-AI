from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewEntityResponse(BaseModel):
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


class ReviewResponse(BaseModel):
    review_id: str
    entity_id: str
    document_id: str
    reviewer: Optional[str] = None
    review_status: Optional[str] = None
    review_comment: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    entity: ReviewEntityResponse

    model_config = ConfigDict(from_attributes=True)


class ReviewDecisionRequest(BaseModel):
    reviewer: Optional[str] = Field(default=None, min_length=1, max_length=255)
    review_status: str = Field(..., min_length=1, max_length=50)
    review_comment: Optional[str] = None
    entity_type: Optional[str] = None
    entity_value: Optional[str] = None
    privacy_category: Optional[str] = None
    final_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    is_redacted: Optional[bool] = None


class ReviewDecisionResponse(ReviewResponse):
    pass