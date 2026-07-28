from typing import Optional

from pydantic import BaseModel, Field


class DetectionResult(BaseModel):
    """
    Standard output model for all detection engines.
    """

    entity_type: str = Field(..., description="Type of detected entity")
    entity_value: str = Field(..., description="Detected text")
    privacy_category: str = Field(
        default="PII", description="Privacy classification (PII, PHI, etc.)"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score"
    )

    start_char: int = Field(..., description="Start character index")
    end_char: int = Field(..., description="End character index")

    page_number: int = Field(default=1, description="Page number")

    detector: str = Field(
        ..., description="Detector that produced this entity"
    )

    metadata: Optional[dict] = Field(
        default_factory=dict,
        description="Additional detector-specific metadata",
    )

    # Output compatibility fields (Issue 4)
    text: Optional[str] = None
    confidence: Optional[float] = None
    start: Optional[int] = None
    end: Optional[int] = None
    canonical_type: Optional[str] = None
    entity_owner: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.text is None:
            self.text = self.entity_value
        if self.confidence is None:
            self.confidence = self.confidence_score
        if self.start is None:
            self.start = self.start_char
        if self.end is None:
            self.end = self.end_char
        if self.canonical_type is None:
            self.canonical_type = self.entity_type
        if self.entity_owner is None:
            self.entity_owner = self.detector