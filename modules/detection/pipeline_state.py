from dataclasses import dataclass, field

from modules.detection.mask_manager import MaskManager
from modules.detection.models.detection_result import DetectionResult


@dataclass
class PipelineState:
    """
    Maintains the state of the sequential detection pipeline.

    Responsibilities:
    - Store the original document text.
    - Track all detected entities.
    - Manage masked regions through MaskManager.
    """

    original_text: str

    resolved_entities: list[DetectionResult] = field(default_factory=list)
    executed_detectors: list[str] = field(default_factory=list)
    skipped_detectors: list[str] = field(default_factory=list)
    execution_time: dict[str, float] = field(default_factory=dict)
    detection_history: list[dict] = field(default_factory=list)
    confidence_summary: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.mask_manager = MaskManager(self.original_text)

    def add_entities(
        self,
        entities: list[DetectionResult],
        detector_name: str = "Unknown",
    ) -> None:
        """
        Add newly detected entities to the pipeline.
        """

        if not entities:
            # Still record that the detector was executed and found nothing
            if detector_name not in self.executed_detectors:
                self.executed_detectors.append(detector_name)
            self.detection_history.append({"step": detector_name, "count": 0})
            return

        self.resolved_entities.extend(entities)
        self.mask_manager.add_entities(entities)

        if detector_name not in self.executed_detectors:
            self.executed_detectors.append(detector_name)
        self.detection_history.append({"step": detector_name, "count": len(entities)})

    def log_skipped(self, detector_name: str) -> None:
        """Logs a skipped detector."""
        if detector_name not in self.skipped_detectors:
            self.skipped_detectors.append(detector_name)

    def log_time(self, detector_name: str, duration: float) -> None:
        """Logs execution latency in milliseconds."""
        self.execution_time[detector_name] = round(duration * 1000.0, 2)

    def finalize_confidence_summary(self) -> None:
        """Calculates count of entities per confidence level."""
        summary = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for entity in self.resolved_entities:
            lvl = entity.metadata.get("confidence_level", "HIGH")
            if lvl in summary:
                summary[lvl] += 1
        self.confidence_summary = summary

    @property
    def current_text(self) -> str:
        """
        Returns the remaining (masked) text for the next detector.
        """

        return self.mask_manager.remaining_text()

    @property
    def has_remaining_text(self) -> bool:
        """
        Returns True if unresolved text still exists.
        """

        return self.mask_manager.has_remaining_text()