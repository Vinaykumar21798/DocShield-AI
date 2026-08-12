from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field


class DocumentJob(BaseModel):
    """
    Job pushed into Redis.
    """

    document_id: UUID
    run_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
