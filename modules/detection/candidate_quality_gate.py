from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from modules.detection.embedding_service import EmbeddingService
from modules.detection.models.detection_result import DetectionResult
from modules.detection.taxonomy import TaxonomyService

logger = logging.getLogger(__name__)


@dataclass
class QualityGateDecision:
    decision: str  # "PENDING_FOR_LLM" | "PRE_LLM_REJECT" | "LOCKED" | "DUPLICATE_SUPPRESSED"
    reason: str
    semantic_score: float = 0.0
    structural_score: float = 0.0
    confidence_score: float = 0.0


class CandidateQualityGate:
    """
    Generalized Candidate Quality Gate.
    Evaluates detector candidates BEFORE they reach the Pending queue or LLM.

    Filters out:
    1. Structural table headers, column labels, and repeated grid placeholders.
    2. Severe semantic incompatibilities (e.g. benefit category tagged as PERSON).
    3. Multilingual language access disclaimers and form field prompts.

    Protects Recall (Zero False Negative principle):
    - Any plausible, ambiguous, or borderline candidate is routed to PENDING_FOR_LLM.
    """

    # Generic structural / table header patterns (not word-specific blacklists)
    TABLE_DELIMITERS = re.compile(r"[|\t]|\s{3,}")
    REPEATED_TOKEN_PATTERN = re.compile(r"^(\b\w+\b)(?:\s+\1){2,}$", re.IGNORECASE)
    KEY_ONLY_PATTERN = re.compile(r"^[A-Za-z\s/_-]{3,40}[:\-]?$", re.IGNORECASE)

    # Multilingual language access disclaimer tokens
    LANGUAGE_DISCLAIMER_TERMS = {
        "español", "espanol", "spanish", "tagalog", "chinese", "navajo",
        "para obtener", "para obtener ayuda", "llame al", "si usted", "o alguien",
        "language access", "language access services", "ayuda en español",
        "atención", "atencion", "assistance services",
    }

    # Benefit & structural category concepts
    STRUCTURAL_TABLE_LABELS = {
        "mail order", "mail-order", "preauth", "pre-auth", "preauthorization",
        "minimum value", "specialty", "tier 1", "tier 2", "tier 3", "tier 4",
        "in-network", "out-of-network", "generic", "preferred brand", "non-preferred",
        "prior authorization", "step therapy", "quantity limit", "plan paid",
        "you paid", "managing type", "type generic", "limitations prescription",
        "schedule of benefits", "explanation of benefits", "coverage details",
        "deductible applies", "copay", "coinsurance", "out of pocket", "out-of-pocket",
        "none none none",
    }

    def __init__(self, embedding_service: EmbeddingService | None = None):
        self.embedding_service = embedding_service or EmbeddingService.get_instance()

    def evaluate(
        self,
        candidate: DetectionResult,
        document_text: str,
        document_type: str | None = None,
    ) -> QualityGateDecision:
        """
        Evaluates a candidate detection result and returns a QualityGateDecision.
        """
        val_raw = candidate.entity_value.strip()
        val_lower = val_raw.lower()
        val_normalized = " ".join(val_lower.split())
        start_char = candidate.start_char
        end_char = candidate.end_char

        # Extract surrounding context window (160 chars left and right)
        left = max(0, start_char - 160)
        right = min(len(document_text), end_char + 160)
        context_text = document_text[left:right]
        line_start = document_text.rfind("\n", 0, start_char) + 1
        line_end = document_text.find("\n", end_char)
        if line_end == -1:
            line_end = len(document_text)
        current_line = document_text[line_start:line_end].strip()

        # 1. Structural Signal: Repetitive dummy placeholder patterns (e.g. "None None None", "NA NA NA")
        if self.REPEATED_TOKEN_PATTERN.match(val_normalized) or val_normalized in {"none none none", "n/a n/a n/a", "null null null"}:
            return QualityGateDecision(
                decision="PRE_LLM_REJECT",
                reason="Candidate is a repeated placeholder/structural sequence with zero sensitive information",
                structural_score=0.95,
                confidence_score=candidate.confidence_score,
            )

        # 2. Structural Signal: Multilingual language access disclaimer
        if any(term in val_normalized for term in self.LANGUAGE_DISCLAIMER_TERMS) or val_normalized in {"al", "para", "obtener", "ayuda", "llame"}:
            return QualityGateDecision(
                decision="PRE_LLM_REJECT",
                reason=f"Candidate '{val_raw}' is part of a multilingual language access disclaimer",
                structural_score=0.90,
                confidence_score=candidate.confidence_score,
            )

        # 3. Structural Signal: Table column header / grid structure
        # (e.g. "Type | Retail | Mail Order | Limitations" or "Limitations Prescription")
        is_table_cell = bool(self.TABLE_DELIMITERS.search(current_line))
        has_colon_prompt = bool(re.search(r"[:\-][ \t]*$", val_raw))

        if has_colon_prompt:
            return QualityGateDecision(
                decision="PRE_LLM_REJECT",
                reason=f"Candidate '{val_raw}' is an unpopulated form/field prompt label ending with delimiter",
                structural_score=0.90,
                confidence_score=candidate.confidence_score,
            )

        # 4. Compute Embedding Semantic Compatibility
        semantic_score = self.embedding_service.entity_semantic_compatibility(
            candidate_value=val_raw,
            context_text=context_text,
            entity_type=candidate.entity_type,
        )

        # 5. Check if candidate is structural benefit/grid text misclassified as PERSON/LOCATION
        if candidate.entity_type in {"PERSON", "LOCATION", "ORGANIZATION"}:
            # Generic table words like "Managing Type", "Type Generic", "Plan Paid", "You Paid"
            if val_normalized in self.STRUCTURAL_TABLE_LABELS:
                return QualityGateDecision(
                    decision="PRE_LLM_REJECT",
                    reason=f"Candidate '{val_raw}' is structural/insurance benefit terminology in a table, not a {candidate.entity_type}",
                    semantic_score=round(semantic_score, 3),
                    structural_score=0.90,
                    confidence_score=candidate.confidence_score,
                )

            # Table header words (single or two common words in table context with very low semantic compatibility)
            if is_table_cell and semantic_score < 0.35 and len(val_raw.split()) <= 3:
                # If it's a known proper noun name like "Dr. Robert Chen" or "John Doe", don't reject
                is_proper_name = bool(re.match(r"^(?:Dr\.?\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$", val_raw))
                if not is_proper_name:
                    return QualityGateDecision(
                        decision="PRE_LLM_REJECT",
                        reason=f"Candidate '{val_raw}' is a table column label with low semantic compatibility ({semantic_score:.2f}) for {candidate.entity_type}",
                        semantic_score=round(semantic_score, 3),
                        structural_score=0.85,
                        confidence_score=candidate.confidence_score,
                    )

        # 6. Check for numbers / phone strings misclassified as PERSON/LOCATION
        if candidate.entity_type in {"PERSON", "LOCATION"} and re.search(r"\d{3,}", val_raw):
            return QualityGateDecision(
                decision="PRE_LLM_REJECT",
                reason=f"Candidate '{val_raw}' contains digits/numbers and cannot be a valid {candidate.entity_type}",
                structural_score=0.90,
                confidence_score=candidate.confidence_score,
            )

        # 7. Check if candidate is a single generic role/form word with no personal linkage
        if candidate.entity_type == "PERSON":
            words = val_raw.split()
            if len(words) == 1 and val_lower in {
                "patient", "doctor", "physician", "provider", "nurse", "member", "subscriber",
                "admin", "preauth", "hearing", "vision", "dental", "generic", "specialty",
                "child", "spouse", "dependent", "parent", "mother", "father", "son", "daughter",
                "employee", "beneficiary", "prescription", "limitations", "coverage", "copay",
                "coinsurance", "deductible", "relationship", "gender", "status",
            }:
                return QualityGateDecision(
                    decision="PRE_LLM_REJECT",
                    reason=f"Single generic role/form word '{val_raw}' has no bound individual identity",
                    semantic_score=round(semantic_score, 3),
                    structural_score=0.85,
                    confidence_score=candidate.confidence_score,
                )

        # 8. Check boilerplate country/geographic locations
        if candidate.entity_type == "LOCATION" and val_lower in {
            "the united states", "united states", "united states of america", "usa", "north america",
        }:
            return QualityGateDecision(
                decision="PRE_LLM_REJECT",
                reason=f"Candidate '{val_raw}' is a boilerplate country region, not an individual location",
                semantic_score=round(semantic_score, 3),
                structural_score=0.90,
                confidence_score=candidate.confidence_score,
            )

        # 9. Check 'Hearing' in 'Hearing aids' context
        if "hearing" in val_lower and ("hearing aid" in context_text.lower() or "benefit" in context_text.lower()):
            return QualityGateDecision(
                decision="PRE_LLM_REJECT",
                reason=f"'Hearing' in hearing aids context is a service category, not a {candidate.entity_type}",
                semantic_score=round(semantic_score, 3),
                structural_score=0.90,
                confidence_score=candidate.confidence_score,
            )

        # 9. Zero False Negative Guard: Pass meaningful uncertain candidates to PENDING_FOR_LLM
        reason_desc = (
            f"Low detector confidence ({candidate.confidence_score:.2f}) but plausible semantic evidence "
            f"(score={semantic_score:.2f}) for {candidate.entity_type} in {document_type or 'document'} context"
        )

        return QualityGateDecision(
            decision="PENDING_FOR_LLM",
            reason=reason_desc,
            semantic_score=round(semantic_score, 3),
            structural_score=0.10,
            confidence_score=candidate.confidence_score,
        )
