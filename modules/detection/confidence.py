from modules.detection.models.detection_result import DetectionResult


class ConfidenceCalculator:
    """
    Calculates confidence levels for entities detected in the
    sequential detection pipeline.

    Since each entity is detected by only one detector,
    confidence is based on the detector's own score rather
    than agreement across multiple detectors.
    """

    HIGH_CONFIDENCE_THRESHOLD = 0.85
    MEDIUM_CONFIDENCE_THRESHOLD = 0.60

    @classmethod
    def calculate(
        cls,
        detections: list[DetectionResult],
    ) -> list[DetectionResult]:

        for detection in detections:

            detector = detection.detector.lower()
            score = float(detection.confidence_score)

            # Detector-specific calibration
            if detector == "hybrid regex":

                # Regex already combines:
                # Pattern + Context + Validation
                final_score = score

            elif detector == "presidio":

                # Presidio returns statistical confidence
                final_score = score

            elif detector == "gliner":

                # GLiNER returns model confidence
                final_score = score

            elif detector == "medspacy":

                # MedSpaCy currently returns 1.0 for every entity.
                # Cap slightly to avoid treating every clinical
                # entity as absolutely certain.
                final_score = min(score, 0.95)

            else:

                final_score = score

            detection.confidence_score = round(final_score, 3)

            if final_score >= cls.HIGH_CONFIDENCE_THRESHOLD:

                level = "HIGH"

            elif final_score >= cls.MEDIUM_CONFIDENCE_THRESHOLD:

                level = "MEDIUM"

            else:

                level = "LOW"

            detection.metadata["confidence_level"] = level
            detection.metadata["final_confidence"] = final_score

        return detections