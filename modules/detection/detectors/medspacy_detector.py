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
    # These fallback matches come from the same small, exact phrase list used
    # by TargetMatcher, so they are safe for the normal auto-ready threshold.
    FALLBACK_CONFIDENCE = 0.85

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
        "CLINICAL_MEASUREMENT",
        "LAB_RESULT",
    }

    TARGET_RULES = (
        ("type 2 diabetes mellitus", "DISEASE"),
        ("diabetes", "DISEASE"),
        ("hypertension", "DISEASE"),
        ("asthma", "DISEASE"),
        ("hyperlipidemia", "DISEASE"),
        ("hypercholesterolemia", "DISEASE"),
        ("persistent fever", "SYMPTOM"),
        ("shortness of breath", "SYMPTOM"),
        ("chest pain", "SYMPTOM"),
        ("abdominal pain", "SYMPTOM"),
        ("loose stools", "SYMPTOM"),
        ("back pain", "DIAGNOSIS"),
        ("fever", "SYMPTOM"),
        ("headache", "SYMPTOM"),
        ("paracetamol", "MEDICATION"),
        ("ibuprofen", "MEDICATION"),
        ("metformin", "MEDICATION"),
        ("aspirin", "MEDICATION"),
        ("lisinopril", "MEDICATION"),
        ("atorvastatin", "MEDICATION"),
        ("lipitor", "MEDICATION"),
        ("zocor", "MEDICATION"),
        ("synthroid", "MEDICATION"),
        ("crestor", "MEDICATION"),
        ("align", "MEDICATION"),
        ("dicyclomine", "MEDICATION"),
        ("probiotic", "MEDICATION"),
        ("amoxicillin", "MEDICATION"),
        ("omeprazole", "MEDICATION"),
        ("gabapentin", "MEDICATION"),
        ("levothyroxine", "MEDICATION"),
        ("ozempic", "MEDICATION"),
        ("metoprolol", "MEDICATION"),
        ("losartan", "MEDICATION"),
        ("hydrochlorothiazide", "MEDICATION"),
        ("simvastatin", "MEDICATION"),
        ("sertraline", "MEDICATION"),
        ("prednisone", "MEDICATION"),
        ("doxycycline", "MEDICATION"),
        ("ciprofloxacin", "MEDICATION"),
        ("clopidogrel", "MEDICATION"),
        ("eliquis", "MEDICATION"),
        ("xarelto", "MEDICATION"),
        ("januvia", "MEDICATION"),
        ("farxiga", "MEDICATION"),
        ("jardiance", "MEDICATION"),
        ("humira", "MEDICATION"),
        ("keytruda", "MEDICATION"),
        ("dupixent", "MEDICATION"),
        ("adderall", "MEDICATION"),
        ("vyvanse", "MEDICATION"),
        ("warfarin", "MEDICATION"),
        ("tramadol", "MEDICATION"),
        ("albuterol", "MEDICATION"),
        ("montelukast", "MEDICATION"),
        ("brilinta", "MEDICATION"),
        ("chest x-ray", "PROCEDURE"),
        ("x-ray", "PROCEDURE"),
        ("mri", "PROCEDURE"),
        ("ct scan", "PROCEDURE"),
        ("biopsy", "PROCEDURE"),
        ("ecg", "PROCEDURE"),
        ("coronary angiography", "PROCEDURE"),
        ("blood glucose", "LAB"),
        ("complete blood count", "LAB"),
        ("cbc", "LAB"),
        ("hemoglobin", "LAB"),
        ("hemoglobin a1c", "LAB"),
        ("a1c", "LAB"),
        ("comprehensive metabolic panel (cmp)", "LAB"),
        ("comprehensive metabolic panel", "LAB"),
        ("lipid panel", "LAB"),
        ("total cholesterol", "LAB"),
        ("hdl", "LAB"),
        ("ldl", "LAB"),
        ("triglycerides", "LAB"),
        ("celiac disease antibody panel", "LAB"),
        ("calprotectin test", "LAB"),
        ("calprotectin", "LAB"),
        ("penicillin allergy", "ALLERGY"),
        ("abnormal ecg findings", "CLINICAL_FINDING"),
        ("elevated blood glucose", "CLINICAL_FINDING"),
        ("high blood pressure", "CLINICAL_FINDING"),
        ("irritable bowel syndrome", "DISEASE"),
        ("acute non-st elevation myocardial infarction", "DIAGNOSIS"),
        ("myocardial infarction", "DIAGNOSIS"),
        ("percutaneous coronary intervention", "PROCEDURE"),
        ("transthoracic echocardiogram", "PROCEDURE"),
        ("138/85 mmhg", "VITAL_SIGN"),
        ("7.4%", "CLINICAL_MEASUREMENT"),
        ("7.2%", "CLINICAL_MEASUREMENT"),
        ("193 mg/dl", "CLINICAL_MEASUREMENT"),
        ("112 mg/dl", "CLINICAL_MEASUREMENT"),
        ("42 mg/dl", "CLINICAL_MEASUREMENT"),
        ("195 mg/dl", "CLINICAL_MEASUREMENT"),
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

        self._add_fallback_rule_detections(
            text,
            page_number,
            detections,
            source="target_rules_supplement",
        )
        detections.sort(key=lambda entity: entity.start_char)
        return detections

    def _detect_with_fallback_rules(
        self,
        text: str,
        page_number: int,
    ) -> List[DetectionResult]:
        detections: list[DetectionResult] = []
        self._add_fallback_rule_detections(
            text,
            page_number,
            detections,
            source="fallback_rules",
        )
        detections.sort(key=lambda entity: entity.start_char)
        return detections

    def _add_fallback_rule_detections(
        self,
        text: str,
        page_number: int,
        detections: list[DetectionResult],
        source: str,
    ) -> None:
        rules = sorted(
            self.TARGET_RULES,
            key=lambda item: len(item[0]),
            reverse=True,
        )
        for phrase, label in rules:
            escaped_terms = [re.escape(term) for term in phrase.split()]
            pattern = r"(?<!\w)" + r"\s+".join(escaped_terms) + r"(?!\w)"
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
                            "source": source,
                            "model": "deterministic",
                            "resolved": True,
                        },
                    )
                )

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
