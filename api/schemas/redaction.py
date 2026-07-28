from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RedactionResponse(BaseModel):
    redaction_id: str
    document_id: str
    redaction_type: str
    redacted_file_path: Optional[str] = None
    redaction_summary: Optional[str] = None
    processed_by: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)