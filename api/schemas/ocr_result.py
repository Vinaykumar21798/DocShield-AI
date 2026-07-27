from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class OCRResultBase(BaseModel):
    document_id: str

    extraction_method: str
    is_searchable: bool

    extracted_text: Optional[str] = None
    extracted_text_path: Optional[str] = None
    structured_output: Optional[Dict[str, Any]] = None

    page_count: Optional[int] = None
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None


class OCRResultCreate(OCRResultBase):
    pass


class OCRResultUpdate(BaseModel):
    extracted_text: Optional[str] = None
    extracted_text_path: Optional[str] = None
    structured_output: Optional[Dict[str, Any]] = None

    page_count: Optional[int] = None
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None


class OCRResultResponse(OCRResultBase):
    id: str

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)