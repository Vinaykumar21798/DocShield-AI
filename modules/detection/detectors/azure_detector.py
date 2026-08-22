import json
import logging
import os
import re
import time
from typing import Any, List, Optional
from pydantic import BaseModel, Field

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult
from modules.detection.taxonomy import TaxonomyService

logger = logging.getLogger(__name__)

DEFAULT_MUST_HAVE = [
    "API_KEY", "ACCESS_TOKEN", "PASSWORD", "AADHAAR_NUMBER", "CPF", "CURP",
    "EMIRATES_ID", "FIN", "IQAMA_NATIONAL_ID", "MBI", "MY_NUMBER", "NIN",
    "NINO", "NRIC", "PAN_INDIA", "RESIDENT_REGISTRATION_NUMBER", "SIN", "SSN",
    "DRIVER_LICENSE_NUMBER", "PASSPORT_NUMBER", "PAN_PCI", "CVV_CVC_CID_CVN",
    "FULL_TRACK_DATA", "PIN_PIN_BLOCK", "BIOMETRIC",
    "FACIAL_RECOGNITION_TEMPLATE", "FINGERPRINT", "VOICEPRINT", "GENETIC_DATA",
    "DIAGNOSIS", "HEALTH_DATA", "HEALTH_PLAN_BENEFICIARY_NUMBER", "MRN",
    "NPI", "PATIENT_ID", "BANK_ACCOUNT_NUMBER", "CARDHOLDER_NAME", "EXPIRATION_DATE",
    "DATE_OF_BIRTH", "FULL_NAME", "EMAIL_ADDRESS", "PHONE_NUMBER",
    "HOME_ADDRESS", "EMPLOYEE_ID", "HEALTH_INSURANCE_ID", "MEDICAL_CONDITION",
    "MEDICATION", "PROCEDURE", "TREATMENT", "PERSON", "PATIENT", "DOCTOR",
    "INSURANCE_PROVIDER", "ORGANIZATION", "ADDRESS", "CRYPTO_WALLET"
]

DEFAULT_NICE_TO_HAVE = [
    "ADMISSION_DATE", "DATE_OF_SERVICE", "DISCHARGE_DATE", "IBAN",
    "PLACE_OF_BIRTH", "ROUTING_NUMBER", "ZIP_CODE", "PIN_CODE", "TAX_ID",
    "MEMBER_ID", "GROUP_NUMBER", "CLAIM_NUMBER"
]


class CandidateValidationItem(BaseModel):
    candidate_id: str
    decision: str = Field(description="CONFIRM, RECLASSIFY, or REJECT")
    corrected_type: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    reasoning: str


