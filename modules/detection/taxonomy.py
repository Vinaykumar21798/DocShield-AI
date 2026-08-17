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

    @classmethod
    def canonicalize(cls, raw_label: str) -> str:
        """
        Maps a detector-specific label or alias to its canonical entity name.
        """
        if not raw_label:
            return ""
        cleaned = raw_label.strip().upper()
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

            # Fallback search for partial match
            for ent_key, meta in policy_map.items():
                if canonical == ent_key or canonical in ent_key or ent_key in canonical:
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
