from __future__ import annotations

import re
from datetime import datetime

from modules.detection.entity_mapper import EntityMapper, PrivacyMapper
from modules.detection.models.detection_result import DetectionResult


class EntityValidator:
    """Deterministic validation gate shared by every detector.

    Detector confidence is never enough to make a candidate maskable.  The
    candidate must first have an exact source span and, for structured entity
    types, a value that satisfies the type's syntax and context rules.
    """

    DATE_TYPES = {
        "DATE",
        "DATE_TIME",
        "DATE_OF_BIRTH",
        "START_DATE",
        "VISIT_DATE",
    }
    IDENTIFIER_TYPES = {
        "CLAIM_NUMBER",
        "MEMBER_ID",
        "GROUP_NUMBER",
        "EOB_NUMBER",
    }
    BAD_IDENTIFIER_VALUES = {
        "claim",
        "claims",
        "group",
        "id",
        "member",
        "messages",
        "name",
        "no",
        "number",
        "processed",
        "received",
        "status",
        "subscriber",
        "request",
        "requests",
        "transfer",
        "cif",
        "branch",
        "branch code",
        "branch name",
    }
    GENERIC_SEMANTIC_TYPES = {
        "PERSON",
        "LOCATION",
        "ORGANIZATION",
        "DISEASE",
        "PROBLEM",
    }
    BAD_GENERIC_VALUES = {
        "certified mail",
        "ciso",
        "complete",
        "fsa",
        "health",
        "healthcare",
        "hipaa",
        "implemented",
        "medical",
        "medical record",
        "medication",
        "needed",
        "protected health information",
        "secured",
        "the health insurance portability",
        "ppo",
        "hmo",
        "epo",
        "pos",
        "individual",
        "family",
        "date of service",
        "level 4",
        "totals",
        "phi",
        "keep",
        "patient",
        "weight",
        "excluded services",
        "excluded services & other covered services",
        "excluded services & other covered services not covered: cosmetic",
        "covered services",
        "not covered",
        "cosmetic",
        "what you can do",
        "what happened",
        "what information was involved",
        "what we are doing",
        "for more information",
        "legal notice",
        "notice of data breach",
        "notice of data breach involving your health information",
        "comprehensive",
        "metabolic",
        "panel",
        "disclaimer & notice",
        "disclaimer",
        "request",
        "requests",
        "requested",
        "transfer",
        "transferred",
        "transferee",
        "captioned",
        "enclosed",
        "cif",
        "deposit",
        "term deposit",
        "faithfully",
        "yours faithfully",
        "sincerely",
        "regards",
        "branch name",
        "branch code",
        "account transfer",
        "home branch",
        "arrange",
        "understand",
        "caption",
        "dear",
        "sir",
        "madam",
        "please",
        "thank",
        "thanks",
        "account/accounts",
        "equipment & technical metadata",
        "technical metadata",
        "attending physician",
        "primary nurse",
        "discharge summary",
        "patient information",
        "admission & discharge",
        "clinical course & diagnosis",
        "procedures performed",
        "discharge medications",
        "laboratory & vital signs at discharge",
        "insurance & billing",
        "md",
        "rn",
        "sn",
        "npi",
        "blood pressure",
        "heart rate",
        "pulse",
        "spo2",
        "vital sign",
        "vital signs",
        "blood glucose",
        "glucose",
        "creatinine",
        "fasting blood glucose",
        "serum creatinine",
        "peak troponin",
        "peak troponin i",
        "troponin",
        "ecg",
        "ekg",
        "diagnosis",
        "diagnoses",
        "primary diagnosis",
        "secondary diagnoses",
        "clinical course",
        "procedures",
        "medications",
        "patient name",
        "member name",
        "subscriber name",
        "provider name",
        "physician name",
        "facility name",
        "service date",
        "billing date",
        "visit date",
        "visitdate",
        "eob date",
        "eobdate",
        "statement date",
        "statementdate",
        "allowed amount",
        "billed amount",
        "paid amount",
        "copay amount",
        "amount covered",
        "amountcovered",
        "amount billed",
        "amountbilled",
        "amount paid",
        "amountpaid",
        "total billed",
        "totalbilled",
        "total paid",
        "totalpaid",
        "procedure code",
        "procedurecode",
        "diagnosis code",
        "diagnosiscode",
        "insurance id",
        "insuranceid",
        "policy number",
        "policynumber",
        "claim number",
        "claimnumber",
        "group number",
        "groupnumber",
        "subscriber id",
        "subscriberid",
        "member id",
        "memberid",
        "claim status",
        "coverage type",
        "patient responsibility",
        "deductible amount",
        "para obtener ayuda",
        "ayuda en español",
        "atención al cliente",
        "language access services",
        "assistance services",
        "language assistance",
    }
    CLINICAL_VALUE_TYPES = {
        "abdominal pain": "SYMPTOM",
        "loose stools": "SYMPTOM",
        "complete blood count": "LAB",
        "cbc": "LAB",
        "comprehensive metabolic panel": "LAB",
        "cmp": "LAB",
        "celiac disease antibody panel": "LAB",
        "calprotectin test": "LAB",
        "calprotectin": "LAB",
    }
    ICD10_PATTERN = re.compile(
        r"^[A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?$",
        re.IGNORECASE,
    )
    CPT_PATTERN = re.compile(
        r"^(?:\d{5}|\d{4}[FTU]|[A-V]\d{4})$",
        re.IGNORECASE,
    )
    CURRENCY_PATTERN = re.compile(
        r"^\(?\s*[$€£₹]\s*\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\s*\)?$"
        r"|^\(?\s*[$€£₹]\s*\d+(?:\.\d{1,2})?\s*\)?$"
    )
    DATE_VALUE_PATTERN = (
        r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|\d{4}-\d{1,2}-\d{1,2}"
        r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}"
        r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4})"
    )
    TIME_PATTERN = re.compile(
        r"^(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?(?:\s*[AP]M)?$",
        re.IGNORECASE,
    )
    CPT_CONTEXT_PATTERN = re.compile(
        r"\b(?:cpt(?:\s*/\s*hcpcs)?|hcpcs|procedure\s+code|service\s+code|service\s+details|procedure\s+diagnosis|service\s+description\s+code)\b",
        re.IGNORECASE,
    )

    DATE_FORMATS = (
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%m/%d/%y",
        "%d/%m/%y",
    )
    DATE_TIME_FORMATS = tuple(
        f"{date_format} {time_format}"
        for date_format in DATE_FORMATS
        for time_format in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p")
    )

    _mapped_types = set(EntityMapper.ENTITY_MAPPING)
    _mapped_types.update(EntityMapper.ENTITY_MAPPING.values())
    _mapped_types.update(PrivacyMapper.MAPPING)
    KNOWN_ENTITY_TYPES = _mapped_types | {
        "BODY_PART",
        "CLINICAL_MEASUREMENT",
        "DOSAGE",
        "EOB_NUMBER",
        "GROUP_NUMBER",
        "ICD10_CODE",
        "MEMBER_ID",
        "NPI_NUMBER",
        "OTHER_PHI",
        "PO_BOX",
        "REFERENCE_NUMBER",
        "TAX_ID",
    }

    @classmethod
    def validate_candidates(
        cls,
        candidates: list[DetectionResult] | None,
        source_text: str,
    ) -> list[DetectionResult]:
        if not candidates:
            return []
        validated: list[DetectionResult] = []
        for candidate in candidates:
            result = cls.validate_candidate(candidate, source_text)
            if result is not None:
                validated.append(result)
        return validated

    @classmethod
    def validate_candidate(
        cls,
        candidate: DetectionResult,
        source_text: str,
    ) -> DetectionResult | None:
        if not cls._align_exact_span(candidate, source_text):
            return None

        raw_type = candidate.entity_type.strip().upper()
        entity_type = EntityMapper.ENTITY_MAPPING.get(raw_type, raw_type)
        if entity_type not in cls.KNOWN_ENTITY_TYPES:
            return None

        # Clean multiline candidate text for person/name candidates if second line is a structural label (e.g. "Linda Morgan\nFamily Member" -> "Linda Morgan")
        if "\n" in candidate.entity_value and entity_type in {"PERSON", "PATIENT", "DOCTOR"}:
            lines = [line.strip() for line in candidate.entity_value.splitlines() if line.strip()]
            if len(lines) > 1 and re.search(r"(?i)^(?:Family Member|DOB|Insurance|Diagnosis|Prescription|Relationship|Relative|Primary)", lines[1]):
                candidate.entity_value = lines[0]
                candidate.end_char = candidate.start_char + len(lines[0])

        value = candidate.entity_value.strip()
        original_type = entity_type
        structurally_validated = False
        semantic_key = cls._semantic_key(value)

        if cls._is_rejected_semantic_value(entity_type, value, semantic_key):
            return None

        clinical_type = cls.CLINICAL_VALUE_TYPES.get(semantic_key)
        if clinical_type and entity_type in cls.GENERIC_SEMANTIC_TYPES:
            entity_type = clinical_type
            structurally_validated = True

        if entity_type in {"ORGANIZATION", "INSURANCE_PROVIDER"}:
            if entity_type == "INSURANCE_PROVIDER":
                structurally_validated = True
            elif semantic_key == "medicare":
                entity_type = "INSURANCE_PROVIDER"
                structurally_validated = True
            elif re.search(
                r"\b(?:healthcare|health care|health system|medical center|hospital|clinic)\b",
                semantic_key,
            ):
                entity_type = "HEALTHCARE_ORGANIZATION"
                structurally_validated = True

        if entity_type == "POLICY_NUMBER" and not cls.has_label_context(
            source_text,
            candidate.start_char,
            "policy",
        ):
            if cls.has_label_context(
                source_text,
                candidate.start_char,
                r"(?:using|access|activation|enrollment|security)\s+code",
            ):
                entity_type = "ACCESS_CODE"
                structurally_validated = True
            else:
                return None

        if entity_type in cls.DATE_TYPES:
            if cls.is_currency(value):
                return None
            if entity_type == "DATE_TIME" and re.match(r"^\d{1,2}:\d{2}(?:\s*[APap][Mm])?$", value):
                preceding = source_text[max(0, candidate.start_char - 80):candidate.start_char].lower()
                following = source_text[candidate.end_char:min(len(source_text), candidate.end_char + 80)].lower()
                context_str = preceding + " " + value.lower() + " " + following
                if any(kw in context_str for kw in ["hours", "mon-fri", "monday", "friday", "saturday", "sunday", "am -", "pm -", "customer service", "open", "available"]):
                    return None
            if cls.is_icd10(value):
                entity_type = "ICD10_CODE"
                structurally_validated = True
            elif cls.is_cpt(value) and cls.has_cpt_context(
                source_text,
                candidate.start_char,
                candidate.end_char,
                candidate.metadata,
            ):
                entity_type = "CPT_CODE"
                structurally_validated = True
            elif not cls.is_real_date_or_time(value, entity_type):
                return None
            else:
                structurally_validated = True

        elif entity_type == "DATE_RANGE":
            if not cls.is_real_date_range(value):
                return None
            structurally_validated = True

        elif entity_type == "ICD10_CODE":
            if not cls.is_icd10(value):
                return None
            structurally_validated = True

        elif entity_type == "CPT_CODE":
            if not cls.is_cpt(value):
                return None
            if not cls.has_cpt_context(
                source_text,
                candidate.start_char,
                candidate.end_char,
                candidate.metadata,
            ):
                return None
            structurally_validated = True

        elif entity_type == "ACCESS_CODE":
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{5,30}", value):
                return None
            if not re.search(r"\d", value):
                return None
            structurally_validated = True

        elif entity_type == "TRACKING_NUMBER":
            digits = re.sub(r"\D", "", value)
            if not 12 <= len(digits) <= 22:
                return None
            structurally_validated = True

        elif entity_type == "REPORT_ID":
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{5,40}", value):
                return None
            if not re.search(r"\d", value):
                return None
            structurally_validated = True

        elif entity_type in {"PHONE_NUMBER", "US_PHONE_NUMBER", "FAX_NUMBER", "ORGANIZATION_CONTACT_INFO"}:
            digits_count = sum(c.isdigit() for c in value)
            if digits_count < 7:
                return None
            structurally_validated = True

        elif entity_type in cls.IDENTIFIER_TYPES:
            if not cls.is_identifier_value(value, entity_type):
                return None
            structurally_validated = True

        candidate.entity_type = entity_type
        candidate.canonical_type = entity_type
        candidate.privacy_category = PrivacyMapper.get_category(entity_type)

        if entity_type != original_type:
            candidate.metadata["original_entity_type"] = original_type
            candidate.metadata["reclassified_by"] = "deterministic_validator"

        candidate.metadata["deterministic_validation"] = (
            "passed" if structurally_validated else "not_applicable"
        )

        # Gemma confidence is self-reported.  Semantic Gemma-only candidates stay
        # below the automatic-review threshold unless a deterministic rule has
        # validated their type and value.
        if "gemma" in candidate.detector.lower() and not structurally_validated:
            candidate.confidence_score = min(candidate.confidence_score, 0.79)

        candidate.text = candidate.entity_value
        candidate.confidence = candidate.confidence_score
        candidate.start = candidate.start_char
        candidate.end = candidate.end_char
        return candidate

    @staticmethod
    def _normalized_text(value: str) -> str:
        return " ".join(value.split()).strip()

    @staticmethod
    def _semantic_key(value: str) -> str:
        return " ".join(
            re.sub(r"[^a-z0-9]+", " ", value.lower()).split()
        )

    @classmethod
    def _is_rejected_semantic_value(
        cls,
        entity_type: str,
        value: str,
        semantic_key: str | None = None,
    ) -> bool:
        if semantic_key is None:
            semantic_key = cls._semantic_key(value)
        # Strip bullet markers and special characters
        clean_value = re.sub(r"^(?:[•*\-]|â€¢|\d+\.|\w\.)\s*", "", value.strip(), flags=re.IGNORECASE)
        clean_semantic_key = clean_value.lower()

        # Reject single-word vague noise
        if clean_semantic_key in {"info", "patient info", "provider info"}:
            return True

        # Reject audit report verb phrases or multi-word sentence fragments for any entity candidate
        if re.search(r"\b(?:disclosed|exposed|repeated|references|documentation|noted|disclosures|compliance|cleartext|sections|outcomes|recommendation|strategy|protocols|policy|policies|portal|leak|sharing|tokenize|tracking|identifiers|plans|response|review|communication|distribution|redaction|prior)\b", clean_semantic_key):
            return True

        norm_type = entity_type.strip().upper().replace(" ", "_")
        if len(clean_value.split()) > 4 and norm_type != "ADDRESS":
            return True

        norm_type = entity_type.strip().upper().replace(" ", "_")
        semantic_types = cls.GENERIC_SEMANTIC_TYPES | {
            "HOSPITAL",
            "MEDICAL_FACILITY",
            "HEALTHCARE_ORGANIZATION",
            "VITAL_SIGN",
            "LAB",
            "PROCEDURE",
            "SYMPTOM",
            "CLINICAL_MEASUREMENT",
            "DIAGNOSIS",
            "DISEASE",
            "MEDICATION",
            "CLINICAL_NOTES",
            "FULL_NAME",
            "PERSON_NAME",
        }
        if norm_type not in semantic_types and not any(t in norm_type for t in ["PERSON", "NAME", "PHONE", "NOTE", "DIAGNOSIS"]):
            return False

        if clean_semantic_key in cls.BAD_GENERIC_VALUES:
            return True

        clean_key = re.sub(r"[^a-z0-9]", "", clean_value.lower())
        if clean_key in {
            "amountcovered", "amountbilled", "amountpaid", "totalbilled", "totalpaid",
            "visitdate", "procedurecode", "diagnosiscode", "insuranceid", "policynumber",
            "claimnumber", "groupnumber", "subscriberid", "memberid", "eobdate", "statementdate",
            "patient", "weight", "excludedservices", "coveredservices", "notcovered", "cosmetic",
            "whatyoucando", "whathappened", "whatwearedoing", "formoreinformation", "legalnotice",
            "excludedservicesothercoveredservicesnotcoveredcosmetic", "excludedservicesothercoveredservices"
        }:
            return True

        if re.search(r"\b(?:disclosed|exposed|repeated|references|documentation|noted|disclosures|compliance|cleartext|sections|outcomes|recommendation|strategy|protocols)\b", clean_semantic_key):
            return True

        if len(clean_value.split()) > 4 and entity_type in {"PERSON", "PATIENT", "DOCTOR", "PHONE_NUMBER", "US_PHONE_NUMBER", "SSN", "ORGANIZATION", "DISEASE"}:
            return True

        normalized = cls._normalized_text(clean_value)
        if re.match(r"^(?:[•*\-]|â€¢)\s*(?:keep|always|this|patient)\b", normalized, re.IGNORECASE):
            return True

        if re.fullmatch(r"(?i)(?:level\s*\d+|date of service|total|totals|phi|ppo|hmo|epo|pos|patient|weight|excluded services)", normalized):
            return True

        return False

    @classmethod
    def _align_exact_span(
        cls,
        candidate: DetectionResult,
        source_text: str,
    ) -> bool:
        start = candidate.start_char
        end = candidate.end_char
        if start < 0 or end > len(source_text) or start >= end:
            return False

        span = source_text[start:end]

        # Strip field label prefixes (e.g. "SSN: 123-45-6789" -> "123-45-6789")
        prefix_match = re.match(r"^(?:SSN|PATIENT NAME|PATIENT|NAME|CONTACT NUMBERS|PHONE|FAX|PHONE/FAX|ADDRESS|RE):\s*", span, re.IGNORECASE)
        if prefix_match:
            prefix_len = len(prefix_match.group(0))
            start = start + prefix_len
            span = source_text[start:end]

        leading = len(span) - len(span.lstrip())
        trailing = len(span) - len(span.rstrip())
        exact_value = span.strip()
        if cls._normalized_text(exact_value) != cls._normalized_text(
            candidate.entity_value
        ) and cls._normalized_text(exact_value) != cls._normalized_text(re.sub(r"^(?:SSN|PATIENT NAME|PATIENT|NAME|CONTACT NUMBERS|PHONE|FAX|PHONE/FAX|ADDRESS|RE):\s*", "", candidate.entity_value, flags=re.IGNORECASE)):
            return False

        candidate.start_char = start + leading
        candidate.end_char = end - trailing
        candidate.entity_value = source_text[
            candidate.start_char:candidate.end_char
        ]
        return bool(candidate.entity_value)

    @classmethod
    def is_currency(cls, value: str) -> bool:
        return bool(cls.CURRENCY_PATTERN.fullmatch(value.strip()))

    @classmethod
    def is_icd10(cls, value: str) -> bool:
        return bool(cls.ICD10_PATTERN.fullmatch(value.strip()))

    @classmethod
    def is_cpt(cls, value: str) -> bool:
        normalized = re.sub(r"(?i)^CPT\s*[:#-]?\s*", "", value.strip())
        return bool(cls.CPT_PATTERN.fullmatch(normalized))

    @classmethod
    def has_cpt_context(
        cls,
        source_text: str,
        start: int,
        end: int,
        metadata: dict | None = None,
    ) -> bool:
        if metadata and metadata.get("structured_table"):
            return True

        line_start = source_text.rfind("\n", 0, start) + 1
        line_end = source_text.find("\n", end)
        if line_end == -1:
            line_end = len(source_text)
        line = source_text[line_start:line_end]
        offset_start = start - line_start
        offset_end = end - line_start
        line_left = line[:offset_start]
        line_right = line[offset_end:]
        if (
            re.search(cls.DATE_VALUE_PATTERN, line_left, re.IGNORECASE)
            and re.search(r"\b[A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?\b", line_right, re.IGNORECASE)
        ):
            return True

        left = max(0, start - 180)
        right = min(len(source_text), end + 120)
        return bool(cls.CPT_CONTEXT_PATTERN.search(source_text[left:right]))

    @staticmethod
    def has_label_context(
        source_text: str,
        start: int,
        label_pattern: str,
        window: int = 100,
    ) -> bool:
        left = max(0, start - window)
        return bool(
            re.search(
                label_pattern,
                source_text[left:start],
                re.IGNORECASE,
            )
        )

    @classmethod
    def is_identifier_value(cls, value: str, entity_type: str) -> bool:
        normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
        if normalized in cls.BAD_IDENTIFIER_VALUES:
            return False
        if re.search(r"\s", value.strip()):
            return False
        if not re.fullmatch(r"[A-Za-z0-9-]{4,24}", value.strip()):
            return False
        if re.search(r"\d", value):
            return True
        prefixes = {
            "CLAIM_NUMBER": ("CLM",),
            "MEMBER_ID": ("MEM", "MBR"),
            "GROUP_NUMBER": ("GRP",),
            "EOB_NUMBER": ("EOB",),
        }
        return value.upper().startswith(prefixes.get(entity_type, ()))

    @classmethod
    def is_real_date_or_time(cls, value: str, entity_type: str) -> bool:
        normalized = " ".join(value.strip().replace("T", " ").split())
        normalized = re.sub(
            r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(r"\s+at\s+", " ", normalized, flags=re.IGNORECASE)

        if entity_type == "DATE_TIME" and cls.TIME_PATTERN.fullmatch(normalized):
            return True

        iso_value = normalized[:-1] + "+00:00" if normalized.endswith("Z") else normalized
        try:
            parsed = datetime.fromisoformat(iso_value)
            return cls._plausible_year(parsed.year)
        except ValueError:
            pass

        formats = cls.DATE_FORMATS
        if entity_type == "DATE_TIME":
            formats = (*cls.DATE_TIME_FORMATS, *cls.DATE_FORMATS)
        for date_format in formats:
            try:
                parsed = datetime.strptime(normalized, date_format)
            except ValueError:
                continue
            return cls._plausible_year(parsed.year)
        return False

    @classmethod
    def is_real_date_range(cls, value: str) -> bool:
        match = re.fullmatch(
            r"([A-Za-z]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2}),?\s+(\d{4})",
            value.strip(),
        )
        if not match:
            return False

        month_name, start_day, end_day, year = match.groups()
        try:
            month = datetime.strptime(month_name[:3], "%b").month
            start_date = datetime(int(year), month, int(start_day))
            end_date = datetime(int(year), month, int(end_day))
        except ValueError:
            return False
        return start_date <= end_date and cls._plausible_year(int(year))

    @staticmethod
    def _plausible_year(year: int) -> bool:
        return 1850 <= year <= datetime.now().year + 10
