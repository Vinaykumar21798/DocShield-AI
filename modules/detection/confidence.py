from modules.detection.models.detection_result import DetectionResult


class ConfidenceCalculator:
    """
    Calculates confidence levels for entities detected in the
    sequential detection pipeline.

    Since each entity is detected by only one detector,
    confidence is based on the detector's own score rather
    than agreement across multiple detectors.
    """

    HIGH_CONFIDENCE_THRESHOLD = 0.80
    MEDIUM_CONFIDENCE_THRESHOLD = 0.60

    @classmethod
    def calculate(
        cls,
        detections: list[DetectionResult],
        high_threshold: float | None = None,
        medium_threshold: float | None = None,
    ) -> list[DetectionResult]:
        high_threshold = (
            cls.HIGH_CONFIDENCE_THRESHOLD
            if high_threshold is None
            else high_threshold
        )
        medium_threshold = (
            cls.MEDIUM_CONFIDENCE_THRESHOLD
            if medium_threshold is None
            else medium_threshold
        )

        for detection in detections:

            detector = detection.detector.lower()
            score = float(detection.confidence_score)

            # Detector-specific calibration
            if detector == "hybrid regex":

                # Regex already combines:
                # Pattern + Context + Validation
                final_score = score

            elif detector == "presidio":

                # Presidio returns statistical confidence.
                # Boost DATE_TIME confidence if it meets the medium threshold (0.60)
                # to 0.80 (high confidence) so that it is masked early, preventing
                # redundant downstream candidate processing on dates.
                if detection.entity_type == "DATE_TIME" and score >= 0.60:
                    final_score = 0.80
                else:
                    final_score = score

            elif detector == "gliner":

                # GLiNER returns model confidence
                final_score = score

            elif detector == "medspacy":

                # MedSpaCy currently returns 1.0 for every entity.
                # Cap slightly to avoid treating every clinical
                # entity as absolutely certain.
                final_score = min(score, 0.95)

            elif "gemma" in detector or detection.metadata.get("gemma_validation") in {"CONFIRM", "RECLASSIFY"}:

                # Gemma contextual validation / LLM discovery
                if detection.metadata.get("test_detector"):
                    final_score = score
                else:
                    final_score = max(score, 0.88)
                detection.detector = "Gemma"
                detection.entity_owner = "gemma4e4b"

            else:

                final_score = score

            detection.confidence_score = round(final_score, 3)

            if final_score >= high_threshold:

                level = "HIGH"

            elif final_score >= medium_threshold:

                level = "MEDIUM"

            else:

                level = "LOW"

            detection.metadata["confidence_level"] = level
            detection.metadata["final_confidence"] = final_score

        return detections
