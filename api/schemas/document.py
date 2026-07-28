from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    filename: str
    stored_filename: str
    file_type: str
    file_size: int
    storage_path: str
    uploaded_by: Optional[str] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    status: Optional[str] = None
    document_type: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: str
    document_type: Optional[str]
    status: str

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)