from modules.detection.models.detection_result import DetectionResult


class Deduplicator:
    """
    Removes duplicate detector outputs for the same entity span.

    The same value can legitimately appear multiple times in a document and
    every occurrence needs its own span for redaction. Only merge detections
    that point to the same page and character range.
    """

    @staticmethod
    def deduplicate(
        detections: list[DetectionResult],
    ) -> list[DetectionResult]:

        unique_entities: dict[
            tuple[str, str, int, int, int],
            DetectionResult,
        ] = {}

        for detection in detections:

            key = (
                detection.entity_type.upper(),
                detection.entity_value.strip().lower(),
                detection.page_number,
                detection.start_char,
                detection.end_char,
            )

            if key not in unique_entities:
                unique_entities[key] = detection
                continue

            existing = unique_entities[key]

            # Keep the highest confidence detection for this exact span.
            if detection.confidence_score > existing.confidence_score:
                detection.detector = Deduplicator._merged_detectors(
                    existing.detector,
                    detection.detector,
                )
                unique_entities[key] = detection
                continue

            existing.detector = Deduplicator._merged_detectors(
                existing.detector,
                detection.detector,
            )

        return list(unique_entities.values())

    @staticmethod
    def _merged_detectors(*detector_values: str) -> str:
        detectors = {
            detector.strip()
            for value in detector_values
            for detector in value.split(",")
            if detector.strip()
        }
        return ",".join(sorted(detectors))
