from __future__ import annotations

import logging
import re
from typing import Any

from modules.detection.taxonomy_data import (
    CANONICAL_ENTITY_MAPPING,
    DOCUMENT_POLICIES,
    GLOBAL_POLICY,
    DROP_ENTITIES,
)

logger = logging.getLogger(__name__)


class TaxonomyService:
    """
    Query interface for the PII/PHI Enterprise Entity Policy Taxonomy.
    Provides fast in-memory lookup for MUST_HAVE, NICE_TO_HAVE, and DROP
    entity policies across all supported document types.
    """

    _DOC_TYPE_ALIASES = {
        "medical_record": "Medical Record / Clinical Note",
        "clinical_note": "Medical Record / Clinical Note",
        "discharge_summary": "Discharge Summary",
        "prescription": "Prescription",
        "lab_report": "Lab Report / Pathology Report",
        "radiology_report": "Imaging / Radiology Report",
        "eob": "Explanation of Benefits (EOB) / Medical Claim",
        "medical_claim": "Explanation of Benefits (EOB) / Medical Claim",
        "health_insurance": "Health Insurance Policy / Benefits Document",
        "insurance_policy": "Health Insurance Policy / Benefits Document",
        "bank_statement": "Bank Statement",
        "tax_document": "Tax Document",
        "employee_record": "Employee Record / HR Application",
        "contract": "Contract / NDA / Legal Agreement",
        "nda": "Contract / NDA / Legal Agreement",
        "invoice": "Invoice / Purchase Order",
        "purchase_order": "Invoice / Purchase Order",
        "kyc": "KYC Document",
        "aml": "AML Document",
        "identity_document": "Identity Document (Passport / Driver License / National ID / Visa)",
        "passport": "Identity Document (Passport / Driver License / National ID / Visa)",
        "resume": "Resume / CV",
        "cv": "Resume / CV",
        "credit_card_statement": "Credit Card Statement",
        "loan_document": "Loan / Mortgage Document",
        "payroll": "Payroll / Salary Document",
        "system_log": "System Log / Incident Report / Security Report",
    }

    @classmethod
    def match_document_type(cls, doc_type_hint: str | None) -> str | None:
        """
        Matches a raw or shorthand document type hint to the canonical Excel document type.
        """
        if not doc_type_hint:
            return None

        normalized = doc_type_hint.strip()
        if normalized in DOCUMENT_POLICIES:
            return normalized

        # Check lowercase alias lookup
        key = re.sub(r"[\s/_\-]+", "_", normalized.lower())
        if key in cls._DOC_TYPE_ALIASES:
            return cls._DOC_TYPE_ALIASES[key]

        # Case-insensitive search across known document types
        for known_type in DOCUMENT_POLICIES:
            if normalized.lower() in known_type.lower() or known_type.lower() in normalized.lower():
                return known_type

        return None

    _DETECTOR_ENTITY_ALIASES = {
        "PATIENT": "FULL NAME / PERSON NAME",
        "PERSON": "FULL NAME / PERSON NAME",
        "DOCTOR": "TREATING PROVIDER NAME / NPI NUMBER",
        "PHYSICIAN": "TREATING PROVIDER NAME / NPI NUMBER",
        "NURSE": "TREATING PROVIDER NAME / NPI NUMBER",
        "HEALTHCARE_STAFF": "TREATING PROVIDER NAME / NPI NUMBER",
        "PROVIDER": "TREATING PROVIDER NAME / NPI NUMBER",
        "DISEASE": "DIAGNOSIS / MEDICAL CONDITION",
        "DIAGNOSIS": "DIAGNOSIS / MEDICAL CONDITION",
        "SYMPTOM": "DIAGNOSIS / MEDICAL CONDITION",
        "PROBLEM": "DIAGNOSIS / MEDICAL CONDITION",
        "PROCEDURE": "PROCEDURE CODE / DESCRIPTION",
        "MEDICATION": "MEDICATION / PRESCRIPTION DETAIL",
        "DOSAGE": "MEDICATION / PRESCRIPTION DETAIL",
        "ALLERGY": "ALLERGY INFORMATION",
        "VITAL_SIGN": "LAB TEST RESULT / VALUE",
        "CLINICAL_MEASUREMENT": "LAB TEST RESULT / VALUE",
        "LAB_RESULT": "LAB TEST RESULT / VALUE",
        "LAB": "LAB TEST RESULT / VALUE",
        "HOSPITAL": "COMPANY / EMPLOYER NAME",
        "CLINIC": "COMPANY / EMPLOYER NAME",
        "ORGANIZATION": "COMPANY / EMPLOYER NAME",
        "LOCATION": "STREET / MAILING ADDRESS",
        "ADDRESS": "STREET / MAILING ADDRESS",
        "ZIP_CODE": "GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)",
        "PIN_CODE": "GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)",
        "DATE_OF_BIRTH": "DATE OF BIRTH",
        "VISIT_DATE": "ADMISSION / DISCHARGE / SERVICE DATE",
        "START_DATE": "ADMISSION / DISCHARGE / SERVICE DATE",
        "DATE_TIME": "ADMISSION / DISCHARGE / SERVICE DATE",
        "DATE": "ADMISSION / DISCHARGE / SERVICE DATE",
        "SSN": "SOCIAL SECURITY NUMBER (SSN)",
        "MRN": "MEDICAL RECORD NUMBER (MRN)",
        "MEDICAL_RECORD_NUMBER": "MEDICAL RECORD NUMBER (MRN)",
        "MEMBER_ID": "HEALTH PLAN BENEFICIARY/MEMBER NUMBER",
        "GROUP_NUMBER": "GROUP / POLICY NUMBER",
        "POLICY_NUMBER": "HEALTH INSURANCE POLICY NUMBER",
        "CLAIM_NUMBER": "MEDICAL CLAIM NUMBER",
        "NPI_NUMBER": "TREATING PROVIDER NAME / NPI NUMBER",
        "NPI": "TREATING PROVIDER NAME / NPI NUMBER",
        "US_PHONE_NUMBER": "PHONE NUMBER",
        "PHONE_NUMBER": "PHONE NUMBER",
        "EMAIL": "EMAIL ADDRESS",
        "CREDIT_CARD": "PAYMENT CARD NUMBER (PAN)",
        "BANK_ACCOUNT": "BANK ACCOUNT NUMBER",
        "TAX_ID": "US TAX ID (EIN / ITIN)",
        "AADHAAR_NUMBER": "AADHAAR NUMBER (INDIA)",
        "PAN_NUMBER": "PERMANENT ACCOUNT NUMBER — INCOME TAX (INDIA)",
        "PASSPORT_NUMBER": "PASSPORT NUMBER",
        "DRIVING_LICENSE": "DRIVER'S LICENSE NUMBER",
    }

    @classmethod
    def canonicalize(cls, raw_label: str) -> str:
        """
        Maps a detector-specific label or alias to its canonical entity name.
        """
        if not raw_label:
            return ""
        cleaned = raw_label.strip().upper()
        if cleaned in cls._DETECTOR_ENTITY_ALIASES:
            return cls._DETECTOR_ENTITY_ALIASES[cleaned]
        return CANONICAL_ENTITY_MAPPING.get(cleaned, cleaned)

    @classmethod
    def get_priority(cls, entity_type: str, doc_type: str | None = None) -> str:
        """
        Returns the policy priority ('MUST_HAVE', 'NICE_TO_HAVE', or 'DROP')
        for the given entity type within the active document context.
        """
        canonical = cls.canonicalize(entity_type)
        matched_doc = cls.match_document_type(doc_type)

        if matched_doc and matched_doc in DOCUMENT_POLICIES:
            policy_map = DOCUMENT_POLICIES[matched_doc]
            if canonical in policy_map:
                return policy_map[canonical]["priority"]

            # Fallback search for token-boundary or full-word match
            canonical_tokens = set(re.findall(r"\b[A-Z0-9]+\b", canonical))
            for ent_key, meta in policy_map.items():
                ent_tokens = set(re.findall(r"\b[A-Z0-9]+\b", ent_key))
                if canonical == ent_key or (canonical_tokens and canonical_tokens.issubset(ent_tokens)):
                    return meta["priority"]

        # Check global policy
        if canonical in GLOBAL_POLICY:
            return GLOBAL_POLICY[canonical]["priority"]

        # If entity is in DROP registry
        if canonical in DROP_ENTITIES:
            return "DROP"

        # Default fallback for unlisted PII/PHI
        return "NICE_TO_HAVE"

    @classmethod
    def is_must_have(cls, entity_type: str, doc_type: str | None = None) -> bool:
        """Returns True if the entity is a MUST_HAVE priority."""
        return cls.get_priority(entity_type, doc_type) == "MUST_HAVE"

    @classmethod
    def is_nice_to_have(cls, entity_type: str, doc_type: str | None = None) -> bool:
        """Returns True if the entity is a NICE_TO_HAVE priority."""
        return cls.get_priority(entity_type, doc_type) == "NICE_TO_HAVE"

    @classmethod
    def is_drop(cls, entity_type: str, doc_type: str | None = None) -> bool:
        """Returns True if the entity is marked as DROP (noise/excluded)."""
        if not doc_type:
            return False
        return cls.get_priority(entity_type, doc_type) == "DROP"

    @classmethod
    def should_target(cls, entity_type: str, doc_type: str | None = None) -> bool:
        """
        Returns True if the entity should be targeted by detectors/LLM
        (MUST_HAVE or NICE_TO_HAVE), False if it is a DROP entity.
        """
        return not cls.is_drop(entity_type, doc_type)

    @classmethod
    def should_mask(cls, entity_type: str, doc_type: str | None = None) -> bool:
        """
        Returns True if the entity should be masked upon detection
        (MUST_HAVE and NICE_TO_HAVE are masked; DROP is not).
        """
        priority = cls.get_priority(entity_type, doc_type)
        return priority in {"MUST_HAVE", "NICE_TO_HAVE"}

    @classmethod
    def get_target_entities(cls, doc_type: str | None = None) -> dict[str, list[str]]:
        """
        Returns categorized lists of MUST_HAVE and NICE_TO_HAVE entities
        for the given document type, suitable for LLM prompt configuration.
        """
        matched_doc = cls.match_document_type(doc_type)
        must_have: list[str] = []
        nice_to_have: list[str] = []

        if matched_doc and matched_doc in DOCUMENT_POLICIES:
            for ent, meta in DOCUMENT_POLICIES[matched_doc].items():
                if meta["priority"] == "MUST_HAVE":
                    must_have.append(ent)
                elif meta["priority"] == "NICE_TO_HAVE":
                    nice_to_have.append(ent)
        else:
            for ent, meta in GLOBAL_POLICY.items():
                if meta["priority"] == "MUST_HAVE":
                    must_have.append(ent)
                elif meta["priority"] == "NICE_TO_HAVE":
                    nice_to_have.append(ent)

        return {
            "MUST_HAVE": sorted(list(set(must_have))),
            "NICE_TO_HAVE": sorted(list(set(nice_to_have))),
        }
