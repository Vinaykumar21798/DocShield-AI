"""Shared helpers for the isolated per-detector evaluation harness.

This module only reads existing files under storage/ and writes under
benchmarks/output/. It does not import or execute the production detection
service; each detector is invoked directly via its BaseDetector.detect().
"""

from __future__ import annotations

import re
from typing import Any

PAGE_SEPARATOR = "\n\n\f\n\n"

DOCUMENT_DIR = (
    "storage/runs/03b21b46-ea02-4d21-9429-331a9ca7456a"
    "/documents/3148c6b8-7198-45d1-951f-2a1dbde6e623"
)
CONTENT_PATH = f"{DOCUMENT_DIR}/extracted/content.txt"
REPORT_PATH = f"{DOCUMENT_DIR}/report.json"

OUTPUT_DIR = "benchmarks/output"
PREDICTIONS_DIR = f"{OUTPUT_DIR}/detector_predictions"


def load_content() -> str:
    with open(CONTENT_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def page_boundaries(text: str) -> list[tuple[int, int, int]]:
    """Return [(page_number, abs_start, abs_end)] from form-feed separators.

    Page numbers are 1-based. Separator length is included in the gap
    between page end and the next page start (offset math still maps any
    character position to its page unambiguously).
    """
    parts = text.split(PAGE_SEPARATOR)
    pages: list[tuple[int, int, int]] = []
    cursor = 0
    for index, part in enumerate(parts, start=1):
        start = cursor
        end = cursor + len(part)
        pages.append((index, start, end))
        cursor = end + len(PAGE_SEPARATOR)
    return pages


def page_of(offset: int, boundaries: list[tuple[int, int, int]]) -> int:
    """Return the page number containing an absolute character offset."""
    for page_number, start, end in boundaries:
        if start <= offset < end:
            return page_number
    return boundaries[-1][0] if boundaries else 1


def canonical_type_for(raw_type: str) -> str:
    """Map a detector's raw entity type to the shared gold vocabulary.

    Used ONLY for scoring so that equivalent labels from different detectors
    are comparable. The raw type is preserved on every prediction.
    """
    normalized = (raw_type or "").strip().upper()
    for canonical, aliases in CANONICAL_ALIASES.items():
        if normalized in aliases:
            return canonical
    return normalized


CANONICAL_ALIASES: dict[str, set[str]] = {
    "PERSON": {"PERSON", "PATIENT", "PROVIDER", "DOCTOR", "PHYSICIAN", "NURSE"},
    "DISEASE": {"DISEASE", "DIAGNOSIS", "PROBLEM", "MEDICAL_CONDITION"},
    "MEDICATION": {"MEDICATION", "DRUG"},
    "ALLERGY": {"ALLERGY"},
    "SYMPTOM": {"SYMPTOM"},
    "PROCEDURE": {"PROCEDURE"},
    "LAB": {"LAB", "LAB_RESULT", "LAB_TEST"},
    "CLINICAL_FINDING": {"CLINICAL_FINDING", "CLINICAL FINDING"},
    "CLINICAL_MEASUREMENT": {"CLINICAL_MEASUREMENT"},
    "VITAL_SIGN": {"VITAL_SIGN"},
    "DATE": {"DATE", "DATE_TIME", "START_DATE", "VISIT_DATE", "TIME"},
    "DATE_OF_BIRTH": {"DATE_OF_BIRTH", "DOB"},
    "DATE_RANGE": {"DATE_RANGE"},
    "EMAIL": {"EMAIL", "EMAIL_ADDRESS"},
    "URL": {"URL"},
    "IP_ADDRESS": {"IP_ADDRESS"},
    "US_PHONE_NUMBER": {"US_PHONE_NUMBER", "PHONE_NUMBER", "PHONE", "MOBILE"},
    "SSN": {"SSN"},
    "ADDRESS": {"ADDRESS", "PO_BOX"},
    "LOCATION": {"LOCATION", "CITY", "STATE", "COUNTRY"},
    "ORGANIZATION": {
        "ORGANIZATION",
        "ORG",
        "COMPANY",
        "HOSPITAL",
        "CLINIC",
        "INSTITUTE",
        "MEDICAL_FACILITY",
        "HEALTHCARE_ORGANIZATION",
        "INSURANCE_PROVIDER",
    },
    "POLICY_NUMBER": {"POLICY_NUMBER", "INSURANCE_ID"},
    "GROUP_NUMBER": {"GROUP_NUMBER"},
    "MEMBER_ID": {"MEMBER_ID"},
    "CLAIM_NUMBER": {"CLAIM_NUMBER"},
    "EOB_NUMBER": {"EOB_NUMBER"},
    "NPI_NUMBER": {"NPI_NUMBER"},
    "TAX_ID": {"TAX_ID", "EIN"},
    "MRN": {"MRN", "MEDICAL_RECORD_NUMBER"},
    "PATIENT_ID": {"PATIENT_ID"},
    "ZIP_CODE": {"ZIP_CODE", "PIN_CODE", "POSTAL_CODE"},
    "DOSAGE": {"DOSAGE"},
    "CPT_CODE": {"CPT_CODE"},
    "ICD10_CODE": {"ICD10_CODE"},
    "BANK_ACCOUNT_NUMBER": {"BANK_ACCOUNT", "BANK_ACCOUNT_NUMBER"},
    "CREDIT_CARD_NUMBER": {"CREDIT_CARD", "CREDIT_CARD_NUMBER"},
    "PAN_NUMBER": {"PAN_NUMBER"},
    "AADHAAR_NUMBER": {"AADHAAR", "AADHAAR_NUMBER"},
    "PASSPORT_NUMBER": {"PASSPORT", "PASSPORT_NUMBER"},
    "DRIVING_LICENSE": {"DRIVING_LICENSE", "DRIVING_LICENSE_NUMBER"},
    "IFSC_CODE": {"IFSC_CODE"},
    "UPI_ID": {"UPI_ID"},
    "GSTIN": {"GSTIN"},
    "INVOICE_NUMBER": {"INVOICE_NUMBER"},
    "EMPLOYEE_ID": {"EMPLOYEE_ID"},
    "DOCUMENT_ID": {"DOCUMENT_ID"},
    "REPORT_ID": {"REPORT_ID"},
    "SALARY": {"SALARY"},
}


def canonical_key(entity_type: str) -> str:
    """Normalize any entity type string for equality comparison."""
    return canonical_type_for(entity_type)


def normalize_value(value: str) -> str:
    """Normalize an entity value for equality comparison."""
    return " ".join((value or "").split()).casefold()


def spans_overlap(ax: int, ay: int, bx: int, by: int) -> bool:
    return ax < by and bx < ay


def overlap_ratio(ax: int, ay: int, bx: int, by: int) -> float:
    overlap = max(0, min(ay, by) - max(ax, bx))
    length = max(1, max(ay - ax, by - bx))
    return overlap / length


def asdict(entity: Any) -> dict[str, Any]:
    """Serialize a DetectionResult-like object to a plain dict."""
    if hasattr(entity, "model_dump"):
        return entity.model_dump()
    return dict(entity)


def write_json(path: str, payload: Any) -> None:
    import json
    import os

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, default=str)
