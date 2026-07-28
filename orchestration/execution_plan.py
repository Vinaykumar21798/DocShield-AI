from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class WorkflowStep(str, Enum):
    LOAD_DOCUMENT = "LOAD_DOCUMENT"
    UPDATE_PROCESSING_STATUS = "UPDATE_PROCESSING_STATUS"
    DOCUMENT_CLASSIFICATION = "DOCUMENT_CLASSIFICATION"
    OCR_DECISION = "OCR_DECISION"
    OCR_EXECUTION = "OCR_EXECUTION"
    STORE_OCR_RESULTS = "STORE_OCR_RESULTS"
    COMPLETE_WORKFLOW = "COMPLETE_WORKFLOW"


@dataclass(frozen=True)
class WorkflowExecutionPlan:
    steps: Tuple[WorkflowStep, ...]
