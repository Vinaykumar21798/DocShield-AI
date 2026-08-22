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
    Azure OpenAI Detector using gpt-5.4-mini / AzureOpenAI SDK for high-recall cloud LLM extraction.
    Covers global privacy frameworks (HIPAA, GDPR, PCI-DSS, GLBA, CCPA, and international identifiers).
    """

    MODEL_NAME = "gpt-5.4-mini"
    TEMPERATURE = 0.0
    TOP_P = 0.1

    COMMON_FORM_NOISE = {
        "request", "requests", "requested", "transfer", "transferred", "transferee",
        "captioned", "enclosed", "cif", "deposit", "term deposit", "faithfully",
        "yours faithfully", "sincerely", "regards", "branch name", "branch code",
        "account transfer", "home branch", "arrange", "understand", "caption",
        "dear", "sir", "madam", "please", "thank", "thanks", "hello", "hi",
    }

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
        Phase 5: Contextual LLM candidate validation (CONFIRM / RECLASSIFY / REJECT).
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

            prompt_estimate = max(50, len(chunk_text or candidate.entity_value) // 4 + 80)
            completion_estimate = 30
            if self.client:
                try:
                    resp = self.client.chat.completions.create(
                        model=self.deployment,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are a strict PII/PHI compliance validation classifier. "
                                    "Confirm if candidate is genuinely sensitive personal, health, or financial data. "
                                    "Reject generic English verbs/nouns (e.g. 'request', 'transfer', 'captioned', 'enclosed', 'notice')."
                                ),
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Candidate Entity: '{candidate.entity_value}' (Proposed Type: {candidate.entity_type})\n"
                                    f"Context: \"\"\"{chunk_text[:400]}\"\"\"\n\n"
                                    "Decide: CONFIRM, RECLASSIFY, or REJECT."
                                ),
                            },
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
        val_lower = val.lower().strip(" ,;:.[](){}\"'\t\n-")

        # 1. Reject common noise words and generic English verbs
        if val_lower in self.COMMON_FORM_NOISE:
            return CandidateValidationItem(
                candidate_id=str(getattr(candidate, "entity_id", "cand")),
                decision="REJECT",
                confidence_score=0.10,
                reasoning=f"Rejected '{val}' as common document verb/form noise.",
            )

        from modules.detection.validators.entity_validator import EntityValidator
        if EntityValidator._is_rejected_semantic_value(e_type, val):
            return CandidateValidationItem(
                candidate_id=str(getattr(candidate, "entity_id", "cand")),
                decision="REJECT",
                confidence_score=0.10,
                reasoning=f"Rejected '{val}' as generic form header or document noise.",
            )

        # 2. Phone validation: require minimum 7 digits
        if "PHONE" in norm_type or "FAX" in norm_type or "CONTACT" in norm_type:
            if sum(c.isdigit() for c in val) < 7:
                return CandidateValidationItem(
                    candidate_id=str(getattr(candidate, "entity_id", "cand")),
                    decision="REJECT",
                    confidence_score=0.10,
                    reasoning=f"Rejected '{val}' as non-phone text (lacks required digits).",
                )

        # 3. High-entropy, Financial, Government, Military, Tax & Structured Identifiers (Synthetic & Real)
        STRUCTURED_IDENTIFIER_KEYWORDS = [
            "ACCOUNT", "BANK", "IBAN", "ROUTING", "SWIFT", "BIC", "BRANCH",
            "SSN", "PASSPORT", "CARD", "PAN", "TAX", "TIN", "EIN", "ITIN",
            "AADHAAR", "MRN", "MILITARY", "DOD", "CAC", "SIN", "NINO",
            "DEVICE", "RX", "PRESCRIPTION", "LICENSE", "CREDIT", "DEBIT"
        ]
        if any(kw in norm_type for kw in STRUCTURED_IDENTIFIER_KEYWORDS):
            has_alnum = sum(c.isalnum() for c in val) >= 3
            if has_alnum:
                return CandidateValidationItem(
                    candidate_id=str(getattr(candidate, "entity_id", "cand")),
                    decision="CONFIRM",
                    corrected_type=e_type,
                    confidence_score=min(0.95, max(0.85, candidate.confidence_score)),
                    reasoning=f"Confirmed sensitive identifier '{val}' ({e_type}).",
                )

        # 4. Clinical & Healthcare Entities (Diagnoses, Medications, Procedures)
        CLINICAL_KEYWORDS = ["DIAGNOSIS", "MEDICATION", "PROCEDURE", "TREATMENT", "SYMPTOM", "CONDITION", "DRUG"]
        if any(kw in norm_type for kw in CLINICAL_KEYWORDS):
            if val_lower not in self.COMMON_FORM_NOISE and len(val) >= 2:
                return CandidateValidationItem(
                    candidate_id=str(getattr(candidate, "entity_id", "cand")),
                    decision="CONFIRM",
                    corrected_type=e_type,
                    confidence_score=min(0.92, max(0.85, candidate.confidence_score)),
                    reasoning=f"Confirmed clinical health entity '{val}' ({e_type}).",
                )

        # 5. Person Name validation
        if any(kw in norm_type for kw in ["PERSON", "PATIENT", "DOCTOR", "PHYSICIAN"]):
            if val_lower in self.COMMON_FORM_NOISE or (len(val.split()) == 1 and val.islower()):
                return CandidateValidationItem(
                    candidate_id=str(getattr(candidate, "entity_id", "cand")),
                    decision="REJECT",
                    confidence_score=0.10,
                    reasoning=f"Rejected '{val}' as non-name word.",
                )
            if len(val) >= 2 and any(c.isalpha() for c in val):
                return CandidateValidationItem(
                    candidate_id=str(getattr(candidate, "entity_id", "cand")),
                    decision="CONFIRM",
                    corrected_type=e_type,
                    confidence_score=min(0.92, max(0.85, candidate.confidence_score)),
                    reasoning=f"Validated person identity '{val}' within document context.",
                )

        # 6. Organizations, Clinics & Facilities
        if any(kw in norm_type for kw in ["ORGANIZATION", "HOSPITAL", "CLINIC", "PROVIDER", "INSURANCE"]):
            if val_lower in self.COMMON_FORM_NOISE or len(val) < 3:
                return CandidateValidationItem(
                    candidate_id=str(getattr(candidate, "entity_id", "cand")),
                    decision="REJECT",
                    confidence_score=0.10,
                    reasoning=f"Rejected '{val}' as non-organization word.",
                )
            return CandidateValidationItem(
                candidate_id=str(getattr(candidate, "entity_id", "cand")),
                decision="CONFIRM",
                corrected_type=e_type,
                confidence_score=min(0.90, max(0.85, candidate.confidence_score)),
                reasoning=f"Confirmed organization '{val}'.",
            )

        if len(val) >= 3 and any(c.isalnum() for c in val):
            return CandidateValidationItem(
                candidate_id=str(getattr(candidate, "entity_id", "cand")),
                decision="CONFIRM",
                corrected_type=e_type,
                confidence_score=min(0.88, max(0.80, candidate.confidence_score)),
                reasoning=f"Validated '{val}' as sensitive {e_type} entity.",
            )

        return CandidateValidationItem(
            candidate_id=str(getattr(candidate, "entity_id", "cand")),
            decision="REJECT",
            confidence_score=0.20,
            reasoning=f"Rejected '{val}' as non-sensitive text.",
        )

    def _locate_span_in_chunk(self, chunk_text: str, entity_value: str) -> tuple[int, int, str] | None:
        """
        Locates the exact start/end character offsets of entity_value in chunk_text.
        Handles exact matches as well as formatting/whitespace variations.
        Returns (rel_start, rel_end, verbatim_text_slice) or None.
        """
        if not entity_value or not chunk_text:
            return None

        # 1. Exact match
        idx = chunk_text.find(entity_value)
        if idx != -1:
            return idx, idx + len(entity_value), chunk_text[idx:idx + len(entity_value)]

        # 2. Case-insensitive exact match
        idx = chunk_text.lower().find(entity_value.lower())
        if idx != -1:
            return idx, idx + len(entity_value), chunk_text[idx:idx + len(entity_value)]

        # 3. Flexible whitespace & punctuation regex match
        escaped_tokens = [re.escape(tok) for tok in re.split(r"[\s\-_/]+", entity_value.strip()) if tok]
        if escaped_tokens:
            pattern = r"[\s\-_/]*".join(escaped_tokens)
            match = re.search(pattern, chunk_text, re.IGNORECASE)
            if match:
                return match.start(), match.end(), chunk_text[match.start():match.end()]

        return None

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
        Phase 4: High-Recall 6-Domain Global Regulatory & Compliance Residual Entity Discovery.
        """
        if not chunk_text or not chunk_text.strip():
            return []

        known_entities = known_entities or []
        known_entities_text = self._format_known_entities(known_entities)

        prompt = f"""You are an elite PII, PHI, Financial, and Government Data Protection Security Auditor.
Your primary mission is ZERO MISSED SENSITIVE ENTITIES across all global privacy regulations (HIPAA, PCI-DSS, GLBA, GDPR, CCPA/CPRA, State Privacy Laws, International Standards).

EXHAUSTIVE 6-DOMAIN TAXONOMY TARGETS:
1. HEALTHCARE & PHI: Patient Names, Date of Birth, Medical Record # (MRN), Health Plan/Member IDs, Diagnoses, Procedures, Medications, Prescriptions (Rx), Doctors, Hospitals, Medical Device Serials, Implant IDs.
2. FINANCIAL & PAYMENT CARDS: Credit & Debit Card Numbers (all formats/networks: Visa, Mastercard, Amex, Discover, RuPay, etc.), CVV/CVC, Expiration Dates, Bank Account Numbers (all country formats/spacings), IBAN, SWIFT/BIC, Branch Codes, Routing Numbers, Sort Codes, Crypto Wallet Addresses, Financial Balances.
3. GOVERNMENT, TAX & MILITARY: SSN, ITIN, EIN, Military ID / DoD ID / CAC, State Driver's Licenses, Passports, Aadhaar Numbers, PAN (India), Canadian SIN, UK NINO, EU National IDs, Tax IDs worldwide.
4. DIRECT & CONTACT PII: Full Names, Aliases, Street/Mailing Addresses, Phone Numbers (all country formats), Email Addresses, Employee IDs.
5. STATE-LAW SENSITIVE SPI: Precise Geolocation, Biometric Templates, Genetic Data, Racial/Ethnic Identifiers.
6. TECHNICAL CREDENTIALS: Passwords, API Keys, Access Tokens, Session Cookies, IP Addresses.

CRITICAL INSTRUCTIONS:
1. Review the entire chunk for sensitive entities. Pay special attention to key-value pairs (e.g. "A/c No: <val>", "Branch Code: <val>", "Card No: <val>", "DoD ID: <val>", "Rx: <val>", "Tax ID: <val>").
2. SYNTHETIC & TEST DATA SUPPORT: Include synthetic, test, or mock numbers in document context (e.g., mock 16-digit cards, fake SSNs, mock bank accounts). Extract any value acting as a sensitive identifier.
3. DO NOT EXTRACT GENERIC FORM WORDS OR VERBS (e.g. "Request", "Transfer", "Enclosed", "Captioned", "Faithfully", "Dear", "Sir", "Madam").
4. DO NOT RE-EXTRACT ALREADY RESOLVED ENTITIES:
{known_entities_text}
5. VERBATIM SUBSTRING MANDATE: You MUST extract the EXACT raw substring from the text as the 'value'. Do NOT reformat, strip spaces, or alter punctuation.

Text to Inspect:
\"\"\"{chunk_text}\"\"\"

Return a valid JSON object with the "entities" key containing items with "value", "entity_type", and "confidence_score":
{{"entities": [{{"value": "...", "entity_type": "...", "confidence_score": 0.90}}]}}
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
                c = float(item.get("confidence_score", 0.88))

                if not val or len(val) < 2 or not t:
                    continue

                if val.lower() in self.COMMON_FORM_NOISE:
                    continue

                span_match = self._locate_span_in_chunk(chunk_text, val)
                if not span_match:
                    continue

                rel_start, rel_end, verbatim_slice = span_match
                start_char = chunk_start + rel_start
                end_char = chunk_start + rel_end

                results.append(
                    DetectionResult(
                        entity_type=t,
                        entity_value=verbatim_slice,
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


