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

        # Now, perform Longest Span Overlap Resolution on unique spans.
        sorted_detections = sorted(
            unique_entities.values(),
            key=lambda d: (
                -(d.end_char - d.start_char),  # Length descending
                -d.confidence_score,           # Confidence descending
                d.start_char                   # Position ascending
            )
        )

        accepted: list[DetectionResult] = []

        for detection in sorted_detections:
            overlaps = False
            for acc in accepted:
                if (
                    detection.page_number == acc.page_number
                    and detection.start_char < acc.end_char
                    and acc.start_char < detection.end_char
                ):
                    overlaps = True
                    # Record conflicting types for overlapping spans
                    if acc.entity_type.upper() != detection.entity_type.upper():
                        conflicting = acc.metadata.get("conflicting_types") or [acc.entity_type]
                        if detection.entity_type not in conflicting:
                            conflicting.append(detection.entity_type)
                        acc.metadata["conflicting_types"] = conflicting
                    # Merge detector names if they overlap
                    acc.detector = Deduplicator._merged_detectors(acc.detector, detection.detector)
                    break
            if not overlaps:
                accepted.append(detection)

        # Sort the accepted list by page number and position
        accepted.sort(key=lambda d: (d.page_number, d.start_char))
        return accepted

    @staticmethod
    def _merged_detectors(*detector_values: str) -> str:
        detectors = {
            detector.strip()
            for value in detector_values
            for detector in value.split(",")
            if detector.strip()
        }
        return ",".join(sorted(detectors))
