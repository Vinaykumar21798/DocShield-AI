from __future__ import annotations

from typing import List

import medspacy
from medspacy.ner import TargetRule

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult


class MedSpaCyDetector(BaseDetector):

    DEFAULT_CONFIDENCE = 0.85

    #
    # Clinical entities we care about
    #
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

    @property
    def name(self):
        return "medspacy"

    def should_run(self, text: str, state: "PipelineState") -> bool:
        """
        Run MedSpaCy only if the text appears to contain
        clinical or medical content.
        """

        if not text or not text.strip():
            return False

        cleaned = self.clean_text_of_labels(text)
        if not cleaned:
            return False

        text_lower = text.lower()

        # Check special multi-word phrases or punctuated abbreviations
        if any(phrase in text_lower for phrase in ["chief complaint", "ct scan", "x-ray"]):
            return True

        # Find all alphanumeric words in the original raw text to check keywords
        words = set(re.findall(r'\b[a-z]+\b', text_lower))
        medspacy_keywords = {
            "patient", "doctor", "hospital", "diagnosis", "diagnoses", "complaint",
            "history", "symptom", "symptoms", "medication", "medicine", "drug", "prescription", "allergy",
            "procedure", "surgery", "lab", "laboratory", "blood", "glucose", "hemoglobin", "diabetes",
            "hypertension", "asthma", "fever", "headache", "mri", "ct", "biopsy", "findings", "clinical"
        }

        return not words.isdisjoint(medspacy_keywords)




    def __init__(self):
        self._nlp = None

    @property
    def nlp(self):

        if self._nlp is None:

            self._nlp = medspacy.load()

            #
            # Get TargetMatcher from pipeline
            #
            if "medspacy_target_matcher" not in self._nlp.pipe_names:
                self._nlp.add_pipe(
                    "medspacy_target_matcher",
                    last=True,
                )

            target_matcher = self._nlp.get_pipe(
                "medspacy_target_matcher"
            )

            target_rules = [
                # Problems / Diseases
                TargetRule("diabetes", "DISEASE"),
                TargetRule("hypertension", "DISEASE"),
                TargetRule("asthma", "DISEASE"),
                TargetRule("type 2 diabetes mellitus", "DISEASE"),

                # Symptoms
                TargetRule("fever", "SYMPTOM"),
                TargetRule("persistent fever", "SYMPTOM"),
                TargetRule("headache", "SYMPTOM"),
                TargetRule("chest pain", "SYMPTOM"),
                TargetRule("shortness of breath", "SYMPTOM"),

                # Medications
                TargetRule("paracetamol", "MEDICATION"),
                TargetRule("ibuprofen", "MEDICATION"),
                TargetRule("metformin", "MEDICATION"),
                TargetRule("aspirin", "MEDICATION"),
                TargetRule("atorvastatin", "MEDICATION"),

                # Procedures
                TargetRule("x-ray", "PROCEDURE"),
                TargetRule("chest x-ray", "PROCEDURE"),
                TargetRule("mri", "PROCEDURE"),
                TargetRule("ct scan", "PROCEDURE"),
                TargetRule("biopsy", "PROCEDURE"),
                TargetRule("ecg", "PROCEDURE"),
                TargetRule("coronary angiography", "PROCEDURE"),

                # Labs
                TargetRule("blood glucose", "LAB"),
                TargetRule("cbc", "LAB"),
                TargetRule("hemoglobin", "LAB"),

                # Allergies
                TargetRule("penicillin allergy", "ALLERGY"),

                # Vital Signs
                TargetRule("blood pressure", "VITAL_SIGN"),
                TargetRule("heart rate", "VITAL_SIGN"),

                # Clinical Findings
                TargetRule("abnormal ecg findings", "CLINICAL_FINDING"),
                TargetRule("elevated blood glucose", "CLINICAL_FINDING"),
                TargetRule("high blood pressure", "CLINICAL_FINDING"),
            ]

            target_matcher.add(target_rules)

        return self._nlp

    def detect(
        self,
        text: str,
        page_number: int = 1,
    ) -> List[DetectionResult]:

        doc = self.nlp(text)

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