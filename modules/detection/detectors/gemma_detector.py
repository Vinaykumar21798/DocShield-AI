import csv
import io
import json
import logging
import os
import re
import time
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult
from modules.detection.taxonomy import TaxonomyService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Taxonomy fallback defaults (used only if TaxonomyService.get_target_entities
# returns nothing for the given document_type). Sourced from the
# Global_PII_PHI_Entity_Taxonomy workbook's Implementation_Shortlist sheet:
# 67 Must Have entities (36 Critical / 21 High / 10 Medium) and 40 Nice to
# Have entities. Kept as the single source of truth here so a missing
# TaxonomyService config never silently narrows coverage.
# ---------------------------------------------------------------------------
DEFAULT_MUST_HAVE = [
    # Critical
    "API_KEY", "ACCESS_TOKEN", "PASSWORD", "AADHAAR_NUMBER", "CPF", "CURP",
    "EMIRATES_ID", "FIN", "IQAMA_NATIONAL_ID", "MBI", "MY_NUMBER", "NIN",
    "NINO", "NRIC", "PAN_INDIA", "RESIDENT_REGISTRATION_NUMBER", "SIN", "SSN",
    "DRIVER_LICENSE_NUMBER", "PASSPORT_NUMBER", "PAN_PCI", "CVV_CVC_CID_CVN",
    "FULL_TRACK_DATA", "PIN_PIN_BLOCK", "BIOMETRIC",
    "FACIAL_RECOGNITION_TEMPLATE", "FINGERPRINT", "VOICEPRINT", "GENETIC_DATA",
    "DIAGNOSIS", "HEALTH_DATA", "HEALTH_PLAN_BENEFICIARY_NUMBER", "MRN",
    "NPI", "PATIENT_ID",
    # High
    "BANK_ACCOUNT_NUMBER", "CARDHOLDER_NAME", "EXPIRATION_DATE",
    "DATE_OF_BIRTH", "FULL_NAME", "EMAIL_ADDRESS", "PHONE_NUMBER",
    "HOME_ADDRESS", "GPS_COORDINATES", "GEOLOCATION", "DEVICE_ID", "IMEI",
    "IP_ADDRESS", "EMPLOYEE_ID", "SOCIAL_SECURITY_TAX_ID",
    "HEALTH_INSURANCE_ID", "LAB_RESULT", "MEDICAL_CONDITION", "MEDICATION",
    "PROCEDURE", "TREATMENT",
    # Medium
    "ACCOUNT_ID", "AGE", "CUSTOMER_ID", "FIRST_NAME", "LAST_NAME",
    "LICENSE_PLATE", "PHOTO", "POSTAL_CODE", "SIGNATURE", "WORK_EMAIL",
]

DEFAULT_NICE_TO_HAVE = [
    "CNPJ", "ADMISSION_DATE", "DATE_OF_SERVICE", "DISCHARGE_DATE", "IBAN",
    "IMSI", "MAC_ADDRESS", "PLACE_OF_BIRTH", "ROUTING_NUMBER", "SWIFT_BIC",
    "SALARY", "SERVICE_CODE", "SORT_CODE", "STUDENT_ID", "URL",
    "VEHICLE_REGISTRATION", "ADVERTISING_ID", "BROWSER_FINGERPRINT", "CITY",
    "COOKIE_ID", "COUNTRY", "EMAIL_DOMAIN", "EMPLOYER_NAME", "FAX_NUMBER",
    "GENDER_SEX", "JOB_TITLE", "MIDDLE_NAME", "NATIONALITY", "ORDER_ID",
    "SOCIAL_MEDIA_HANDLE", "TRANSACTION_ID", "USERNAME",
    "VEHICLE_IDENTIFICATION_NUMBER", "VOICE_RECORDING", "WORK_PHONE",
    "BROWSER_VERSION", "IP_SUBNET_NETWORK_PREFIX", "LANGUAGE_LOCALE",
    "OPERATING_SYSTEM", "TIME_ZONE",
]

# Explicit, bounded noise definition.
DROP_PATTERNS_TEXT = """\
- Field labels / form headers with no value (e.g. "Name:", "SSN:" with nothing filled in)
- Placeholder / sample / template values (e.g. "John Doe", "123-45-6789" inside a format
  example, "user@example.com")
- Aggregate or de-identified statistics (e.g. "42% of patients reported...", "average age 54")
- Document/section metadata: page numbers, section titles, document IDs, revision numbers
- Organizational (non-personal) identifiers: company registration numbers, generic org email
  aliases (info@company.com, support@company.com)
- Generic role/title mentions with no bound person (e.g. "the attending physician", "a patient")
- Publicly published, non-personal addresses (e.g. a hospital's public street address, not a
  patient's home address)
- Boilerplate legal/consent text, disclaimers, footers
- Currency amounts with no personal linkage (e.g. a generic price list total)
- Common words that only coincidentally match a pattern (e.g. "Bill" as a verb, "May" as a
  month) -- resolve using context, not literal string matching
- Empty, null, "N/A", or placeholder values in a structured field, and schema/column-definition
  rows in a table (the header row itself, not a data row)

IMPORTANT: a DROP pattern is only a default. If the same span is also a real instance of a
MUST_HAVE or NICE_TO_HAVE entity in context, it must still be extracted. When in doubt between
DROP and MUST_HAVE, always resolve to MUST_HAVE -- a missed entity is a breach, a dropped noise
token is not.
"""


class CandidateValidationItem(BaseModel):
    id: str | int
    decision: Literal["CONFIRM", "RECLASSIFY", "REJECT"]
    corrected_type: Optional[str] = None
    reason: str
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0)


