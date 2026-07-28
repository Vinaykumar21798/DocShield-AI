from presidio_analyzer import AnalyzerEngine
from presidio_analyzer import RecognizerRegistry

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult


FIELD_LABELS = {
    "patient",
    "consultant",
    "doctor",
    "hospital",
    "address",
    "email",
    "phone",
    "aadhaar",
    "pan",
    "passport",
    "diagnosis",
    "medication",
    "mrn",
    "upi",
    "account",
    "account holder",
}


HOSPITAL_SUFFIXES = (
    "hospital",
    "hospitals",
    "clinic",
    "medical center",
    "healthcare",
    "institute",
)


TITLE_ONLY = {
    "dr",
    "dr.",
    "mr",
    "mr.",
    "mrs",
    "mrs.",
    "ms",
    "ms.",
}


class PresidioDetector(BaseDetector):

    SUPPORTED_ENTITIES = [
        "PERSON",
        "LOCATION",
        "DATE_TIME",
        "ORGANIZATION",
    ]

    @property
    def name(self):
        return "presidio"

    def __init__(self):
        self._analyzer = None

    @property
    def analyzer(self):
        if self._analyzer is None:
            registry = RecognizerRegistry()
            registry.load_predefined_recognizers()

            REMOVE = [
                "NhsRecognizer",
                "UsBankRecognizer",
                "UsLicenseRecognizer",
            ]

            for recognizer in list(registry.recognizers):
                if recognizer.name in REMOVE:
                    registry.remove_recognizer(recognizer.name)

            self._analyzer = AnalyzerEngine(
                registry=registry,
            )
        return self._analyzer


    def should_run(self, text: str, state: "PipelineState") -> bool:
        """
        Presidio targets PERSON, LOCATION, DATE_TIME, ORGANIZATION.
        Runs if text contains proper noun structures, names titles, address suffixes, or date clues.
        """
        if not text or not text.strip():
            return False

        cleaned = self.clean_text_of_labels(text)
        if not cleaned:
            return False

        text_lower = cleaned.lower()

        # Mr, Ms, Dr, etc.
        titles = {"mr.", "mr", "mrs.", "mrs", "ms.", "ms", "dr.", "dr", "prof", "professor", "hon", "consultant"}
        if any(f" {title} " in f" {text_lower} " or text_lower.startswith(title) for title in titles):
            return True

        # Address indicator keywords
        address_keywords = {
            "street", "st.", "road", "rd.", "avenue", "ave.", "lane", "ln.", "boulevard", "blvd.",
            "zip", "postal", "address", "po box", "p.o. box", "city", "state", "country", "apartment", "apt", "suite"
        }
        if any(keyword in text_lower for keyword in address_keywords):
            return True

        # Org triggers
        org_keywords = {"inc.", "inc", "corp.", "corp", "ltd.", "ltd", "llc", "co.", "company", "pharmacy", "association"}
        if any(keyword in text_lower for keyword in org_keywords):
            return True

        # Date triggers
        date_keywords = {
            "dob", "birth", "date", "january", "february", "march", "april", "june", "july", "august",
            "september", "october", "november", "december", "jan", "feb", "mar", "apr", "jun", "jul",
            "aug", "sep", "oct", "nov", "dec"
        }
        if any(keyword in text_lower for keyword in date_keywords):
            return True

        # Capitalized proper noun pairs (e.g. John Doe, Microsoft Corp) that are not template headers
        import re
        for match in re.finditer(r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b', text):
            full_match = match.group(0).lower()
            if full_match not in {
                "claim number", "insurance id", "phone number", "aadhaar number",
                "pan number", "passport number", "date of birth", "pin code",
                "zip code", "ifsc code", "ip address", "us phone", "customer name",
                "account holder"
            }:
                return True

        return False


    def detect(
        self,
        text,
        page_number=1,
    ):

        results = self.analyzer.analyze(
            text=text,
            language="en",
            entities=self.SUPPORTED_ENTITIES,
        )

        detections = []
        seen = set()

        for result in results:

            entity_value = text[result.start:result.end].strip()

            # Reclassify PERSON/ORGANIZATION to LOCATION if preceded by address label
            preceding_context = text[max(0, result.start - 15):result.start].lower()
            current_entity_type = result.entity_type
            if "address" in preceding_context and current_entity_type in {"PERSON", "ORGANIZATION"}:
                current_entity_type = "LOCATION"

            # PERSON entities should never span multiple lines
            if current_entity_type == "PERSON":
                entity_value = entity_value.splitlines()[0].strip()

            # Skip empty values
            if not entity_value:
                continue

            value_lower = entity_value.lower()

            # Prevent false positives (Task 7)
            if (
                current_entity_type == "PERSON"
                and any(proc in value_lower for proc in ["chest x-ray", "ecg", "coronary angiography", "x-ray", "mri", "ct scan", "ct", "biopsy", "findings"])
            ):
                continue

            if (
                current_entity_type == "DATE_TIME"
                and value_lower == "daily"
            ):
                continue

            # Ignore field labels
            if (
                current_entity_type == "PERSON"
                and value_lower in FIELD_LABELS
            ):
                continue

            # Ignore title-only detections
            if (
                current_entity_type == "PERSON"
                and value_lower in TITLE_ONLY
            ):
                continue

            # Ignore hospitals classified as PERSON
            if (
                current_entity_type == "PERSON"
                and value_lower.endswith(HOSPITAL_SUFFIXES)
            ):
                continue

            # Remove duplicate detections
            key = (
                current_entity_type,
                value_lower,
                result.start,
                result.end,
            )

            if key in seen:
                continue

            seen.add(key)

            detections.append(
                DetectionResult(
                    entity_type=current_entity_type,
                    entity_value=entity_value,
                    confidence_score=float(result.score),
                    start_char=result.start,
                    end_char=result.end,
                    page_number=page_number,
                    detector=self.name,
                    metadata={
                        "recognizer": (
                            result.recognition_metadata.get(
                                "recognizer_name",
                                "Unknown",
                            )
                            if hasattr(result, "recognition_metadata")
                            else "Unknown"
                        ),
                    },
                )
            )

        # Supplementary Organization regex (case sensitive to match proper noun patterns)
        import re
        org_pattern = r'\b[A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*\s+(?:Corporation|Corp\b|Inc\b|Inc\.|Llc|Ltd|Company|Association|Group|Solutions)\b'
        for match in re.finditer(org_pattern, text):
            val = match.group()
            start, end = match.start(), match.end()
            key = ("ORGANIZATION", val.lower(), start, end)
            if key not in seen:
                seen.add(key)
                detections.append(
                    DetectionResult(
                        entity_type="ORGANIZATION",
                        entity_value=val,
                        confidence_score=0.85,
                        start_char=start,
                        end_char=end,
                        page_number=page_number,
                        detector=self.name,
                        metadata={"recognizer": "PatternRecognizer_Org"},
                    )
                )

        # Supplementary Address regex
        addr_pattern = r'\b(?:[Oo]ne|[Tt]wo|[Tt]hree|\d+)\s+[A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*\s+(?:Way|Street|St\b|St\.|Road|Rd\b|Rd\.|Avenue|Ave\b|Ave\.|Lane|Ln\b|Ln\.|Boulevard|Blvd\b|Blvd\.|Drive|Dr\b|Dr\.|Court|Ct\b|Ct\.)\b'
        for match in re.finditer(addr_pattern, text):
            val = match.group()
            start, end = match.start(), match.end()
            key = ("ADDRESS", val.lower(), start, end)
            if key not in seen:
                seen.add(key)
                detections.append(
                    DetectionResult(
                        entity_type="ADDRESS",
                        entity_value=val,
                        confidence_score=0.85,
                        start_char=start,
                        end_char=end,
                        page_number=page_number,
                        detector=self.name,
                        metadata={"recognizer": "PatternRecognizer_Addr"},
                    )
                )

        return detections