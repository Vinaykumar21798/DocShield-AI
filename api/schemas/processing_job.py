from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProcessingJobBase(BaseModel):
    document_id: str
    workflow_stage: str
    queue_name: str


class ProcessingJobCreate(ProcessingJobBase):
    pass


class ProcessingJobUpdate(BaseModel):
    workflow_stage: Optional[str] = None
    job_status: Optional[str] = None
    worker_id: Optional[str] = None
    retry_count: Optional[int] = None
    error_message: Optional[str] = None


class ProcessingJobResponse(ProcessingJobBase):
    id: str

    job_status: str
    worker_id: Optional[str]
    retry_count: int
    error_message: Optional[str]

    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)