from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

class RunProgress(BaseModel):
    document_id: str
    filename: str
    status: str
    document_type: Optional[str] = None

class RunResponse(BaseModel):
    run_id: str
    status: str
    total_files: int
    completed_files: int
    failed_files: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    documents: List[RunProgress]
