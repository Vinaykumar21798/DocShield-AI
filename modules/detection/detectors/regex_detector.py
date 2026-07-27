import re

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult


class RegexDetector(BaseDetector):

    @property
    def name(self) -> str:
        return "Regex"

    PATTERNS = {

        "EMAIL":
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",

        "PHONE_NUMBER":
            r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b",

        "AADHAAR_NUMBER":
            r"\b\d{4}\s?\d{4}\s?\d{4}\b",

        "PAN_NUMBER":
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",

        "PASSPORT_NUMBER":
            r"\b[A-Z][0-9]{7}\b",

        "CREDIT_CARD":
            r"\b(?:\d[ -]?){13,16}\b",

        "IFSC_CODE":
            r"\b[A-Z]{4}0[A-Z0-9]{6}\b",

        "UPI_ID":
            r"\b[a-zA-Z0-9._-]{2,}@(ybl|ibl|okicici|oksbi|okaxis|paytm|apl|axl|upi)\b",

        "URL":
            r"\b(?:https?://|www\.)\S+\b",

        "IP_ADDRESS":
            r"\b(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}\b",

        "PIN_CODE":
            r"\b\d{6}\b",

        "SSN":
            r"\b\d{3}-\d{2}-\d{4}\b",

        "US_PHONE_NUMBER":
            r"\b(?:\+1[-. \t]?)?(?:\(\d{3}\)|\d{3})[-. \t]?\d{3}[-. \t]?\d{4}\b",

        "DATE_OF_BIRTH":
            r"\b(?:DOB|Date of Birth)[ \t]*[:\-]?[ \t]*(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})\b",

        "ZIP_CODE":
            r"\b\d{5}(?:-\d{4})?\b",

        "BANK_ACCOUNT":
            r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",

        "MRN":
            r"\bMRN[-: \t]?\d+\b",

        "CLAIM_NUMBER":
            r"\bCLM[-: \t]?[A-Z0-9-]+\b",

        "INSURANCE_ID":
            r"\b(?:INS|POL|POLICY|(?!CPT|DOB|SSN)[a-zA-Z]{3})[-: \t]?(?=[a-zA-Z0-9-]*\d)[a-zA-Z0-9-]{5,15}\b",

        "CPT_CODE":
            r"\b(?:CPT[-: \t]?)?\d{5}\b",

        "ICD10_CODE":
            r"\b[A-TV-Z][0-9]{2}(?:\.[A-Z0-9]{1,4})?\b",
        }
    ENTITY_PRIORITY = {
    "CREDIT_CARD": 100,
    "BANK_ACCOUNT": 98,
    "PASSPORT_NUMBER": 90,
    "PAN_NUMBER": 80,
    "AADHAAR_NUMBER": 70,
    "IFSC_CODE": 60,
    "UPI_ID": 50,
    "PHONE_NUMBER": 40,
    "EMAIL": 30,
    "URL": 20,
    "IP_ADDRESS": 10,
    "PIN_CODE": 5,
    "SSN": 95,
    "MRN": 92,
    "CLAIM_NUMBER": 91,
    "INSURANCE_ID": 90,
    "DATE_OF_BIRTH": 85,
    "US_PHONE_NUMBER": 45,
    "ZIP_CODE": 6,
    "CPT_CODE": 25,
    "ICD10_CODE": 24,
}

    CONTEXT = {

        "EMAIL": ["email", "mail"],

        "PHONE_NUMBER": ["phone", "mobile", "contact"],

        "AADHAAR_NUMBER": ["aadhaar", "uid"],

        "PAN_NUMBER": ["pan"],

        "PASSPORT_NUMBER": ["passport"],

        "CREDIT_CARD": ["card", "visa", "mastercard"],

        "BANK_ACCOUNT": ["iban", "bank", "account", "acc"],

        "IFSC_CODE": ["ifsc", "bank"],

        "UPI_ID": ["upi", "payment"],

        "IP_ADDRESS": ["ip"],

        "PIN_CODE": ["pin", "zipcode", "postal"],
        "SSN": ["ssn", "social security"],

        "US_PHONE_NUMBER": ["phone", "mobile", "contact"],

        "DATE_OF_BIRTH": ["dob", "date of birth"],

        "ZIP_CODE": ["zip", "zipcode", "postal"],

        "MRN": ["mrn", "medical record"],

        "CLAIM_NUMBER": ["claim"],

        "INSURANCE_ID": ["insurance", "policy"],

        "CPT_CODE": ["cpt"],

        "ICD10_CODE": ["diagnosis", "icd"],
    }

    def detect(
        self,
        text: str,
        page_number: int = 1,
    ) -> list[DetectionResult]:

        detections: list[DetectionResult] = []

        for entity, pattern in self.PATTERNS.items():

            for match in re.finditer(pattern, text):

                value = match.group()

                # Enforce contextual verification for CPT_CODE to prevent ZIP_CODE collisions
                if entity == "CPT_CODE":
                    if not self.has_context(entity, text, match.start()):
                        continue

                # Enforce contextual verification for ZIP_CODE to avoid matching street numbers
                if entity == "ZIP_CODE":
                    if not self.validate_zip_code(value, text, match.start()):
                        continue

                # Enforce contextual verification for PIN_CODE to avoid matching salaries/numbers
                if entity == "PIN_CODE":
                    if not self.validate_pin_code(value, text, match.start()):
                        continue

                confidence = self.calculate_confidence(
                    entity,
                    value,
                    text,
                    match.start(),
                )

                detections.append(
                    DetectionResult(
                        entity_type=entity,
                        entity_value=value,
                        confidence_score=confidence,
                        start_char=match.start(),
                        end_char=match.end(),
                        page_number=page_number,
                        detector=self.name,
                        metadata={
                            "method": "hybrid_regex",
                            "resolved": True,
                        },
                    )
                )

        # -----------------------------------------
        # Resolve overlapping matches
        # -----------------------------------------

        detections.sort(
            key=lambda entity: (
                -self.ENTITY_PRIORITY.get(entity.entity_type, 0),
                entity.start_char,
            )
        )

        filtered = []

        for entity in detections:

            if not self.has_overlap(
                entity.start_char,
                entity.end_char,
                filtered,
            ):
                filtered.append(entity)

        filtered.sort(
            key=lambda entity: entity.start_char
        )

        return filtered
    def has_overlap(
            self,
            start: int,
            end: int,
            accepted: list[DetectionResult],
        ) -> bool:
            """
            Check whether the current match overlaps with an
            already accepted higher-priority entity.
            """

            for entity in accepted:

                if start < entity.end_char and end > entity.start_char:
                    return True

            return False

    def calculate_confidence(
        self,
        entity: str,
        value: str,
        text: str,
        start: int,
    ) -> float:

        score = 0.40

        if self.has_context(entity, text, start):
            score += 0.30

        if self.validate(entity, value):
            score += 0.30

        return round(min(score, 1.0), 2)

    def has_context(
        self,
        entity: str,
        text: str,
        start: int,
    ) -> bool:

        window = 40

        left = max(0, start - window)
        right = min(len(text), start + window)

        context = text[left:right].lower()

        keywords = self.CONTEXT.get(entity, [])

        return any(keyword in context for keyword in keywords)

    def validate(
        self,
        entity: str,
        value: str,
    ) -> bool:

        if entity == "CREDIT_CARD":
            return self.luhn(value)

        if entity == "AADHAAR_NUMBER":
            return len(re.sub(r"\D", "", value)) == 12

        if entity == "PAN_NUMBER":
            return bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", value))

        if entity == "PHONE_NUMBER":
            return len(re.sub(r"\D", "", value)[-10:]) == 10
            
        if entity == "SSN":
            return bool(re.fullmatch(r"\d{3}-\d{2}-\d{4}", value))

        if entity == "US_PHONE_NUMBER":
            digits = re.sub(r"\D", "", value)
            if digits.startswith("1"):
                digits = digits[1:]
            return len(digits) == 10

        if entity == "ZIP_CODE":
            return bool(re.fullmatch(r"\d{5}(-\d{4})?", value))

        if entity == "MRN":
            return bool(re.search(r"\d+", value))

        if entity == "CLAIM_NUMBER":
            return len(value) > 6

        if entity == "INSURANCE_ID":
            return len(value) > 8

        if entity == "CPT_CODE":
            return len(value) == 5

        if entity == "ICD10_CODE":
            return bool(re.fullmatch(r"[A-TV-Z][0-9]{2}(\.[A-Z0-9]{1,4})?", value))

        return True

    def validate_zip_code(self, value: str, text: str, start: int) -> bool:
        """
        Ensures a 5-digit number is only classified as a ZIP_CODE if it is either:
        1. Preceded by a US state abbreviation (e.g. UT 12036, AP 81970).
        2. Or matches context keywords within a 40-character window.
        This prevents false positives on 5-digit street numbers (e.g. 00480 Cook Cove).
        """
        US_STATES = {
            "AL", "AK", "AS", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FM", "FL", "GA",
            "GU", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MH", "MD", "MA",
            "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND",
            "MP", "OH", "OK", "OR", "PW", "PA", "PR", "RI", "SC", "SD", "TN", "TX", "UT",
            "VT", "VI", "VA", "WA", "WV", "WI", "WY", "AE", "AA", "AP"
        }
        # Check if preceded by a US state abbreviation
        preceding = text[max(0, start - 10):start].strip()
        state_match = re.search(r'\b([A-Z]{2})\s*$', preceding)
        if state_match and state_match.group(1) in US_STATES:
            return True
        # Check if keyword context exists
        return self.has_context("ZIP_CODE", text, start)

    def validate_pin_code(self, value: str, text: str, start: int) -> bool:
        """
        Ensures a 6-digit number is only classified as a PIN_CODE if it is not a currency/salary
        and is either preceded by an Indian state name/abbreviation or matches pin context.
        """
        # Check if preceded by currency or salary markers
        preceding = text[max(0, start - 15):start].strip()
        if any(curr in preceding.lower() for curr in ["$", "₹", "rs", "rs.", "usd", "eur", "gbp", "salary"]):
            return False

        INDIAN_STATES = {
            "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DN", "DD", "DL", "GA", "GJ", "HR",
            "HP", "JK", "JH", "KA", "KL", "LA", "LD", "MP", "MH", "MN", "ML", "MZ", "NL",
            "OD", "PY", "PB", "RJ", "SK", "TN", "TS", "TR", "UP", "UK", "WB",
            "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa",
            "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka", "kerala",
            "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland",
            "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
            "uttar pradesh", "uttarakhand", "west bengal"
        }
        state_match = re.search(r'\b([A-Za-z]{2,15})\s*[-:\s]*$', preceding.lower())
        if state_match and state_match.group(1).upper() in INDIAN_STATES:
            return True

        # Check if keyword context exists
        return self.has_context("PIN_CODE", text, start)

    def luhn(
        self,
        number: str,
    ) -> bool:

        digits = re.sub(r"\D", "", number)

        total = 0

        reverse = digits[::-1]

        for i, d in enumerate(reverse):

            n = int(d)

            if i % 2 == 1:

                n *= 2

                if n > 9:
                    n -= 9

            total += n

        return total % 10 == 0