from __future__ import annotations

import logging
import re
from typing import List

try:
    import medspacy
    from medspacy.ner import TargetRule
except ImportError:
    medspacy = None
    TargetRule = None

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult

logger = logging.getLogger(__name__)


class MedSpaCyDetector(BaseDetector):

    DEFAULT_CONFIDENCE = 0.85
    FALLBACK_CONFIDENCE = 0.78

    ALLOWED_LABELS = {
        "PROBLEM",
        "MEDICATION",
        "PROCEDURE",
        "LAB",
        "SYMPTOM",
        "DIAGNOSIS",
        "ALLERGY",
        "VITAL_SIGN",
        "DISEASE",
        "CLINICAL FINDING",
        "CLINICAL_FINDING",
    }

    TARGET_RULES = (
        ("type 2 diabetes mellitus", "DISEASE"),
        ("diabetes", "DISEASE"),
        ("hypertension", "DISEASE"),
        ("asthma", "DISEASE"),
        ("persistent fever", "SYMPTOM"),
        ("shortness of breath", "SYMPTOM"),
        ("chest pain", "SYMPTOM"),
        ("back pain", "DIAGNOSIS"),
        ("fever", "SYMPTOM"),
        ("headache", "SYMPTOM"),
        ("paracetamol", "MEDICATION"),
        ("ibuprofen", "MEDICATION"),
        ("metformin", "MEDICATION"),
        ("aspirin", "MEDICATION"),
        ("atorvastatin", "MEDICATION"),
        ("chest x-ray", "PROCEDURE"),
        ("x-ray", "PROCEDURE"),
        ("mri", "PROCEDURE"),
        ("ct scan", "PROCEDURE"),
        ("biopsy", "PROCEDURE"),
        ("ecg", "PROCEDURE"),
        ("coronary angiography", "PROCEDURE"),
        ("blood glucose", "LAB"),
        ("cbc", "LAB"),
        ("hemoglobin", "LAB"),
        ("penicillin allergy", "ALLERGY"),
        ("blood pressure", "VITAL_SIGN"),
        ("heart rate", "VITAL_SIGN"),
        ("abnormal ecg findings", "CLINICAL_FINDING"),
        ("elevated blood glucose", "CLINICAL_FINDING"),
        ("high blood pressure", "CLINICAL_FINDING"),
    )

    @property
    def name(self):
        return "medspacy"

    def __init__(self):
        self._nlp = None

    def should_run(self, text: str, state: "PipelineState") -> bool:
        """
        Run MedSpaCy only if the text appears to contain clinical content.
        """

        if not text or not text.strip():
            return False

        cleaned = self.clean_text_of_labels(text)
        if not cleaned:
            return False

        text_lower = text.lower()

        if any(phrase in text_lower for phrase in ["chief complaint", "ct scan", "x-ray"]):
            return True

        words = set(re.findall(r"\b[a-z]+\b", text_lower))
        medspacy_keywords = {
            "patient", "doctor", "hospital", "diagnosis", "diagnoses", "complaint",
            "history", "symptom", "symptoms", "medication", "medicine", "drug", "prescription", "allergy",
            "procedure", "surgery", "lab", "laboratory", "blood", "glucose", "hemoglobin", "diabetes",
            "hypertension", "asthma", "fever", "headache", "pain", "mri", "ct", "biopsy", "findings", "clinical",
        }

        return not words.isdisjoint(medspacy_keywords)

    @property
    def nlp(self):
        if medspacy is None or TargetRule is None:
            raise RuntimeError(
                "MedSpaCy is not installed. Using deterministic clinical fallback."
            )

        if self._nlp is None:
            self._nlp = medspacy.load()

            if "medspacy_target_matcher" not in self._nlp.pipe_names:
                self._nlp.add_pipe(
                    "medspacy_target_matcher",
                    last=True,
                )

            target_matcher = self._nlp.get_pipe(
                "medspacy_target_matcher"
            )
            target_matcher.add([
                TargetRule(phrase, label)
                for phrase, label in self.TARGET_RULES
            ])

        return self._nlp

    def detect(
        self,
        text: str,
        page_number: int = 1,
    ) -> List[DetectionResult]:
        if not text or not text.strip():
            return []

        try:
            doc = self.nlp(text)
        except Exception as exc:
            logger.warning("MedSpaCy unavailable; using fallback rules: %s", exc)
            return self._detect_with_fallback_rules(text, page_number)

        detections = []

        for ent in doc.ents:
            if ent.label_ not in self.ALLOWED_LABELS:
                continue

            entity_value = " ".join(ent.text.split())

            detections.append(
                DetectionResult(
                    entity_type=ent.label_,
                    entity_value=entity_value,
                    confidence_score=self.DEFAULT_CONFIDENCE,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    page_number=page_number,
                    detector=self.name,
                    metadata={
                        "clinical": True,
                        "source": "TargetMatcher",
                        "model": "medspacy",
                        "resolved": True,
                    },
                )
            )

        detections.sort(key=lambda entity: entity.start_char)
        return detections

    def _detect_with_fallback_rules(
        self,
        text: str,
        page_number: int,
    ) -> List[DetectionResult]:
        detections: list[DetectionResult] = []

        rules = sorted(
            self.TARGET_RULES,
            key=lambda item: len(item[0]),
            reverse=True,
        )
        for phrase, label in rules:
            pattern = r"(?<!\w)" + re.escape(phrase).replace(r"\ ", r"\s+") + r"(?!\w)"
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                if self._overlaps(match.start(), match.end(), detections):
                    continue

                detections.append(
                    DetectionResult(
                        entity_type=label,
                        entity_value=" ".join(match.group(0).split()),
                        confidence_score=self.FALLBACK_CONFIDENCE,
                        start_char=match.start(),
                        end_char=match.end(),
                        page_number=page_number,
                        detector=self.name,
                        metadata={
                            "clinical": True,
                            "source": "fallback_rules",
                            "model": "deterministic",
                            "resolved": True,
                        },
                    )
                )

        detections.sort(key=lambda entity: entity.start_char)
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