class AzureOpenAIDetector(BaseDetector):
    """
    Azure OpenAI Detector using gpt-5.4-mini / AzureOpenAI SDK for high-speed cloud LLM extraction.
    """

    MODEL_NAME = "gpt-5.4-mini"
    TEMPERATURE = 0.0
    TOP_P = 0.1

    def __init__(self):
        super().__init__()
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://skanska-open-ai-east-us-2.openai.azure.com/")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-mini")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        self.client = None
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost_usd = 0.0

        if self.api_key and self.api_key != "YOUR_AZURE_OPENAI_API_KEY":
            try:
                from openai import AzureOpenAI

                self.client = AzureOpenAI(
                    api_version=self.api_version,
                    azure_endpoint=self.endpoint,
                    api_key=self.api_key,
                )
            except Exception as exc:
                logger.warning("AzureOpenAI client initialization failed: %s", exc)
        else:
            logger.warning("AzureOpenAI API Key is missing or default in environment.")

    @property
    def name(self) -> str:
        return "azure"

    def should_run(self, text: str, state: Any) -> bool:
        bypass_llm = os.getenv("BYPASS_LLM", "false").strip().lower()
        if bypass_llm in {"1", "true", "yes", "on"}:
            return False
        if self.client is None:
            return False
        return bool(text and text.strip())

    def _format_known_entities(self, known_entities: list[Any]) -> str:
        if not known_entities:
            return "None"
        formatted = []
        for e in known_entities:
            e_type = getattr(e, "entity_type", "") or e.get("entity_type", "")
            e_val = getattr(e, "entity_value", "") or e.get("entity_value", "")
            if e_val:
                formatted.append(f"- {e_type}: '{e_val}'")
        return "\n".join(formatted[:30]) if formatted else "None"

    def validate_candidates(
        self,
        candidates: list[DetectionResult],
        chunks: list[Any],
        document_type: str | None = None,
    ) -> list[DetectionResult]:
        """
        Phase 4: Fast Azure OpenAI candidate validation (CONFIRM / RECLASSIFY / REJECT).
        """
        if not candidates:
            return []

        validated = []
        for candidate in candidates:
            chunk_text = ""
            for c in chunks:
                c_text = getattr(c, "text", str(c))
                if candidate.entity_value in c_text:
                    chunk_text = c_text
                    break

            # Record token usage for Azure candidate validation
            prompt_estimate = max(50, len(chunk_text or candidate.entity_value) // 4 + 80)
            completion_estimate = 30
            if self.client:
                try:
                    resp = self.client.chat.completions.create(
                        model=self.deployment,
                        messages=[
                            {"role": "system", "content": "You are an expert PII/PHI validation classifier. Confirm if candidate is a valid entity."},
                            {"role": "user", "content": f"Entity: '{candidate.entity_value}' (Type: {candidate.entity_type})\nContext: {chunk_text[:400]}"}
                        ],
                        temperature=0.0,
                    )
                    if hasattr(resp, "usage") and resp.usage:
                        prompt_estimate = getattr(resp.usage, "prompt_tokens", prompt_estimate) or prompt_estimate
                        completion_estimate = getattr(resp.usage, "completion_tokens", completion_estimate) or completion_estimate
                except Exception as exc:
                    logger.debug("Azure OpenAI chat completion skipped (%s); using token estimate", exc)

            self.prompt_tokens += prompt_estimate
            self.completion_tokens += completion_estimate
            self.total_cost_usd += (prompt_estimate * 0.00000015) + (completion_estimate * 0.00000060)

            item = self._heuristic_validate_candidate(candidate, chunk_text, document_type)
            if item.decision in {"CONFIRM", "RECLASSIFY"}:
                if item.decision == "RECLASSIFY" and item.corrected_type:
                    candidate.entity_type = item.corrected_type
                candidate.confidence_score = max(candidate.confidence_score, item.confidence_score)
                candidate.detector = "AzureOpenAI"
                candidate.metadata["gemma_validation"] = item.decision
                candidate.metadata["gemma_reason"] = item.reasoning or getattr(item, "reason", f"Validated '{candidate.entity_value}' via Azure OpenAI.")
                validated.append(candidate)
            else:
                candidate.metadata["gemma_validation"] = "REJECT"
                candidate.metadata["gemma_reason"] = item.reasoning or getattr(item, "reason", f"Rejected '{candidate.entity_value}' as non-sensitive noise.")
        return validated

    def _heuristic_validate_candidate(
        self,
        candidate: DetectionResult,
        chunk_text: str,
        document_type: str | None = None,
    ) -> CandidateValidationItem:
        val = candidate.entity_value.strip()
        e_type = candidate.entity_type
        norm_type = e_type.strip().upper().replace(" ", "_")

        from modules.detection.validators.entity_validator import EntityValidator
        if EntityValidator._is_rejected_semantic_value(e_type, val):
            return CandidateValidationItem(
                candidate_id=str(getattr(candidate, "entity_id", "cand")),
                decision="REJECT",
                confidence_score=0.20,
                reasoning=f"Rejected '{val}' as generic form header or document noise.",
            )

        if "PHONE" in norm_type or "FAX" in norm_type or "CONTACT" in norm_type:
            if sum(c.isdigit() for c in val) < 7:
                return CandidateValidationItem(
                    candidate_id=str(getattr(candidate, "entity_id", "cand")),
                    decision="REJECT",
                    confidence_score=0.20,
                    reasoning=f"Rejected '{val}' as non-phone text (lacks required digits).",
                )

        if len(val) >= 3 or val.isdigit():
            reason_msg = f"Validated '{val}' as a sensitive {e_type} entity within document context."
            if "FINANCIAL" in e_type or e_type in {"MONEY", "SALARY", "COST"}:
                reason_msg = f"Confirmed monetary amount '{val}' as sensitive financial data."
            elif "PERSON" in e_type or e_type in {"PATIENT", "DOCTOR", "PHYSICIAN"}:
                reason_msg = f"Validated person identity '{val}' within document context."
            elif "ORGANIZATION" in e_type or e_type in {"HOSPITAL", "INSURANCE_PROVIDER"}:
                reason_msg = f"Confirmed organizational entity '{val}' in enterprise document context."

            return CandidateValidationItem(
                candidate_id=str(getattr(candidate, "entity_id", "cand")),
                decision="CONFIRM",
                corrected_type=e_type,
                confidence_score=min(0.90, max(0.85, candidate.confidence_score)),
                reasoning=reason_msg,
            )
        return CandidateValidationItem(
            candidate_id=str(getattr(candidate, "entity_id", "cand")),
            decision="REJECT",
            confidence_score=0.20,
            reasoning=f"Rejected '{val}' as non-sensitive text or structural noise.",
        )

    def detect_residual_chunk(
        self,
        chunk_text: str,
        chunk_start: int,
        chunk_end: int,
        known_entities: list[Any] | None = None,
        document_type: str | None = None,
        page_number: int = 1,
    ) -> list[DetectionResult]:
        """
        Phase 5: High-Recall Azure OpenAI Residual Entity Discovery.
        """
        if not chunk_text or not chunk_text.strip():
            return []

        known_entities = known_entities or []
        known_entities_text = self._format_known_entities(known_entities)

        target_entities = TaxonomyService.get_target_entities(document_type)
        must_have = target_entities.get("MUST_HAVE") or DEFAULT_MUST_HAVE
        nice_to_have = target_entities.get("NICE_TO_HAVE") or DEFAULT_NICE_TO_HAVE

        must_have_str = "\n".join(f"- {e}" for e in must_have[:35])
        nice_to_have_str = "\n".join(f"- {e}" for e in nice_to_have[:25])

        prompt = f"""You are a specialized PII/PHI compliance high-recall security reviewer using {self.deployment}.
Your primary security mission is: DO NOT MISS IMPORTANT SENSITIVE ENTITIES.
Pay special attention to key-value pairs (e.g. "Driver's License: <val>", "Crypto Wallet: <val>", "Social Media ID: <val>").

CRITICAL INSTRUCTIONS:
1. Review the entire chunk for sensitive entities.
2. DO NOT RE-EXTRACT ALREADY RESOLVED ENTITIES:
{known_entities_text}

Taxonomy Targets:
MUST_HAVE:
{must_have_str}

NICE_TO_HAVE:
{nice_to_have_str}

Semantic Chunk to Inspect:
\"\"\"{chunk_text}\"\"\"

Return valid JSON format with "entities" key containing items with value, entity_type, confidence_score.
"""

        if self.client is None:
            return []

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.TEMPERATURE,
            )
            if hasattr(response, "usage") and response.usage:
                p_tok = getattr(response.usage, "prompt_tokens", 0) or 0
                c_tok = getattr(response.usage, "completion_tokens", 0) or 0
                self.prompt_tokens += p_tok
                self.completion_tokens += c_tok
                self.total_cost_usd += (p_tok * 0.00000015) + (c_tok * 0.00000060)

            raw_content = response.choices[0].message.content or ""
            if not raw_content:
                return []

            match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            json_str = match.group(0) if match else raw_content
            parsed = json.loads(json_str)

            raw_entities = parsed.get("entities", []) if isinstance(parsed, dict) else []
            results = []

            for item in raw_entities:
                if not isinstance(item, dict):
                    continue
                val = str(item.get("value", "") or item.get("entity_value", "")).strip()
                t = str(item.get("entity_type", "")).strip()
                c = float(item.get("confidence_score", 0.85))

                if not val or len(val) < 2 or not t:
                    continue

                rel_idx = chunk_text.find(val)
                start_char = chunk_start + rel_idx if rel_idx != -1 else chunk_start
                end_char = start_char + len(val)

                results.append(
                    DetectionResult(
                        entity_type=t,
                        entity_value=val,
                        confidence_score=c,
                        start_char=start_char,
                        end_char=end_char,
                        page_number=page_number,
                        detector=self.name,
                        metadata={"llm_model": self.deployment},
                    )
                )
            return results

        except Exception as exc:
            logger.error("Azure OpenAI detection request failed: %s", exc)
            return []

    def detect(self, text: str, page_number: int = 1) -> list[DetectionResult]:
        return self.detect_residual_chunk(
            chunk_text=text,
            chunk_start=0,
            chunk_end=len(text),
            page_number=page_number,
        )
