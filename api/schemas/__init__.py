from .document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
)

from .processing_job import (
    ProcessingJobCreate,
    ProcessingJobUpdate,
    ProcessingJobResponse,
)

from .ocr_result import (
    OCRResultCreate,
    OCRResultUpdate,
    OCRResultResponse,
)

__all__ = [
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "ProcessingJobCreate",
    "ProcessingJobUpdate",
    "ProcessingJobResponse",
    "OCRResultCreate",
    "OCRResultUpdate",
    "OCRResultResponse",
]