class CandidateValidationResponse(BaseModel):
    validations: List[CandidateValidationItem]


class ResidualEntityItem(BaseModel):
    value: str
    entity_type: str
    start: Optional[int] = None
    end: Optional[int] = None
    confidence_score: float = Field(default=0.88, ge=0.0, le=1.0)
    reason: str = Field(default="Discovered by Gemma high-recall residual review")


class ResidualDiscoveryResponse(BaseModel):
    entities: List[ResidualEntityItem] = Field(default_factory=list)
    results: Optional[List[ResidualEntityItem]] = None  # Compatibility alias


class GemmaEntity(BaseModel):
    entity_type: str
    entity_value: str
    confidence_score: float
    start_char: int
    end_char: int
    field_path: Optional[str] = None


class GemmaResponse(BaseModel):
    results: List[GemmaEntity]


class Gemma4E4BDetector(BaseDetector):
    """
    Semantic extractor and contextual validator using Gemma 4:e4b via Ollama.

    Handles both unstructured free text (notes, letters, transcripts) and
    structured data (JSON / CSV / table rows) arriving as a single serialized
    `text` string -- input shape is auto-detected per call, per the project's
    zero-false-negative mandate: a missed entity is treated as a breach event.
    """

    MODEL_NAME = os.getenv("OLLAMA_MODEL", os.getenv("LLM_MODEL", "gemma4:e4b"))
    TEMPERATURE = 0.10
    TOP_P = 0.90
    KEEP_ALIVE = "5m"

    SOFT_RESULT_CEILING = 25
    NUM_PREDICT = 768

    def __init__(self):
        super().__init__()
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = None
        self.ollama_host = ollama_host
        self.MODEL_NAME = os.getenv("OLLAMA_MODEL", os.getenv("LLM_MODEL", "gemma4:e4b"))

        try:
            import httpx
            from ollama import Client

            timeout_val = float(os.getenv("OLLAMA_TIMEOUT", "600.0"))
            custom_timeout = httpx.Timeout(timeout_val, connect=2.0, read=timeout_val, write=60.0)
            self.client = Client(host=ollama_host, timeout=custom_timeout)
        except (ImportError, Exception):
            try:
                from ollama import Client

                timeout_val = float(os.getenv("OLLAMA_TIMEOUT", "600.0"))
                self.client = Client(host=ollama_host, timeout=timeout_val)
            except (ImportError, Exception):
                logger.warning(
                    "Ollama package is not installed or unavailable. LLM detection will be skipped."
                )

        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost_usd = 0.0

    @property
    def name(self) -> str:
        return "gemma"

    def should_run(self, text: str, state: Any) -> bool:
        """
        LLM validation/detection runs whenever:
        - BYPASS_LLM is false and Ollama client is active.
        - Remaining unmasked text or pending candidates are available to process.
        """
        bypass_llm = os.getenv("BYPASS_LLM", "false").strip().lower()
        if bypass_llm in {"1", "true", "yes", "on"}:
            return False

        if self.client is None:
            return False

        if not text or not text.strip():
            return False

        cleaned = self.clean_text_of_labels(text)
        if not cleaned:
            return False

        return True

    @staticmethod
    def _normalized_text(value: str) -> str:
        return " ".join(value.split()).strip()

    @classmethod
    def _find_nearest_span(
        cls,
        text: str,
        entity_value: str,
        preferred_start: int,
        used_spans: set[tuple[int, int]],
    ) -> tuple[int, int] | None:
        escaped = re.escape(entity_value).replace(r"\ ", r"\s+")
        matches = [
            match
            for match in re.finditer(escaped, text)
            if (match.start(), match.end()) not in used_spans
        ]
        if not matches:
            return None
        match = min(matches, key=lambda item: abs(item.start() - preferred_start))
        return match.start(), match.end()

    @staticmethod
    def _get_entity_attr(entity: Any, key: str, default: Any = None) -> Any:
        if isinstance(entity, dict):
            return entity.get(key, default)

        val = getattr(entity, key, None)
        if val is not None:
            return val

        if key == "start_char":
            val = getattr(entity, "start", None)
            if val is not None:
                return val
        elif key == "end_char":
            val = getattr(entity, "end", None)
            if val is not None:
                return val
        elif key == "entity_type":
            val = getattr(entity, "canonical_type", None)
            if val is not None:
                return val

        metadata = getattr(entity, "metadata", None)
        if isinstance(metadata, dict) and key in metadata:
            return metadata[key]

        return default

    @classmethod
    def _format_known_entities(cls, known_entities: list[Any]) -> str:
        if not known_entities:
            return "None"

        lines = []
        for entity in known_entities:
            field_path = cls._get_entity_attr(entity, "field_path")
            start_char = cls._get_entity_attr(entity, "start_char")
            end_char = cls._get_entity_attr(entity, "end_char")
            entity_type = cls._get_entity_attr(entity, "entity_type", "ENTITY")

            location = (
                f"field '{field_path}'"
                if field_path
                else f"chars {start_char}-{end_char}"
            )
            lines.append(
                "- {entity_type} at {location} "
                "(already detected; do not return)".format(
                    entity_type=entity_type,
                    location=location,
                )
            )
        return "\n".join(lines)

    @staticmethod
    def _detect_input_mode(text: str) -> Literal["structured", "unstructured"]:
        stripped = text.strip()
        if not stripped:
            return "unstructured"

        if stripped[0] in "{[":
            try:
                json.loads(stripped)
                return "structured"
            except (ValueError, json.JSONDecodeError):
                pass

        lines = [line for line in stripped.splitlines() if line.strip()]
        if len(lines) >= 2:
            for delim in (",", "\t", "|"):
                counts = [line.count(delim) for line in lines[:10]]
                if counts[0] > 0 and len(set(counts)) == 1:
                    header_fields = lines[0].split(delim)
                    if all(len(f.strip()) <= 40 for f in header_fields):
                        return "structured"

        return "unstructured"

    def _build_prompt(
        self,
        text: str,
        input_mode: Literal["structured", "unstructured"],
        must_have_str: str,
        nice_to_have_str: str,
        known_entities_text: str,
    ) -> str:
        structured_guidance = ""
        if input_mode == "structured":
            structured_guidance = """
=== STRUCTURED INPUT MODE ===
This input is structured data (JSON, CSV/table rows, or key-value records), not prose.
1. Walk EVERY field/column/key, including nested objects and array elements.
2. The field name / column header is a STRONG PRIOR for entity_type.
"""

        return f"""You are a senior PII/PHI redaction and compliance extraction engine operating under a
ZERO-FALSE-NEGATIVE mandate using {self.MODEL_NAME}. A missed sensitive entity is a compliance
breach; a low-confidence extraction that a human or downstream validator later discards costs
nothing. When in doubt, EXTRACT and assign a lower confidence_score rather than omitting the span.

{structured_guidance}

RECALL CHECKLIST -- read the text at least twice before answering:
1. First pass: obvious, clearly-labeled identifiers (e.g. "SSN: 123-45-6789", "Patient: Jane Doe").
2. Second pass: entities without an explicit label, inferred from context (e.g. a name mentioned in
   running prose with no "Name:" prefix, a number that matches an ID format even if unlabeled).
3. Also check for: values split or wrapped across a line break; abbreviated or shorthand forms
   (initials, "DOB" instead of "Date of Birth"); values embedded inside a longer sentence, footer,
   signature block, or table cell; international formats that don't match a US pattern; and any
   second/third occurrence of the same entity elsewhere in the text (each occurrence needs its own
   span, don't stop after the first).
4. Do not silently narrow a MUST_HAVE or NICE_TO_HAVE type to only its most common surface form --
   if a variant plausibly matches the category in context, include it.

Taxonomy Target Entities:
MUST_HAVE:
{must_have_str}

NICE_TO_HAVE:
{nice_to_have_str}

Already Resolved Known Entities:
{known_entities_text}

Input Text to Scan:
\"\"\"{text}\"\"\"

Return ONLY valid JSON with key "results" containing an array of detected entities with fields:
entity_type, entity_value, confidence_score, start_char, end_char.
"""

    def detect(self, text: str, page_number: int = 1) -> list[DetectionResult]:
        if not text or not text.strip():
            return []

        context = getattr(self, "orchestration_context", {}) or {}
        known_entities = context.get("known_entities") or []
        known_entities_text = self._format_known_entities(known_entities)
        document_type = context.get("document_type")

        target_entities = context.get("target_entities") or TaxonomyService.get_target_entities(document_type)
        must_have = target_entities.get("MUST_HAVE") or DEFAULT_MUST_HAVE
        nice_to_have = target_entities.get("NICE_TO_HAVE") or DEFAULT_NICE_TO_HAVE

        must_have_str = "\n".join(f"- {e}" for e in must_have)
        nice_to_have_str = "\n".join(f"- {e}" for e in nice_to_have)

        input_mode = self._detect_input_mode(text)
        prompt = self._build_prompt(
            text=text,
            input_mode=input_mode,
            must_have_str=must_have_str,
            nice_to_have_str=nice_to_have_str,
            known_entities_text=known_entities_text,
        )

        if self.client is None or os.getenv("BYPASS_LLM", "false").strip().lower() in {"1", "true", "yes", "on"}:
            return []

        response = None
        elapsed_ms = 0.0
        for attempt in range(2):
            try:
                start_time = time.perf_counter()
                response = self.client.chat(
                    model=self.MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": self.TEMPERATURE, "top_p": self.TOP_P},
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                break
            except Exception as exc:
                if attempt == 0 and "timeout" in str(exc).lower():
                    logger.warning("Ollama chat timeout encountered, retrying once... (%s)", exc)
                    time.sleep(1.0)
                    continue
                logger.error("LLM extraction failed: error_type=%s (%s)", type(exc).__name__, exc)
                return []

        if response is None:
            return []

        try:
            if isinstance(response, dict):
                msg = response.get("message", {})
                raw_content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
                p_tok = response.get("prompt_eval_count", 0) or (len(prompt) // 4)
                c_tok = response.get("eval_count", 0) or (len(raw_content) // 4 if raw_content else 0)
            else:
                msg = getattr(response, "message", None)
                if isinstance(msg, dict):
                    raw_content = msg.get("content", "")
                else:
                    raw_content = getattr(msg, "content", "") if msg else ""
                p_tok = getattr(response, "prompt_eval_count", 0) or (len(prompt) // 4)
                c_tok = getattr(response, "eval_count", 0) or (len(raw_content) // 4 if raw_content else 0)

            self.prompt_tokens += max(1, p_tok)
            self.completion_tokens += max(1, c_tok)

            if not raw_content or not raw_content.strip():
                return []

            # Parse JSON safely
            match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            json_str = match.group(0) if match else raw_content
            parsed = json.loads(json_str)

            raw_list = parsed.get("results", []) if isinstance(parsed, dict) else []
            results = []
            used_spans = set()

            for item in raw_list:
                val = item.get("entity_value", "").strip()
                if not val:
                    continue
                e_type = item.get("entity_type", "ENTITY")
                c_score = float(item.get("confidence_score", 0.85))
                p_start = int(item.get("start_char", 0))

                span = self._find_nearest_span(text, val, p_start, used_spans)
                if not span:
                    continue

                start_char, end_char = span
                used_spans.add(span)

                results.append(
                    DetectionResult(
                        entity_type=e_type,
                        entity_value=val,
                        confidence_score=c_score,
                        start_char=start_char,
                        end_char=end_char,
                        page_number=page_number,
                        detector=self.name,
                        metadata={"llm_model": self.MODEL_NAME, "elapsed_ms": elapsed_ms},
                    )
                )

            return results
        except Exception as exc:
            logger.error("LLM extraction parsing failed: error_type=%s (%s)", type(exc).__name__, exc)
            return []

    def validate_candidates(
        self,
        candidates: list[DetectionResult],
        chunks: list[Any],
        document_type: str | None = None,
    ) -> list[DetectionResult]:
        """
        Phase 4: Low-confidence candidate validation using Gemma context with structured JSON reasoning.
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
            if self.client and os.getenv("BYPASS_LLM", "false").strip().lower() not in {"1", "true", "yes", "on"}:
                try:
                    system_prompt = (
                        "You are an elite PII/PHI Compliance Validation Engine. "
                        "Evaluate candidate text in context against global privacy regulations (HIPAA, GDPR, CCPA, PCI-DSS).\n\n"
                        "Decide: CONFIRM, RECLASSIFY, or REJECT.\n"
                        "This system runs under a zero-false-negative mandate: a wrongly REJECTed real entity is a "
                        "compliance breach, while a wrongly CONFIRMed candidate is just reviewed later at no real cost. "
                        "Resolve any genuine ambiguity toward CONFIRM or RECLASSIFY, never toward REJECT.\n"
                        "Only REJECT when you are clearly and specifically certain the candidate is non-sensitive noise: "
                        "an empty/unlabeled document header, an email thread title, a bare form field label with no "
                        "filled-in value, a generic English verb/greeting, or template/placeholder boilerplate. "
                        "If the candidate could plausibly be a real instance of any PII/PHI type in this context, CONFIRM "
                        "it (RECLASSIFY if a different canonical type fits better) rather than rejecting it.\n\n"
                        "Respond ONLY in valid JSON:\n"
                        '{"thought": "...", "decision": "CONFIRM"|"RECLASSIFY"|"REJECT", "corrected_type": "<TYPE or null>", "confidence_score": 0.85, "reason": "..."}'
                    )
                    user_msg = (
                        f"Candidate: '{candidate.entity_value}' (Proposed Type: {candidate.entity_type})\n"
                        f"Context:\n\"\"\"{chunk_text[:400]}\"\"\"\n\n"
                        "Return your validation decision in strict JSON format."
                    )
                    resp = self.client.chat(
                        model=self.MODEL_NAME,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_msg},
                        ],
                        format="json",
                        options={"temperature": 0.0},
                    )
                    raw_content = resp.get("message", {}).get("content", "")
                    if raw_content:
                        json_m = re.search(r"\{.*\}", raw_content, re.DOTALL)
                        if json_m:
                            d = json.loads(json_m.group(0))
                            dec = str(d.get("decision", "")).strip().upper()
                            if dec in {"CONFIRM", "RECLASSIFY", "REJECT"}:
                                corr = d.get("corrected_type")
                                conf = float(d.get("confidence_score", 0.85))
                                r_reason = str(d.get("reason") or d.get("thought") or f"Validated '{candidate.entity_value}' via Gemma.").strip()
                                llm_item = CandidateValidationItem(
                                    id=str(getattr(candidate, "entity_id", "cand")),
                                    decision=dec,
                                    corrected_type=corr if dec == "RECLASSIFY" and corr else candidate.entity_type,
                                    confidence_score=min(1.0, max(0.0, conf)),
                                    reason=r_reason,
                                )
                except Exception as exc:
                    logger.debug("Gemma chat completion failed/skipped (%s); falling back to heuristic", exc)

            item = llm_item or self._heuristic_validate_candidate(candidate, chunk_text, document_type)
            logger.info(
                "GemmaValidation: mode=VALIDATION decision=%s type=%s confidence=%.2f",
                item.decision,
                candidate.entity_type,
                item.confidence_score,
            )
            if item.decision in {"CONFIRM", "RECLASSIFY"}:
                if item.decision == "RECLASSIFY" and item.corrected_type:
                    candidate.entity_type = item.corrected_type
                candidate.confidence_score = max(candidate.confidence_score, item.confidence_score)
                candidate.detector = "Gemma"
                candidate.metadata["gemma_validation"] = item.decision
                candidate.metadata["gemma_reason"] = item.reason or getattr(item, "reasoning", f"Validated '{candidate.entity_value}' in document context.")
                validated.append(candidate)
            else:
                candidate.metadata["gemma_validation"] = "REJECT"
                candidate.metadata["gemma_reason"] = item.reason or getattr(item, "reasoning", f"Rejected '{candidate.entity_value}' as non-sensitive noise.")
        return validated

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
        Phase 5: Exhaustive High-Recall Residual Entity Discovery.
        """
        if not chunk_text or not chunk_text.strip():
            return []

        # Sub-chunk long text into slices of max ~750 characters at line breaks to prevent LLM ReadTimeout
        if len(chunk_text) > 800:
            sub_results = []
            lines = chunk_text.splitlines(keepends=True)
            curr_text = ""
            curr_start = chunk_start
            for line in lines:
                if len(curr_text) + len(line) > 750 and curr_text:
                    sub_end = curr_start + len(curr_text)
                    res = self.detect_residual_chunk(
                        chunk_text=curr_text,
                        chunk_start=curr_start,
                        chunk_end=sub_end,
                        known_entities=known_entities,
                        document_type=document_type,
                        page_number=page_number,
                    )
                    sub_results.extend(res)
                    curr_start = sub_end
                    curr_text = line
                else:
                    curr_text += line
            if curr_text:
                sub_end = curr_start + len(curr_text)
                res = self.detect_residual_chunk(
                    chunk_text=curr_text,
                    chunk_start=curr_start,
                    chunk_end=sub_end,
                    known_entities=known_entities,
                    document_type=document_type,
                    page_number=page_number,
                )
                sub_results.extend(res)
            return sub_results


        known_entities = known_entities or []
        known_entities_text = self._format_known_entities(known_entities)

        target_entities = TaxonomyService.get_target_entities(document_type)
        must_have = target_entities.get("MUST_HAVE") or DEFAULT_MUST_HAVE
        nice_to_have = target_entities.get("NICE_TO_HAVE") or DEFAULT_NICE_TO_HAVE

        must_have_str = "\n".join(f"- {e}" for e in must_have[:35])
        nice_to_have_str = "\n".join(f"- {e}" for e in nice_to_have[:25])

        prompt = f"""You are a specialized PII/PHI compliance high-recall security reviewer using {self.MODEL_NAME}.
Your primary security mission is: DO NOT MISS IMPORTANT SENSITIVE ENTITIES. This is a residual pass
over text that earlier detectors already scanned once and likely missed something -- assume there is
at least one more entity hiding here and look harder, including partial, unlabeled, or oddly-formatted
values. A borderline candidate reported with a lower confidence_score is far preferable to silence.

CRITICAL INSTRUCTIONS:
1. Review the entire chunk for sensitive entities, including values with no explicit field label,
   values split across a line break, abbreviated forms, and any repeated occurrence of an entity
   already found elsewhere in this chunk (report every occurrence, not just the first).
2. DO NOT RE-EXTRACT ALREADY RESOLVED ENTITIES:
{known_entities_text}

Taxonomy Targets:
MUST_HAVE:
{must_have_str}

NICE_TO_HAVE:
{nice_to_have_str}

Semantic Chunk to Inspect:
\"\"\"{chunk_text}\"\"\"

Return JSON format with "entities" key containing items with value, entity_type, confidence_score.
"""

        if self.client is None or os.getenv("BYPASS_LLM", "false").strip().lower() in {"1", "true", "yes", "on"}:
            return []

        response = None
        elapsed_ms = 0.0
        for attempt in range(2):
            try:
                start_time = time.perf_counter()
                response = self.client.chat(
                    model=self.MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": self.TEMPERATURE, "top_p": self.TOP_P},
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                break
            except Exception as exc:
                if attempt == 0 and "timeout" in str(exc).lower():
                    logger.warning("Ollama residual chat timeout encountered, retrying once... (%s)", exc)
                    time.sleep(1.0)
                    continue
                logger.error("LLM residual discovery failed: error_type=%s (%s)", type(exc).__name__, exc)
                return []

        if response is None:
            return []

        try:
            if isinstance(response, dict):
                msg = response.get("message", {})
                raw_content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
                p_tok = response.get("prompt_eval_count", 0) or (len(prompt) // 4)
                c_tok = response.get("eval_count", 0) or (len(raw_content) // 4 if raw_content else 0)
            else:
                msg = getattr(response, "message", None)
                if isinstance(msg, dict):
                    raw_content = msg.get("content", "")
                else:
                    raw_content = getattr(msg, "content", "") if msg else ""
                p_tok = getattr(response, "prompt_eval_count", 0) or (len(prompt) // 4)
                c_tok = getattr(response, "eval_count", 0) or (len(raw_content) // 4 if raw_content else 0)

            self.prompt_tokens += max(1, p_tok)
            self.completion_tokens += max(1, c_tok)

            if not raw_content or not raw_content.strip():
                return []

            match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            json_str = match.group(0) if match else raw_content
            parsed = json.loads(json_str)

            items = parsed.get("entities", []) if isinstance(parsed, dict) else []
            results = []
            used_spans = set()

            for item in items:
                val = item.get("value", "").strip() if isinstance(item, dict) else ""
                if not val:
                    continue
                e_type = item.get("entity_type", "SENSITIVE_DATA") if isinstance(item, dict) else "SENSITIVE_DATA"
                c_score = float(item.get("confidence_score", 0.88)) if isinstance(item, dict) else 0.88

                span = self._find_nearest_span(chunk_text, val, 0, used_spans)
                if not span:
                    continue
                rel_start, rel_end = span
                used_spans.add(span)

                results.append(
                    DetectionResult(
                        entity_type=e_type,
                        entity_value=val,
                        confidence_score=c_score,
                        start_char=chunk_start + rel_start,
                        end_char=chunk_start + rel_end,
                        page_number=page_number,
                        detector=self.name,
                        metadata={
                            "llm_model": self.MODEL_NAME,
                            "elapsed_ms": elapsed_ms,
                            "residual_discovery": True,
                        },
                    )
                )
            return results
        except Exception as exc:
            logger.error("LLM residual discovery failed: error_type=%s (%s)", type(exc).__name__, exc)
            return []

    def _heuristic_validate_candidate(
        self,
        candidate: DetectionResult,
        chunk_text: str,
        document_type: str | None = None,
    ) -> CandidateValidationItem:
        val_lower = candidate.entity_value.strip().lower()
        chunk_lower = chunk_text.lower()

        SPANISH_DISCLAIMER_TERMS = {
            "español", "espanol", "spanish", "tagalog", "chinese", "navajo",
            "para obtener", "para obtener ayuda", "llame al", "si usted", "o alguien",
            "language access", "language access services", "ayuda en español",
            "atención", "atencion", "assistance services",
        }
        if any(term in val_lower for term in SPANISH_DISCLAIMER_TERMS) or (val_lower in {"al", "para", "obtener", "ayuda"}):
            return CandidateValidationItem(
                id=1,
                decision="REJECT",
                reason=f"Term '{candidate.entity_value}' is part of a multilingual language access disclaimer, not personal PII.",
                confidence_score=0.95,
            )

        if candidate.entity_type in {"PERSON", "LOCATION"} and any(c.isdigit() for c in candidate.entity_value):
            return CandidateValidationItem(
                id=1,
                decision="REJECT",
                reason=f"Candidate '{candidate.entity_value}' contains digits/phone number and is not a valid {candidate.entity_type}.",
                confidence_score=0.95,
            )

        if candidate.entity_type in {"EOB_NUMBER", "INSURANCE_ID", "POLICY_NUMBER", "CLAIM_NUMBER"} and re.match(r"^(?:p\.?o\.?\s*)?box\s+\d+$", val_lower):
            return CandidateValidationItem(
                id=1,
                decision="RECLASSIFY",
                corrected_type="ADDRESS",
                reason=f"Candidate '{candidate.entity_value}' refers to a mailing PO Box address, not an {candidate.entity_type}.",
                confidence_score=0.95,
            )

        if candidate.entity_type in {"ADDRESS", "LOCATION", "CITY_STATE_ZIP"} and re.match(r"^[a-zA-Z\s.'-]+,\s*[A-Z]{2}(?:\s+\d{5})?$", candidate.entity_value.strip()):
            return CandidateValidationItem(
                id=1,
                decision="CONFIRM",
                reason=f"Candidate '{candidate.entity_value}' is a valid geographic address/location in the document context.",
                confidence_score=0.95,
            )

        REJECT_TERMS = {
            "mail order", "mail-order", "preauth", "pre-auth", "preauthorization",
            "minimum value", "minimum value standard", "hearing", "hearing aids",
            "in-network", "out-of-network", "tier 1", "tier 2", "tier 3",
            "copay", "coinsurance", "deductible", "generic", "preferred brand",
            "non-preferred", "specialty", "prior authorization", "step therapy",
            "quantity limit", "emergency room", "urgent care", "routine exam",
            "preventive", "wellness", "schedule of benefits", "explanation of benefits",
            "plan provisions", "disclaimer", "notice", "patient information",
            "appointment details", "medical history", "coverage", "benefit", "summary",
            "coinsurance rate", "eligible expenses", "out of pocket", "out-of-pocket",
            "amountcovered", "amount covered", "amountbilled", "amount billed",
            "amountpaid", "amount paid", "totalbilled", "total billed",
            "visitdate", "visit date", "procedurecode", "procedure code",
            "diagnosiscode", "diagnosis code", "insuranceid", "insurance id",
            "policynumber", "policy number", "claimnumber", "claim number",
            "groupnumber", "group number", "subscriberid", "memberid",
        }

        clean_val_key = re.sub(r"[^a-z0-9]", "", val_lower)
        if val_lower in REJECT_TERMS or clean_val_key in REJECT_TERMS:
            return CandidateValidationItem(
                id=1,
                decision="REJECT",
                reason=f"Term '{candidate.entity_value}' is a document field header or insurance term, not an entity.",
                confidence_score=0.95,
            )

        if "hearing" in val_lower and ("hearing aids" in chunk_lower or "hearing aid" in chunk_lower or "benefit" in chunk_lower):
            return CandidateValidationItem(
                id=1,
                decision="REJECT",
                reason="'Hearing' in hearing aids context is a service category, not a location or person.",
                confidence_score=0.95,
            )

        if "pharmacy" in chunk_lower or "rx" in chunk_lower or "dispense" in chunk_lower or "pharmacy" in val_lower:
            if candidate.entity_type == "PERSON" and any(term in val_lower for term in ["westfield", "walgreens", "cvs", "rite aid", "walmart", "kroger", "pharmacy", "apothecary"]):
                return CandidateValidationItem(
                    id=1,
                    decision="RECLASSIFY",
                    corrected_type="ORGANIZATION",
                    reason=f"'{candidate.entity_value}' in pharmacy context is a pharmacy/organization name, not an individual person.",
                    confidence_score=0.90,
                )

        if candidate.entity_type in {"DOCTOR", "PHYSICIAN"}:
            for suffix in [" office visit", " specialist consult", " consult", " follow up", " evaluation", " exam"]:
                if val_lower.endswith(suffix):
                    clean_val = candidate.entity_value[:-len(suffix)].strip()
                    candidate.entity_value = clean_val
                    candidate.end_char = candidate.start_char + len(clean_val)
                    break
            return CandidateValidationItem(
                id=1,
                decision="CONFIRM",
                reason="Doctor entity confirmed in clinical context.",
                confidence_score=0.90,
            )

        if candidate.entity_type in {"PERSON", "LOCATION", "ORGANIZATION"}:
            words = candidate.entity_value.strip().split()
            LABEL_NOISE_TERMS = {
                "patient", "doctor", "physician", "provider", "nurse", "member", "subscriber",
                "admin", "preauth", "hearing", "vision", "dental", "request", "requests",
                "transfer", "cif", "sb", "rd", "statement", "holder", "summary", "notices",
                "info", "details", "period", "balance", "amount", "total", "ending",
                "logo", "logo placeholder", "placeholder", "field discrepancy", "discrepancy",
                "field", "form title", "header", "footer", "page", "signature", "stamp", "label"
            }
            if val_lower in LABEL_NOISE_TERMS or val_lower in REJECT_TERMS:
                return CandidateValidationItem(
                    id=1,
                    decision="REJECT",
                    reason=f"Term '{candidate.entity_value}' is a document field header or non-sensitive label, not a {candidate.entity_type}.",
                    confidence_score=0.95,
                )
            if len(words) == 1 and (val_lower in LABEL_NOISE_TERMS or len(candidate.entity_value.strip()) <= 2 or candidate.entity_value.islower()):
                return CandidateValidationItem(
                    id=1,
                    decision="REJECT",
                    reason=f"Single-token '{candidate.entity_value}' is not a valid {candidate.entity_type} entity.",
                    confidence_score=0.95,
                )
            if len(words) >= 2 and all(w[0].isupper() for w in words if w.strip(".").isalpha()):
                return CandidateValidationItem(
                    id=1,
                    decision="CONFIRM",
                    reason=f"'{candidate.entity_value}' is a multi-token capitalized person/organization name in context.",
                    confidence_score=0.88,
                )

        if candidate.confidence_score >= 0.80:
            return CandidateValidationItem(
                id=1,
                decision="CONFIRM",
                reason="High confidence candidate confirmed.",
                confidence_score=candidate.confidence_score,
            )

        return CandidateValidationItem(
            id=1,
            decision="CONFIRM",
            reason=f"Candidate '{candidate.entity_value}' has sufficient contextual relevance in document context.",
            confidence_score=0.85,
        )


# Canonical class aliases
GemmaDetector = Gemma4E4BDetector
Gemma4Detector = Gemma4E4BDetector
Gemma4E4BDetector = Gemma4E4BDetector
GemmaDetector = Gemma4E4BDetector
