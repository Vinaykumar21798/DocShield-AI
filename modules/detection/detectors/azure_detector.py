import json
import logging
import os
import re
import time
from typing import Any, List, Optional
from pydantic import BaseModel, Field

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.usage import (
    AzureTokenRates,
    UsageLedger,
    extract_azure_usage,
)
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
    "MEMBER_ID", "GROUP_NUMBER", "CLAIM_NUMBER", "NATIONAL_ID", "SOCIAL_MEDIA_HANDLE"
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
        "statement", "statement notices", "account summary", "holder", "notices",
        "sb", "rd", "info", "details", "period", "balance", "amount", "total", "ending",
        "logo", "logo placeholder", "placeholder", "field discrepancy", "discrepancy",
        "field", "form title", "header", "footer", "page", "signature", "stamp", "label",
        # Communication / email / document structure noise
        "email thread", "email correspondence", "thread", "quoted replies", "original message",
        "retail loans division", "loans division", "loan application follow-up", "documents pending",
        "banking email thread", "confidential email record", "confidential record", "synthetic data",
        "not a real record", "page 1 of 1", "document type", "report no", "subject",
    }

    def __init__(self):
        super().__init__()
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://skanska-open-ai-east-us-2.openai.azure.com/")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-mini")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        self.client = None
        token_rates = AzureTokenRates.from_env()
        self._usage = UsageLedger(
            token_rates.calculate if token_rates is not None else None,
            cost_basis=(
                "azure_configured_token_rates"
                if token_rates is not None
                else None
            ),
        )

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

    @property
    def prompt_tokens(self) -> int:
        return self._usage.prompt_tokens

    @property
    def completion_tokens(self) -> int:
        return self._usage.completion_tokens

    @property
    def cached_prompt_tokens(self) -> Optional[int]:
        return self._usage.cached_prompt_tokens

    @property
    def total_cost_usd(self) -> Optional[float]:
        return self._usage.total_cost_usd

    @property
    def llm_duration_seconds(self) -> None:
        return None

    @property
    def cost_basis(self) -> Optional[str]:
        return self._usage.cost_basis

    @property
    def usage_complete(self) -> bool:
        return self._usage.is_complete

    @property
    def llm_model(self) -> str:
        return self.deployment

    def _record_usage(self, response: Any) -> None:
        usage = extract_azure_usage(response)
        if usage is None:
            self._usage.mark_incomplete()
            logger.warning(
                "Azure OpenAI response did not include token usage; "
                "usage and cost were not estimated."
            )
            return
        self._usage.record(usage)

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
        Uses structured JSON Chain-of-Thought reasoning for compliance verification.
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

            llm_item: Optional[CandidateValidationItem] = None

            if self.client:
                resp = None
                try:
                    system_prompt = (
                        "You are an elite PII/PHI Compliance Validation Engine for legal, healthcare, and enterprise documents, "
                        "operating under a zero-false-negative mandate. "
                        "Your mission is to evaluate candidate text spans in context against strict global privacy regulations (HIPAA, GDPR, PCI-DSS, GLBA, CCPA).\n\n"
                        "A wrongly REJECTed real entity is a compliance breach (the sensitive value ships unredacted). "
                        "A wrongly CONFIRMed candidate is low-cost -- it is only reviewed later. "
                        "For this reason, resolve any genuine ambiguity toward CONFIRM or RECLASSIFY, and reserve REJECT "
                        "for candidates you are clearly and specifically certain are non-sensitive noise.\n\n"
                        "For each candidate, analyze its surrounding context and decide:\n"
                        "1. 'CONFIRM': The candidate is a genuine sensitive personal, health, or financial entity matching the proposed type.\n"
                        "2. 'RECLASSIFY': The candidate is a genuine sensitive entity, but belongs to a different canonical type (specify in corrected_type).\n"
                        "3. 'REJECT': The candidate is NOT sensitive PII/PHI (e.g. document headers, email thread titles, form field labels, common English words, template noise) -- use only when certain, not merely unsure.\n\n"
                        "STRICT REJECTION RULES (Must return 'REJECT' -- these are the ONLY grounds for rejecting; anything else defaults to CONFIRM):\n"
                        "- Document/email structure headers (e.g. 'Email Thread', 'Retail Loans Division', 'Quoted Replies', 'Loan Application Follow-up', 'Documents Pending', 'Discharge Summary', 'Medical Record').\n"
                        "- Form labels and field names (e.g. 'Customer Name:', 'Patient ID:', 'Account No:', 'Date of Birth:', 'Signature').\n"
                        "- Generic English verbs, nouns, and greetings (e.g. 'Request', 'Transfer', 'Enclosed', 'Captioned', 'Dear', 'Sincerely', 'Regards').\n"
                        "- Document metadata and pagination (e.g. 'Page 1 of 1', 'Confidential Record', 'Synthetic Data', 'Report No').\n\n"
                        "CANONICAL ENTITY TYPES:\n"
                        "PERSON, PATIENT, DOCTOR, ORGANIZATION, HOSPITAL, ADDRESS, LOCATION, PHONE_NUMBER, EMAIL, DOCUMENT_ID, POLICY_NUMBER, BANK_ACCOUNT_NUMBER, PAN_NUMBER, SSN, DATE_TIME, FINANCIAL_AMOUNT, DIAGNOSIS, MEDICATION, PROCEDURE.\n\n"
                        "You MUST respond ONLY with a valid JSON object matching this schema:\n"
                        "{\n"
                        '  "thought": "Brief step-by-step reasoning evaluating the candidate and its context.",\n'
                        '  "decision": "CONFIRM" | "RECLASSIFY" | "REJECT",\n'
                        '  "corrected_type": "<CANONICAL_TYPE or null>",\n'
                        '  "confidence_score": 0.0 to 1.0,\n'
                        '  "reasoning": "Clear 1-sentence compliance audit rationale."\n'
                        "}"
                    )

                    user_content = (
                        f"Candidate Entity: '{candidate.entity_value}'\n"
                        f"Proposed Type: '{candidate.entity_type}'\n"
                        f"Surrounding Document Context:\n\"\"\"{chunk_text[:500]}\"\"\"\n\n"
                        "Return your validation decision in strict JSON format."
                    )

                    resp = self.client.chat.completions.create(
                        model=self.deployment,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        temperature=0.0,
                    )
                    self._record_usage(resp)

                    raw_resp = (resp.choices[0].message.content or "").strip()
                    json_match = re.search(r"\{.*\}", raw_resp, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(0))
                        dec = str(data.get("decision", "")).strip().upper()
                        if dec in {"CONFIRM", "RECLASSIFY", "REJECT"}:
                            corr_type = data.get("corrected_type")
                            conf = float(data.get("confidence_score", 0.88))
                            reason = str(data.get("reasoning") or data.get("thought") or f"Validated '{candidate.entity_value}' via Azure OpenAI.").strip()
                            llm_item = CandidateValidationItem(
                                candidate_id=str(getattr(candidate, "entity_id", "cand")),
                                decision=dec,
                                corrected_type=corr_type if dec == "RECLASSIFY" and corr_type else candidate.entity_type,
                                confidence_score=min(1.0, max(0.0, conf)),
                                reasoning=reason,
                            )
                except Exception as exc:
                    if resp is None:
                        self._usage.mark_incomplete()
                    logger.debug("Azure OpenAI chat completion failed/skipped (%s); falling back to heuristic", exc)

            # Use LLM decision if available; fallback to deterministic heuristic
            item = llm_item or self._heuristic_validate_candidate(candidate, chunk_text, document_type)

            # Deterministic Safety Gate: Hardcoded noise words MUST be rejected even if LLM confirmed them
            from modules.detection.validators.entity_validator import EntityValidator
            val_clean = candidate.entity_value.lower().strip(" ,;:.[](){}\"'\t\n-")
            if val_clean in self.COMMON_FORM_NOISE or EntityValidator._is_rejected_semantic_value(candidate.entity_type, candidate.entity_value):
                item = CandidateValidationItem(
                    candidate_id=str(getattr(candidate, "entity_id", "cand")),
                    decision="REJECT",
                    confidence_score=0.10,
                    reasoning=f"Rejected '{candidate.entity_value}' as generic form header or document noise.",
                )

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
            if val_lower in self.COMMON_FORM_NOISE or (len(val.split()) == 1 and (val.islower() or val_lower in self.COMMON_FORM_NOISE or len(val) <= 2)):
                return CandidateValidationItem(
                    candidate_id=str(getattr(candidate, "entity_id", "cand")),
                    decision="REJECT",
                    confidence_score=0.10,
                    reasoning=f"Rejected '{val}' as document form label or non-person word.",
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
            if val_lower in self.COMMON_FORM_NOISE or len(val) < 3 or (len(val.split()) == 1 and val_lower in self.COMMON_FORM_NOISE):
                return CandidateValidationItem(
                    candidate_id=str(getattr(candidate, "entity_id", "cand")),
                    decision="REJECT",
                    confidence_score=0.10,
                    reasoning=f"Rejected '{val}' as document form label or non-organization word.",
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
A missed sensitive entity is a compliance breach; a flagged candidate that turns out to be borderline
costs nothing since it is reviewed downstream. When you are unsure whether something qualifies, INCLUDE
it with a lower confidence_score rather than leaving it out. Read the chunk more than once: once for
clearly labeled values, and again for entities with no explicit label, values split across a line
break, abbreviated/shorthand forms, and repeated occurrences of an entity you already found elsewhere
in the same chunk (report every occurrence, not just the first).

EXHAUSTIVE 6-DOMAIN TAXONOMY TARGETS:
1. HEALTHCARE & PHI: Patient Names, Date of Birth, Medical Record # (MRN), Health Plan/Member IDs, Diagnoses, Procedures, Medications, Prescriptions (Rx), Doctors, Hospitals, Medical Device Serials, Implant IDs.
2. FINANCIAL & PAYMENT CARDS: Credit & Debit Card Numbers (all formats/networks: Visa, Mastercard, Amex, Discover, RuPay, etc.), CVV/CVC, Expiration Dates, Bank Account Numbers (all country formats/spacings), IBAN, SWIFT/BIC, Branch Codes, Routing Numbers, Sort Codes, Crypto Wallet Addresses, Financial Balances.
3. GOVERNMENT, TAX & MILITARY: SSN, ITIN, EIN, Military ID / DoD ID / CAC, State Driver's Licenses, Passports, Aadhaar Numbers, PAN (India), Canadian SIN, UK NINO, EU National IDs, Tax IDs worldwide.
4. DIRECT & CONTACT PII: Full Names, Aliases, Street/Mailing Addresses, Phone Numbers (all country formats), Email Addresses, Employee IDs, Online Handles/Usernames/Social Media IDs.
5. STATE-LAW SENSITIVE SPI: Precise Geolocation, Biometric Templates, Genetic Data, Racial/Ethnic Identifiers.
6. TECHNICAL CREDENTIALS: Passwords, API Keys, Access Tokens, Session Cookies, IP Addresses.

ORGANIZATION NAMES: extract company/organization names even when they have NO corporate suffix
(Inc, LLC, Corp, Ltd, etc.) and even when they look like a plain personal-name-style business name
(e.g. "Landry-Butler", "Mcdonald, Richardson and Johnson", "Alvarez Group") -- these are still
organizations, most often appearing after labels like "Insurance Info:", "Provider Info:",
"Employer:", or "Work History:". Do not require a suffix as a precondition to extract ORGANIZATION.

CRITICAL INSTRUCTIONS:
1. Review the entire chunk for sensitive entities. Pay special attention to key-value pairs (e.g. "A/c No: <val>", "Branch Code: <val>", "Card No: <val>", "DoD ID: <val>", "Rx: <val>", "Tax ID: <val>").
2. SYNTHETIC & TEST DATA SUPPORT: Include synthetic, test, or mock numbers in document context (e.g., mock 16-digit cards, fake SSNs, mock bank accounts). Extract any value acting as a sensitive identifier.
3. DO NOT EXTRACT GENERIC FORM WORDS OR VERBS (e.g. "Request", "Transfer", "Enclosed", "Captioned", "Faithfully", "Dear", "Sir", "Madam").
4. DO NOT RE-EXTRACT ALREADY RESOLVED ENTITIES:
{known_entities_text}
5. VERBATIM SUBSTRING MANDATE: You MUST extract the EXACT raw substring from the text as the 'value'. Do NOT reformat, strip spaces, or alter punctuation.
6. LABEL vs VALUE: for a "Label: value" pair, the entity is the VALUE after the colon/dash, never the
   label word itself. Do not extract field-label text (e.g. "Crypto Wallet", "Password", "Account
   Number") as if it were the sensitive value -- the label is metadata, not PII/PHI.

Text to Inspect:
\"\"\"{chunk_text}\"\"\"

Return a valid JSON object with the "entities" key containing items with "value", "entity_type", and "confidence_score":
{{"entities": [{{"value": "...", "entity_type": "...", "confidence_score": 0.90}}]}}
"""

        if self.client is None:
            return []

        response = None
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.TEMPERATURE,
            )
            self._record_usage(response)

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
            if response is None:
                self._usage.mark_incomplete()
            logger.error("Azure OpenAI detection request failed: %s", exc)
            return []

    def detect(self, text: str, page_number: int = 1) -> list[DetectionResult]:
        return self.detect_residual_chunk(
            chunk_text=text,
            chunk_start=0,
            chunk_end=len(text),
            page_number=page_number,
        )
