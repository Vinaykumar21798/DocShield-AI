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

        # First, group exact duplicates (same page, start_char, end_char)
        # to combine their detector lists and keep the highest confidence.
        unique_entities: dict[
            tuple[int, int, int],
            DetectionResult,
        ] = {}

        for detection in detections:
            key = (
                detection.page_number,
                detection.start_char,
                detection.end_char,
            )

            if key not in unique_entities:
                unique_entities[key] = detection
                continue

            existing = unique_entities[key]

            # Collect conflicting types
            if existing.entity_type.upper() != detection.entity_type.upper():
                conflicting = existing.metadata.get("conflicting_types") or [existing.entity_type]
                if detection.entity_type not in conflicting:
                    conflicting.append(detection.entity_type)
                existing.metadata["conflicting_types"] = conflicting
                detection.metadata["conflicting_types"] = conflicting

            # Merge detector names
            merged_detector = Deduplicator._merged_detectors(existing.detector, detection.detector)

            # Compare confidence
            if detection.confidence_score > existing.confidence_score:
                detection.detector = merged_detector
                unique_entities[key] = detection
            else:
                existing.detector = merged_detector

        # Return unique spans sorted by page number and position.
        results = list(unique_entities.values())
        results.sort(key=lambda d: (d.page_number, d.start_char))
        return results

    @staticmethod
    def _merged_detectors(*detector_values: str) -> str:
        detectors = {
            detector.strip()
            for value in detector_values
            for detector in value.split(",")
            if detector.strip()
        }
        return ",".join(sorted(detectors))
