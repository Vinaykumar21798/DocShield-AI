from __future__ import annotations

import logging
import os
import re

GLiNER = None


from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult

logger = logging.getLogger(__name__)

TRUE_VALUES = {"1", "true", "yes", "on"}


class GLiNERDetector(BaseDetector):
    """
    Semantic fallback detector.

    Runs after Regex and Presidio. Uses GLiNER when the model is available
    locally, with deterministic healthcare role rules as a safe fallback.
    """

    MIN_CONFIDENCE = 0.60
    FALLBACK_CONFIDENCE = 0.76
    MODEL_ID = "urchade/gliner_small-v2.1"

    INVALID_VALUES = {
        "address",
        "email",
        "e-mail",
        "phone",
        "telephone",
        "mobile",
        "fax",
        "name",
        "patient",
        "patient name",
        "doctor",
        "hospital",
        "diagnosis",
        "chief complaint",
        "complaint",
        "medication",
        "medications",
        "procedure",
        "procedures",
        "laboratory",
        "lab",
        "results",
        "allergy",
        "vital signs",
    }

    FALLBACK_PATTERNS = (
        (r"\bDr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", "DOCTOR"),
        (r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+Hospital\b", "HOSPITAL"),
        (r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+Clinic\b", "MEDICAL_FACILITY"),
        (r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+Medical Center\b", "MEDICAL_FACILITY"),
        (r"\bPatient\s*[:\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", "PATIENT"),
        (r"\bPatient Name\s*[:\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", "PATIENT"),
    )

    @property
    def name(self) -> str:
        return "gliner"

    @property
    def model(self):
        global GLiNER

        if GLiNER is None:
            try:
                from gliner import GLiNER as gliner_model_class
            except ImportError as exc:
                raise RuntimeError("GLiNER package is not installed") from exc
            GLiNER = gliner_model_class

        if self._model is None:
            allow_download = os.getenv(
                "GLINER_ALLOW_MODEL_DOWNLOAD",
                "false",
            ).strip().lower() in TRUE_VALUES
            self._model = GLiNER.from_pretrained(
                self.MODEL_ID,
                local_files_only=not allow_download,
            )
        return self._model

    def __init__(self) -> None:
        self._model = None

        self.labels = [
            "person",
            "patient",
            "doctor",
            "hospital",
            "nurse",
            "physician",
            "healthcare staff",
            "medical facility",
            "healthcare organization",
            "organization",
            "company",
            "bank",
        ]

    def should_run(self, text: str, state: "PipelineState") -> bool:
        """
        GLiNER targets healthcare people and facility entities.
        """
        if not text or not text.strip():
            return False

        cleaned = self.clean_text_of_labels(text)
        if not cleaned:
            return False

        text_lower = text.lower()

        if any(phrase in text_lower for phrase in ["dr.", "dr ", "medical center", "healthcare organization", "medical facility", "clinical role", "healthcare staff"]):
            return True

        words = set(re.findall(r"\b[a-z]+\b", text_lower))
        gliner_keywords = {
            "doctor", "physician", "surgeon", "consultant", "specialist", "md",
            "patient", "admitted", "discharged", "hospital", "clinic", "healthcare",
            "ward", "icu", "nursing", "hospice", "referred", "mrn", "clinical",
            "attending", "referring", "resident", "intern", "practitioner", "np", "pa",
            "nurse", "staff", "provider", "facility", "outpatient", "inpatient",
        }

        return not words.isdisjoint(gliner_keywords)

    def detect(
        self,
        text: str,
        page_number: int = 1,
    ) -> list[DetectionResult]:
        if not text or not text.strip():
            return []

        if os.getenv("GLINER_ENABLED", "true").strip().lower() not in TRUE_VALUES:
            return self._detect_with_fallback_rules(text, page_number)

        try:
            predictions = self.model.predict_entities(
                text,
                self.labels,
            )
        except Exception as exc:
            logger.warning("GLiNER unavailable; using fallback rules: %s", exc)
            return self._detect_with_fallback_rules(text, page_number)

        detections: list[DetectionResult] = []
        seen = set()

        for prediction in predictions:
            score = float(prediction["score"])

            if score < self.MIN_CONFIDENCE:
                continue

            start = prediction["start"]
            end = prediction["end"]
            entity_value = text[start:end]
            entity_value = " ".join(entity_value.split()).strip()

            if not entity_value:
                continue

            if entity_value.lower().rstrip(":") in self.INVALID_VALUES:
                continue

            if re.fullmatch(r"[\W_]+", entity_value):
                continue

            if len(entity_value) < 3:
                continue

            label = prediction["label"].upper()

            if label in {"DOCTOR", "PHYSICIAN"}:
                prefix_match = re.search(r"\b[Dd]r\.?\s+$", text[max(0, start - 5):start])
                if prefix_match:
                    start = start - len(prefix_match.group(0))
                    entity_value = text[start:end]
                    entity_value = " ".join(entity_value.split()).strip()

            context_window = text[max(0, start - 25):start].lower()
            if "patient" in context_window:
                label = "PATIENT"
            elif "nurse" in context_window:
                label = "NURSE"

            if label == "ADDRESS" and len(entity_value.split()) == 1:
                continue

            if label == "DOCTOR":
                if (
                    not entity_value.lower().startswith("dr")
                    and len(entity_value.split()) < 2
                ):
                    continue

            key = (
                label,
                entity_value.lower(),
            )

            if key in seen:
                continue

            seen.add(key)
            detections.append(
                DetectionResult(
                    entity_type=label,
                    entity_value=entity_value,
                    confidence_score=score,
                    start_char=start,
                    end_char=end,
                    page_number=page_number,
                    detector=self.name,
                    metadata={
                        "model": "GLiNER",
                        "fallback_detector": True,
                    },
                )
            )

        detections.sort(
            key=lambda entity: (
                entity.page_number,
                entity.start_char,
            )
        )
        return detections

    def _detect_with_fallback_rules(
        self,
        text: str,
        page_number: int,
    ) -> list[DetectionResult]:
        detections: list[DetectionResult] = []
        seen: set[tuple[str, str]] = set()

        for pattern, label in self.FALLBACK_PATTERNS:
            for match in re.finditer(pattern, text):
                start = match.start(1) if match.lastindex else match.start()
                end = match.end(1) if match.lastindex else match.end()
                entity_value = " ".join(text[start:end].split()).strip()

                if not entity_value or entity_value.lower().rstrip(":") in self.INVALID_VALUES:
                    continue

                key = (label, entity_value.lower())
                if key in seen or self._overlaps(start, end, detections):
                    continue

                seen.add(key)
                detections.append(
                    DetectionResult(
                        entity_type=label,
                        entity_value=entity_value,
                        confidence_score=self.FALLBACK_CONFIDENCE,
                        start_char=start,
                        end_char=end,
                        page_number=page_number,
                        detector=self.name,
                        metadata={
                            "model": "deterministic",
                            "fallback_detector": True,
                        },
                    )
                )

        detections.sort(key=lambda entity: (entity.page_number, entity.start_char))
        return detections

    @staticmethod
    def _overlaps(
        start: int,
        end: int,
        accepted: list[DetectionResult],
    ) -> bool:
        return any(
            start < entity.end_char and end > entity.start_char
            for entity in accepted
        )