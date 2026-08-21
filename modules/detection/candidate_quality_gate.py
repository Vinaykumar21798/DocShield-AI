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
    quality_decision: str  # "OBVIOUS_NOISE" | "LOW_RELEVANCE" | "PLAUSIBLE" | "AMBIGUOUS" | "HIGH_VALUE"
    action: str  # "REJECT_BEFORE_LLM" | "PENDING_FOR_LLM" | "LOCK"
    reason: str
    semantic_score: float = 0.0
    structural_score: float = 0.0
    confidence_score: float = 0.0
    llm_required: bool = True


class CandidateQualityGate:
    """
    Multi-signal Candidate Quality Gate.
    Evaluates detector candidates BEFORE sending them to Qwen contextual validation.

    Core Objectives:
    1. Filter out obvious table headers, transaction short-codes, database placeholders, and disclaimers.
    2. Reduce unnecessary expensive LLM calls while preserving high recall.
    3. Use embeddings as semantic relevance evidence, not final ground truth.
    4. Protect high-risk sensitive identifiers from aggressive filtering.
    """

    TABLE_DELIMITERS = re.compile(r"[|\t]|\s{3,}")
    REPEATED_TOKEN_PATTERN = re.compile(r"^(\b\w+\b)(?:\s+\1){2,}$", re.IGNORECASE)

    # Obvious database sentinels & placeholders
    DATABASE_SENTINELS = {
        "null", "n/a", "na", "none", "undefined", "dummy", "test",
        "null null null", "none none none", "n/a n/a n/a", "na na na",
    }

    # Multilingual disclaimer tokens
    LANGUAGE_DISCLAIMER_TERMS = {
        "español", "espanol", "spanish", "tagalog", "chinese", "navajo",
        "para obtener", "para obtener ayuda", "llame al", "si usted", "o alguien",
        "language access", "language access services", "ayuda en español",
        "atención", "atencion", "assistance services",
    }

    # Common table headers, transaction noise, and banking grid words
    TRANSACTION_TABLE_NOISE = {
        "description", "cin", "regd", "particulars", "narration", "chq no", "chq",
        "txn date", "txn", "to onl upi", "to onl", "onl upi", "airtelprep", "cr", "dr",
        "withdrawal", "deposit", "balance", "sl no", "sr no", "page no", "trans id",
        "instrument", "tran date", "value date", "debit", "credit", "closing balance",
        "opening balance", "available balance", "statement period", "account summary",
        "ref no", "cheque no", "upi/dr", "upi/cr", "imps/dr", "imps/cr", "neft/dr",
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
    }

    # High-risk identifier categories requiring conservative recall protection
    HIGH_VALUE_IDENTIFIERS = {
        "SSN", "TAX_ID", "PAN", "AADHAAR", "PASSPORT", "PASSPORT_NUMBER",
        "DRIVING_LICENSE", "BANK_ACCOUNT", "BANK_ACCOUNT_NUMBER", "CREDIT_CARD",
        "CARDHOLDER_NAME", "MEMBER_ID", "MEDICAL_RECORD_NUMBER", "MRN",
        "DIAGNOSIS", "MEDICATION", "PATIENT", "DOCTOR", "PHYSICIAN",
        "FINANCIAL_AMOUNT", "AMOUNT", "SALARY", "INVOICE_AMOUNT",
    }

    def __init__(self, embedding_service: EmbeddingService | None = None):
        self.embedding_service = embedding_service or EmbeddingService.get_instance()

    def evaluate(
        self,
        candidate: DetectionResult,
        document_text: str,
        document_type: str | None = None,
        chunk_text: str | None = None,
    ) -> QualityGateDecision:
        """
        Evaluates a candidate detection result with multi-signal evidence:
        - Entity criticality / high-risk protection
        - Semantic chunk context
        - Embedding semantic compatibility
        - Structural & noise cues
        - Document type awareness
        """
        val_raw = candidate.entity_value.strip()
        val_lower = val_raw.lower()
        val_normalized = " ".join(val_lower.split())
        start_char = candidate.start_char
        end_char = candidate.end_char
        entity_type = candidate.entity_type.upper()
        doc_type_norm = (document_type or "generic").lower()

        # 1. Resolve Semantic Context: prefer semantic chunk if provided, else enclosing paragraph
        if chunk_text:
            context_text = chunk_text
        elif candidate.metadata.get("chunk_text"):
            context_text = candidate.metadata["chunk_text"]
        else:
            para_start = document_text.rfind("\n\n", 0, start_char)
            para_start = 0 if para_start == -1 else para_start + 2
            para_end = document_text.find("\n\n", end_char)
            para_end = len(document_text) if para_end == -1 else para_end
            context_text = document_text[para_start:para_end]

        line_start = document_text.rfind("\n", 0, start_char) + 1
        line_end = document_text.find("\n", end_char)
        if line_end == -1:
            line_end = len(document_text)
        current_line = document_text[line_start:line_end].strip()

        # Compute Embedding Semantic Compatibility
        semantic_score = self.embedding_service.entity_semantic_compatibility(
            candidate_value=val_raw,
            context_text=context_text,
            entity_type=entity_type,
        )

        # Signal A: Repetitive dummy placeholder or database sentinel
        if (
            val_normalized in self.DATABASE_SENTINELS
            or self.REPEATED_TOKEN_PATTERN.match(val_normalized)
        ):
            return QualityGateDecision(
                decision="PRE_LLM_REJECT",
                quality_decision="OBVIOUS_NOISE",
                action="REJECT_BEFORE_LLM",
                reason=f"Candidate '{val_raw}' is a database sentinel or repeated placeholder with zero sensitive information",
                semantic_score=round(semantic_score, 3),
                structural_score=0.98,
                confidence_score=candidate.confidence_score,
                llm_required=False,
            )

        # Signal B: Multilingual language access disclaimer
        if any(term in val_normalized for term in self.LANGUAGE_DISCLAIMER_TERMS) or val_normalized in {"al", "para", "obtener", "ayuda", "llame"}:
            return QualityGateDecision(
                decision="PRE_LLM_REJECT",
                quality_decision="OBVIOUS_NOISE",
                action="REJECT_BEFORE_LLM",
                reason=f"Candidate '{val_raw}' is part of a multilingual language access disclaimer",
                semantic_score=round(semantic_score, 3),
                structural_score=0.92,
                confidence_score=candidate.confidence_score,
                llm_required=False,
            )

        # Signal C: Unpopulated form field prompt with trailing delimiter (e.g. "Name:", "DOB -")
        has_colon_prompt = bool(re.search(r"[:\-][ \t]*$", val_raw))
        if has_colon_prompt:
            return QualityGateDecision(
                decision="PRE_LLM_REJECT",
                quality_decision="OBVIOUS_NOISE",
                action="REJECT_BEFORE_LLM",
                reason=f"Candidate '{val_raw}' is an unpopulated form/field prompt label ending with delimiter",
                semantic_score=round(semantic_score, 3),
                structural_score=0.90,
                confidence_score=candidate.confidence_score,
                llm_required=False,
            )

        # Signal D: Table Column Header / Transaction Noise in Financial/Tabular context
        is_table_cell = bool(self.TABLE_DELIMITERS.search(current_line))
        if entity_type in {"PERSON", "ORGANIZATION", "LOCATION"}:
            # Transaction / accounting noise words
            if val_normalized in self.TRANSACTION_TABLE_NOISE or val_lower in self.TRANSACTION_TABLE_NOISE:
                return QualityGateDecision(
                    decision="PRE_LLM_REJECT",
                    quality_decision="OBVIOUS_NOISE",
                    action="REJECT_BEFORE_LLM",
                    reason=f"Candidate '{val_raw}' is a generic transaction/statement header token, not a {entity_type}",
                    semantic_score=round(semantic_score, 3),
                    structural_score=0.92,
                    confidence_score=candidate.confidence_score,
                    llm_required=False,
                )

            # Benefit category labels in healthcare tables
            if val_normalized in self.STRUCTURAL_TABLE_LABELS:
                return QualityGateDecision(
                    decision="PRE_LLM_REJECT",
                    quality_decision="OBVIOUS_NOISE",
                    action="REJECT_BEFORE_LLM",
                    reason=f"Candidate '{val_raw}' is structural/insurance benefit terminology in a table, not a {entity_type}",
                    semantic_score=round(semantic_score, 3),
                    structural_score=0.90,
                    confidence_score=candidate.confidence_score,
                    llm_required=False,
                )

            # Table header with low semantic score (< 0.35) and not a proper noun person name
            if is_table_cell and semantic_score < 0.35 and len(val_raw.split()) <= 3:
                is_proper_name = bool(re.match(r"^(?:Dr\.?\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-zA-Z.]+)+$", val_raw))
                if not is_proper_name:
                    return QualityGateDecision(
                        decision="PRE_LLM_REJECT",
                        quality_decision="OBVIOUS_NOISE",
                        action="REJECT_BEFORE_LLM",
                        reason=f"Candidate '{val_raw}' is a table column label with low semantic compatibility ({semantic_score:.2f}) for {entity_type}",
                        semantic_score=round(semantic_score, 3),
                        structural_score=0.85,
                        confidence_score=candidate.confidence_score,
                        llm_required=False,
                    )

        # Signal E: Digits/Numbers in PERSON or LOCATION
        if entity_type in {"PERSON", "LOCATION"} and re.search(r"\d{3,}", val_raw):
            return QualityGateDecision(
                decision="PRE_LLM_REJECT",
                quality_decision="OBVIOUS_NOISE",
                action="REJECT_BEFORE_LLM",
                reason=f"Candidate '{val_raw}' contains digits/numbers and cannot be a valid {entity_type}",
                semantic_score=round(semantic_score, 3),
                structural_score=0.90,
                confidence_score=candidate.confidence_score,
                llm_required=False,
            )

        # Signal F: Single generic role words with no bound individual identity
        if entity_type == "PERSON":
            words = val_raw.split()
            if len(words) == 1 and val_lower in {
                "patient", "doctor", "physician", "provider", "nurse", "member", "subscriber",
                "admin", "preauth", "hearing", "vision", "dental", "generic", "specialty",
                "child", "spouse", "dependent", "parent", "mother", "father", "son", "daughter",
                "employee", "beneficiary", "prescription", "limitations", "coverage", "copay",
                "coinsurance", "deductible", "relationship", "gender", "status", "user", "client",
            }:
                return QualityGateDecision(
                    decision="PRE_LLM_REJECT",
                    quality_decision="OBVIOUS_NOISE",
                    action="REJECT_BEFORE_LLM",
                    reason=f"Single generic role/form word '{val_raw}' has no bound individual identity",
                    semantic_score=round(semantic_score, 3),
                    structural_score=0.85,
                    confidence_score=candidate.confidence_score,
                    llm_required=False,
                )

        # Contextual label prompt linkage (e.g. "Name: Alice", "Patient: Bob")
        has_label_cue = bool(
            re.search(
                r"\b(?:name|patient|doctor|physician|employee|client|subscriber|member|holder|beneficiary|attn|contact|user|author)\s*[:\-]\s*$",
                document_text[max(0, start_char - 60):start_char],
                re.IGNORECASE,
            )
        )

        # Signal G: Proper Noun Person Name & Label Linkage Protection (Zero False Negative)
        if entity_type in {"PERSON", "PATIENT", "DOCTOR", "PHYSICIAN"}:
            is_proper_name = bool(re.match(r"^(?:Dr\.?\s+|Mr\.?\s+|Mrs\.?\s+|Ms\.?\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-zA-Z.]+)*$", val_raw))
            if (is_proper_name or has_label_cue) and val_lower not in {
                "patient", "doctor", "physician", "provider", "nurse", "member", "subscriber",
                "generic", "copay", "coinsurance", "deductible", "relationship", "gender", "status",
                "user", "client", "hospital", "clinic", "medical", "facility", "insurance",
            }:
                return QualityGateDecision(
                    decision="PENDING_FOR_LLM",
                    quality_decision="PLAUSIBLE",
                    action="PENDING_FOR_LLM",
                    reason=f"Proper noun name / labeled candidate '{val_raw}' preserved for contextual validation",
                    semantic_score=round(max(semantic_score, 0.70 if has_label_cue else 0.60), 3),
                    structural_score=0.10,
                    confidence_score=candidate.confidence_score,
                    llm_required=True,
                )

        # Signal H: High-Risk Identifier / Financial Amount Protection (Recall Safety Shield)
        if entity_type in self.HIGH_VALUE_IDENTIFIERS:
            return QualityGateDecision(
                decision="PENDING_FOR_LLM",
                quality_decision="HIGH_VALUE",
                action="PENDING_FOR_LLM",
                reason=f"High-value {entity_type} candidate '{val_raw}' preserved for contextual validation (score={semantic_score:.2f})",
                semantic_score=round(semantic_score, 3),
                structural_score=0.10,
                confidence_score=candidate.confidence_score,
                llm_required=True,
            )

        # Signal H: Low Relevance Filtering (< 0.20 on unanchored generic tokens)
        if semantic_score < 0.20 and not is_table_cell:
            return QualityGateDecision(
                decision="PRE_LLM_REJECT",
                quality_decision="LOW_RELEVANCE",
                action="REJECT_BEFORE_LLM",
                reason=f"Candidate '{val_raw}' has very low semantic relevance ({semantic_score:.2f}) to {entity_type} in {doc_type_norm} context",
                semantic_score=round(semantic_score, 3),
                structural_score=0.75,
                confidence_score=candidate.confidence_score,
                llm_required=False,
            )

        # Signal I: Contextually Plausible or Ambiguous Entity
        quality_category = "PLAUSIBLE" if semantic_score >= 0.40 else "AMBIGUOUS"
        reason_desc = (
            f"Candidate '{val_raw}' ({candidate.confidence_score:.2f}) has {quality_category.lower()} contextual evidence "
            f"(semantic score={semantic_score:.2f}) for {entity_type} in {doc_type_norm} context"
        )

        return QualityGateDecision(
            decision="PENDING_FOR_LLM",
            quality_decision=quality_category,
            action="PENDING_FOR_LLM",
            reason=reason_desc,
            semantic_score=round(semantic_score, 3),
            structural_score=0.15,
            confidence_score=candidate.confidence_score,
            llm_required=True,
        )
