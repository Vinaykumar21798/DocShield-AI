from dataclasses import dataclass, field
from typing import Any, List

from modules.detection.detectors.base_detector import BaseDetector


@dataclass
class DetectionStrategy:
    """
    Stores the detector execution strategy for a document.
    """

    document_type: str
    language: str

    use_regex: bool = True
    use_presidio: bool = True
    use_gliner: bool = True
    use_medspacy: bool = True
    use_gemma: bool = False

    selected_detectors: list[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    """
    Encapsulates the execution strategy for a single document transaction.
    """

    selected_detectors: List[BaseDetector] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_empty(self) -> bool:
        """
        Returns True if no detectors (excluding Regex) need to run.
        """
        return len(self.selected_detectors) == 0
