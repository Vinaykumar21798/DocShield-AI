from __future__ import annotations

import re

from gliner import GLiNER

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult


class GLiNERDetector(BaseDetector):
    """
    Semantic fallback detector.

    Runs after Regex and Presidio.
    Detects entities missed by previous detectors.
    """

    MIN_CONFIDENCE = 0.70

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

    @property
    def name(self) -> str:
        return "gliner"

    @property
    def model(self):
        if self._model is None:
            self._model = GLiNER.from_pretrained(
                "urchade/gliner_medium-v2.1"
            )
        return self._model

    def __init__(self) -> None:
        self._model = None

        self.labels = [
            "patient",
            "doctor",
            "hospital",
            "nurse",
            "physician",
            "healthcare staff",
            "medical facility",
            "healthcare organization",
        ]

    def should_run(self, text: str, state: "PipelineState") -> bool:
        """
        GLiNER targets DOCTOR, HOSPITAL, PATIENT, HEALTHCARE ORGANIZATION.
        Runs if text contains clinical roles, healthcare facility tags, or patient references.
        """
        if not text or not text.strip():
            return False

        cleaned = self.clean_text_of_labels(text)
        if not cleaned:
            return False

        text_lower = text.lower()

        # Check special multi-word phrases or punctuated abbreviations
        if any(phrase in text_lower for phrase in ["dr.", "dr ", "medical center", "healthcare organization", "medical facility", "clinical role", "healthcare staff"]):
            return True

        # Find all alphanumeric words in the original raw text to check keywords
        words = set(re.findall(r'\b[a-z]+\b', text_lower))
        gliner_keywords = {
            "doctor", "physician", "surgeon", "consultant", "specialist", "md",
            "patient", "admitted", "discharged", "hospital", "clinic", "healthcare",
            "ward", "icu", "nursing", "hospice", "referred", "mrn", "clinical"
        }

        return not words.isdisjoint(gliner_keywords)




    def detect(
        self,
        text: str,
        page_number: int = 1,
    ) -> list[DetectionResult]:

        predictions = self.model.predict_entities(
            text,
            self.labels,
        )

        detections: list[DetectionResult] = []

        seen = set()

        for prediction in predictions:

            score = float(prediction["score"])

            #
            # Ignore weak predictions
            #
            if score < self.MIN_CONFIDENCE:
                continue

            start = prediction["start"]
            end = prediction["end"]

            entity_value = text[start:end]

            #
            # Normalize whitespace
            #
            entity_value = " ".join(entity_value.split()).strip()

            if not entity_value:
                continue

            #
            # Ignore section headers
            #
            if entity_value.lower().rstrip(":") in self.INVALID_VALUES:
                continue

            #
            # Ignore punctuation-only entities
            #
            if re.fullmatch(r"[\W_]+", entity_value):
                continue

            #
            # Ignore tiny predictions
            #
            if len(entity_value) < 3:
                continue

            label = prediction["label"].upper()

            # Prefix expansion for Doctor / Physician (Task 8)
            if label in {"DOCTOR", "PHYSICIAN"}:
                prefix_match = re.search(r'\b[Dd]r\.?\s+$', text[max(0, start - 5):start])
                if prefix_match:
                    start = start - len(prefix_match.group(0))
                    entity_value = text[start:end]
                    entity_value = " ".join(entity_value.split()).strip()

            # Context-based label refinement (Task 4)
            context_window = text[max(0, start - 25):start].lower()
            if "patient" in context_window:
                label = "PATIENT"
            elif "nurse" in context_window:
                label = "NURSE"

            #
            # Ignore ADDRESS headers
            #
            if (
                label == "ADDRESS"
                and len(entity_value.split()) == 1
            ):
                continue

            #
            # Doctor sanity check
            #
            if label == "DOCTOR":

                if (
                    not entity_value.lower().startswith("dr")
                    and len(entity_value.split()) < 2
                ):
                    continue

            #
            # Remove duplicate detections
            #
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