from modules.detection.models.detection_result import DetectionResult


class Deduplicator:
    """
    Removes duplicate entities detected by multiple detectors.
    """

    @staticmethod
    def deduplicate(
        detections: list[DetectionResult],
    ) -> list[DetectionResult]:

        unique_entities: dict[
            tuple[str, str],
            DetectionResult
        ] = {}

        for detection in detections:

            key = (
                detection.entity_type.upper(),
                detection.entity_value.strip().lower(),
            )

            if key not in unique_entities:
                unique_entities[key] = detection
                continue

            existing = unique_entities[key]

            # Keep the highest confidence detection
            if (
                detection.confidence_score
                > existing.confidence_score
            ):
                unique_entities[key] = detection

            else:
                # Preserve detector information
                detectors = set(
                    existing.detector.split(",")
                )

                detectors.add(detection.detector)

                existing.detector = ",".join(
                    sorted(detectors)
                )

        return list(unique_entities.values())