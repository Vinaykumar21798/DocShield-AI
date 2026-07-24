from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentJob(BaseModel):
    """
    Job pushed into Redis.
    """

    document_id: UUID
    created_at: datetime = datetime.utcnow()