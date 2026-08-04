import logging
import re

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult

logger = logging.getLogger(__name__)


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
    "agreement id",
    "authorized signatory",
    "bank account",
    "claim number",
    "company information",
    "contact information",
    "customer name",
    "driving license",
    "emergency contact",
    "employee id",
    "enterprise service agreement",
    "footer",
    "gstin",
    "ifsc",
    "insurance company",
    "invoice number",
    "legal section",
    "medical information",
    "organization",
    "passport no",
    "policy number",
    "start date",
    "visit date",
    "witness",
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

PERSON_NAME_TOKEN = r"[A-Z][a-z]+(?:['-][A-Z][a-z]+)*"
PERSON_NAME_PATTERN = rf"{PERSON_NAME_TOKEN}(?:\s+{PERSON_NAME_TOKEN}){{1,3}}"
CREDENTIAL_SUFFIX_PATTERN = r"(?:DVM|MD|DO|DDS|PhD|CPA|Esq\.?|RN|NP|PA-C)"

PERSON_CONTEXT_PATTERNS = (
    re.compile(
        rf"\b(?:verify that|certify that|confirm that)\s+"
        rf"(?P<person>{PERSON_NAME_PATTERN})"
        rf"(?:\s+{CREDENTIAL_SUFFIX_PATTERN})?\s+"
        r"(?=is|was|has|currently|will|,)",
    ),
    re.compile(
        rf"(?im)^\s*(?:Customer Name|Witness|Authorized Signatory|Emergency Contact|Employee Name|Candidate Name|Staff Member)"
        rf"[ \t]*[:\-]?[ \t]*(?:\r?\n[ \t]*)?"
        rf"(?P<person>{PERSON_NAME_PATTERN})"
        rf"(?:\s+{CREDENTIAL_SUFFIX_PATTERN})?[ \t]*$",
    ),
)
NON_PERSON_FALLBACK_VALUES = FIELD_LABELS | TITLE_ONLY | {
    "employment verification",
    "hr department",
    "human resources",
}

ORG_FALLBACK_LABELS = FIELD_LABELS | {
    "company information",
    "contact information",
    "enterprise service agreement",
    "footer",
    "insurance",
    "insurance company",
    "legal section",
    "medical information",
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
        self._analyzer_unavailable = False

    @property
    def analyzer(self):
        if self._analyzer_unavailable:
            raise RuntimeError("Presidio analyzer is unavailable")

        if self._analyzer is None:
            try:
                import spacy

                has_local_model = any(
                    spacy.util.is_package(model_name)
                    for model_name in ("en_core_web_lg", "en_core_web_sm")
                )
                if not has_local_model:
                    raise RuntimeError(
                        "No local spaCy English model is installed"
                    )

                from presidio_analyzer import AnalyzerEngine, RecognizerRegistry

                registry = RecognizerRegistry()
                registry.load_predefined_recognizers()

                remove = [
                    "NhsRecognizer",
                    "UsBankRecognizer",
                    "UsLicenseRecognizer",
                ]

                for recognizer in list(registry.recognizers):
                    if recognizer.name in remove:
                        registry.remove_recognizer(recognizer.name)

                self._analyzer = AnalyzerEngine(
                    registry=registry,
                )
            except Exception:
                self._analyzer_unavailable = True
                raise

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

        try:
            results = self.analyzer.analyze(
                text=text,
                language="en",
                entities=self.SUPPORTED_ENTITIES,
            )
        except Exception as exc:
            logger.warning(
                "Presidio analyzer unavailable; using regex supplements only: %s",
                exc,
            )
            results = []

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

            value_lower = entity_value.lower()

            # Discard generic words flagged as PERSON, LOCATION, ORGANIZATION or DATE_TIME
            BLACKLIST = {
                "reschedule", "copay", "appointment", "visit", "date", "phone", "email", "address", "portal", "patient",
                "provider", "doctor", "hospital", "clinic", "amount", "billed", "covered", "cpt", "dob", "ssn", "insurance",
                "policy", "claim", "history", "results", "medication", "procedure", "diagnosis", "information", "details",
                "city", "state", "zip", "complimentary"
            }
            if value_lower in BLACKLIST:
                continue

            # Filter out loose/unlikely DATE_TIME matches (e.g. fractions like 5/10) with very low confidence
            if current_entity_type == "DATE_TIME" and result.score < 0.35:
                continue

            # Skip duration/generic date time matches
            if current_entity_type == "DATE_TIME":
                if any(duration_word in value_lower for duration_word in ["month", "year", "day", "hour", "minute", "week"]):
                    continue
                # Skip invalid 4-digit years (e.g. random numeric tracking code fragments)
                if value_lower.isdigit() and len(value_lower) == 4:
                    year_val = int(value_lower)
                    if year_val < 1900 or year_val > 2100:
                        continue

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
                            if hasattr(result, "recognition_metadata") and result.recognition_metadata is not None
                            else "Unknown"
                        ),
                    },
                )
            )

        self._add_supplemental_person_detections(text, page_number, detections, seen)

        # Supplementary Organization regex (case sensitive to match proper noun patterns)
        import re
        org_pattern = r'\b[A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*\s+(?:Corporation|Corp\b|Inc\b|Inc\.|Llc|Ltd|Company|Association|Group|Solutions)\b'
        for match in re.finditer(org_pattern, text):
            val = match.group()
            normalized_val = " ".join(val.split()).lower().rstrip(":")
            if normalized_val in ORG_FALLBACK_LABELS:
                continue

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

    def _add_supplemental_person_detections(
        self,
        text: str,
        page_number: int,
        detections: list[DetectionResult],
        seen: set[tuple[str, str, int, int]],
    ) -> None:
        for pattern in PERSON_CONTEXT_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group("person").strip()
                if not self._is_valid_person_fallback(value):
                    continue

                start = match.start("person")
                end = match.end("person")
                key = ("PERSON", value.lower(), start, end)
                if key in seen:
                    continue

                seen.add(key)
                detections.append(
                    DetectionResult(
                        entity_type="PERSON",
                        entity_value=value,
                        confidence_score=0.88,
                        start_char=start,
                        end_char=end,
                        page_number=page_number,
                        detector=self.name,
                        metadata={"recognizer": "PatternRecognizer_EmploymentPerson"},
                    )
                )

    @staticmethod
    def _is_valid_person_fallback(value: str) -> bool:
        normalized = " ".join(value.strip().split())
        normalized_key = normalized.lower()

        if normalized_key in NON_PERSON_FALLBACK_VALUES:
            return False

        if re.search(r"\d|@|://|www\.", normalized):
            return False

        if normalized_key.endswith(HOSPITAL_SUFFIXES):
            return False

        tokens = normalized.split()
        if not 2 <= len(tokens) <= 4:
            return False

        return all(
            re.fullmatch(PERSON_NAME_TOKEN, token)
            for token in tokens
        )
