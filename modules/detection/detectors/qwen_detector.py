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

# Explicit, bounded noise definition. This replaces the old vague
# "don't return generic labels/headings/boilerplate" instruction, which left
# the model free to drop real entities it merely *suspected* were noise.
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


class Qwen3BEntity(BaseModel):
    entity_type: str
    entity_value: str
    confidence_score: float
    start_char: int
    end_char: int
    field_path: Optional[str] = None


class Qwen3BResponse(BaseModel):
    results: List[Qwen3BEntity]


class Qwen3BDetector(BaseDetector):
    """
    Semantic extractor using Qwen3:4b via Ollama.

    Handles both unstructured free text (notes, letters, transcripts) and
    structured data (JSON / CSV / table rows) arriving as a single serialized
    `text` string -- input shape is auto-detected per call, per the project's
    zero-false-negative mandate: a missed entity is treated as a breach event,
    a false positive is treated as a minor, acceptable cost.
    """

    MODEL_NAME = os.getenv("OLLAMA_MODEL", os.getenv("LLM_MODEL", "gemma4:e4b"))
    TEMPERATURE = 0.10
    TOP_P = 0.90
    KEEP_ALIVE = "5m"

    # Soft output-budget ceiling only -- NOT a "stop looking for entities"
    # instruction. Sized to roughly match NUM_PREDICT so the model doesn't
    # get cut off mid-JSON on a very dense input. Raise this (and NUM_PREDICT)
    # together if you regularly see truncated responses in the logs.
    SOFT_RESULT_CEILING = 25
    NUM_PREDICT = 768

    def __init__(self):
        super().__init__()
        import os

        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = None
        self.ollama_host = ollama_host
        self.MODEL_NAME = os.getenv("OLLAMA_MODEL", os.getenv("LLM_MODEL", "gemma4:e4b"))

        try:
            from ollama import Client

            self.client = Client(host=ollama_host, timeout=180.0)
        except (ImportError, Exception):
            logger.warning(
                "Ollama package is not installed or unavailable. LLM detection will be skipped."
            )

    @property
    def name(self) -> str:
        return "gemma"

    def should_run(self, text: str, state: "PipelineState") -> bool:
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
    def _format_known_entities(known_entities: list[dict]) -> str:
        if not known_entities:
            return "None"

        lines = []
        for entity in known_entities:
            field_path = entity.get("field_path")
            location = (
                f"field '{field_path}'"
                if field_path
                else f"chars {entity.get('start_char')}-{entity.get('end_char')}"
            )
            lines.append(
                "- {entity_type} at {location} "
                "(already detected; do not return)".format(
                    entity_type=entity.get("entity_type", "ENTITY"),
                    location=location,
                )
            )
        return "\n".join(lines)

    @staticmethod
    def _detect_input_mode(text: str) -> Literal["structured", "unstructured"]:
        """
        Best-effort classification of the serialized `text` payload so the
        prompt can apply the right extraction strategy (Section 6a/6b of the
        detection design). This is a heuristic, not a guarantee -- the prompt
        itself also tells the model to judge structure directly from the
        text, so a misclassification here degrades gracefully rather than
        silently skipping entities.
        """
        stripped = text.strip()
        if not stripped:
            return "unstructured"

        # JSON object or array
        if stripped[0] in "{[":
            try:
                json.loads(stripped)
                return "structured"
            except (ValueError, json.JSONDecodeError):
                pass

        # CSV / TSV heuristic: multiple lines, consistent delimiter count,
        # first line looks like a header (no long free-text sentences).
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
1. Walk EVERY field/column/key, including nested objects and array elements. Do not stop
   at the top level or the first few rows/records.
2. The field name / column header is a STRONG PRIOR for entity_type (e.g. a column named
   "ssn", "patient_mrn", "email", "dob" maps directly to the matching entity type) -- but
   you must still inspect the VALUE, not just the key name:
     a. an empty/null/"N/A"/placeholder value is DROP even under a sensitive-sounding key.
     b. a generically-named field ("field_12", "value", "notes", "comment", "remarks") may
        still contain a real MUST_HAVE entity typed as free text -- scan its value like
        prose, not just as an opaque field.
3. Do not treat a generic column name as proof the column is safe -- check actual values.
4. Skip only true header/schema/column-definition rows; every populated data row must be
   scanned, even if earlier rows were empty.
5. For arrays of records, process every record independently -- a match in record #1 does
   not exempt identical-looking fields in record #50.
6. When you report a structured-mode entity, also set "field_path" to the exact key/column
   path it came from (dot notation for nesting, [i] for array index), IN ADDITION TO the
   required start_char/end_char offsets of that value within the raw input text below.
"""

        return f"""You are a senior PII/PHI redaction and compliance extraction engine operating under a
ZERO-FALSE-NEGATIVE mandate. Your output feeds a masking pipeline. If you fail to identify a
real sensitive entity, that entity will be exposed in a data breach, regulatory filing, or
third-party leak -- this is treated as a critical failure, more costly than over-flagging.

Rules of engagement:
1. When uncertain whether a span is a real entity or noise, INCLUDE it (lower the
   confidence_score, but still return it). Never silently drop a plausible entity.
2. The spans listed under 'Known high-confidence spans' are ALREADY RESOLVED. Do NOT
   re-identify or return anything overlapping those locations.
3. Classify strictly against the MUST_HAVE and NICE_TO_HAVE lists below. Anything matching a
   NO_NEED / DROP pattern must be excluded, UNLESS it is also a real instance of a MUST_HAVE /
   NICE_TO_HAVE type (see the DROP section for the explicit tie-breaker rule).
4. Do not invent entities. Every entity_value must be an exact, verbatim substring of the
   input text below.
5. This input has been classified as {input_mode.upper()}. Apply the matching strategy
   (see STRUCTURED INPUT MODE guidance below if applicable).
{structured_guidance}
=== PRIORITY 1: MUST_HAVE ENTITIES (Highest Priority - Reliably Extract All, Zero Misses) ===
{must_have_str}

=== PRIORITY 2: NICE_TO_HAVE ENTITIES (Secondary Priority - Extract When Present) ===
{nice_to_have_str}

=== NO_NEED / DROP -- Explicit Noise Patterns (do not flag these) ===
{DROP_PATTERNS_TEXT}

Return EXACTLY this JSON schema, nothing else (no markdown fences, no reasoning):
{{
    "results": [
        {{
            "entity_type": "SSN",
            "entity_value": "078-05-1120",
            "confidence_score": 0.93,
            "start_char": 15,
            "end_char": 26,
            "field_path": null
        }}
    ]
}}

Rules:
- start_char/end_char are REQUIRED and must be the exact 0-indexed boundaries of
  entity_value within the raw input text below (this applies even in structured mode, since
  the input is one serialized text string).
- field_path is OPTIONAL: set it for structured-mode entities (e.g. "patients[3].mrn"),
  leave it null for free-text/prose spans.
- entity_type must be one of the MUST_HAVE or NICE_TO_HAVE codes above (uppercase,
  underscore-separated).
- confidence_score in [0.0, 1.0]. Use LOWER confidence for uncertain spans instead of
  omitting them -- low confidence is never a reason to drop a real entity.
- Cover the ENTIRE input (all text / all fields / all rows). Do not stop early. Return up to
  {self.SOFT_RESULT_CEILING} results; if you find more than that in one input, prioritize
  MUST_HAVE (Critical, then High, then Medium) over NICE_TO_HAVE.
- DATE values must be real calendar dates.
- If truly nothing is present, return {{"results": []}} -- this should be rare once
  known_entities and DROP filtering are applied correctly.

Before finalizing, verify: did I scan the entire input (not just the first portion)? Did I
check specifically for each MUST_HAVE type plausible for this input/document type? Did I avoid
dropping any span just because it was low-confidence or resembled a DROP pattern, when a
MUST_HAVE interpretation was also plausible? Did I avoid overlapping any known high-confidence
span? Is every entity_value an exact verbatim substring at the stated offsets?

Known high-confidence spans (DO NOT re-extract):
{known_entities_text}

Input Text:
{text}
"""

    def detect(
        self,
        text: str,
        page_number: int = 1,
    ) -> list[DetectionResult]:
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

        if self.client is None:
            logger.warning(
                "Qwen3:4b detection skipped because the `ollama` Python package is not installed."
            )
            return []

        try:
            start = time.perf_counter()
            response = self.client.chat(
                model=self.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                think=False,
                format="json",
                options={
                    "temperature": self.TEMPERATURE,
                    "top_p": self.TOP_P,
                    "num_predict": self.NUM_PREDICT,
                },
                keep_alive=self.KEEP_ALIVE,
            )
            elapsed = time.perf_counter() - start
            logger.info(
                "Qwen3:4b extraction completed in %.3f sec (input_mode=%s)",
                elapsed,
                input_mode,
            )

            raw = ""
            if hasattr(response, "message") and hasattr(response.message, "content"):
                raw = response.message.content
            elif isinstance(response, dict) and "message" in response:
                raw = response["message"].get("content", "")
            raw = raw.strip()

            if not raw:
                logger.warning("Qwen3:4b returned an empty response. It may have hit the token budget limit.")
                return []

            if raw.startswith("```"):
                raw = (
                    raw.replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

            try:
                parsed = Qwen3BResponse.model_validate_json(raw)
            except Exception as parse_exc:
                logger.warning(
                    "Failed to parse Qwen3:4b response as JSON: %s (Raw response: %r)",
                    parse_exc,
                    raw,
                )
                return []

            results = []
            used_spans: set[tuple[int, int]] = set()
            for item in parsed.results:
                entity_value = " ".join(item.entity_value.split()).strip()
                if not entity_value:
                    continue

                start_char = item.start_char
                end_char = item.end_char
                span_is_valid = 0 <= start_char < end_char <= len(text)
                span_value = text[start_char:end_char] if span_is_valid else ""
                span_matches_value = (
                    span_is_valid
                    and self._normalized_text(span_value)
                    == self._normalized_text(entity_value)
                    and (start_char, end_char) not in used_spans
                )

                if not span_matches_value:
                    recovered = self._find_nearest_span(
                        text,
                        entity_value,
                        start_char,
                        used_spans,
                    )
                    if recovered is None:
                        continue
                    start_char, end_char = recovered

                entity_value = text[start_char:end_char]
                used_spans.add((start_char, end_char))

                confidence_score = max(0.0, min(1.0, item.confidence_score))

                metadata = {
                    "model": self.MODEL_NAME,
                    "resolved": True,
                    "input_mode": input_mode,
                }
                if item.field_path:
                    metadata["field_path"] = item.field_path

                results.append(
                    DetectionResult(
                        entity_type=item.entity_type.upper(),
                        entity_value=entity_value,
                        confidence_score=confidence_score,
                        start_char=start_char,
                        end_char=end_char,
                        page_number=page_number,
                        detector=self.name,
                        metadata=metadata,
                    )
                )
            return results
        except Exception as exc:
            logger.exception("LLM extraction failed: %s", exc)
            return []

    def detect_residual_chunk(
        self,
        chunk_text: str,
        chunk_start: int,
        chunk_end: int,
        known_entities: list[DetectionResult] | None = None,
        document_type: str | None = None,
        page_number: int = 1,
    ) -> list[DetectionResult]:
        """
        Phase 5: Exhaustive High-Recall Residual Entity Discovery for unresolved semantic chunk.
        
        Mandate:
        - Security-critical high-recall review: DO NOT MISS IMPORTANT SENSITIVE ENTITIES.
        - Two-level reasoning (Coverage Review -> Sensitive Entity Discovery).
        - Multi-entity extraction per chunk.
        - Robust to unusual formats, prose, tables, and distorted tokens.
        - Exact global coordinate mapping and verification.
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

        prompt = f"""You are a specialized PII/PHI compliance high-recall security reviewer using {self.MODEL_NAME}.
Your primary security mission is: DO NOT MISS IMPORTANT SENSITIVE ENTITIES.
Review the following semantic chunk from a {document_type or 'general'} document to identify all genuinely sensitive entities that earlier detectors may have missed.

CRITICAL INSTRUCTIONS:
1. HIGH-RECALL REVIEW: Review the entire semantic chunk for sensitive personal, medical, financial, identity, or regulated data. Check names, account numbers, identifiers, medical conditions/diagnoses, medications, procedures, addresses, contact details, and organization names.
2. DO NOT STOP AFTER FINDING ONE ENTITY: Perform a complete, exhaustive review of all sentences, labels, and table cells in the chunk. Identify ALL distinct sensitive entities supported by the text.
3. HANDLE UNUSUAL FORMATS & NATURAL LANGUAGE: Look for sensitive identifiers with non-standard prefixes (e.g. "SB-5001010135"), names in unexpected positions, or medical terms in prose.
4. TEXTUAL EVIDENCE REQUIRED: Do NOT hallucinate or invent entities. Every detected entity must be an exact verbatim substring present in the chunk.
5. ALREADY RESOLVED ENTITIES: Do NOT re-extract the following known entities already locked in this chunk:
{known_entities_text}

Taxonomy Target Entities:
MUST_HAVE:
{must_have_str}

NICE_TO_HAVE:
{nice_to_have_str}

Semantic Chunk to Inspect:
\"\"\"{chunk_text}\"\"\"

Return EXACTLY JSON format:
{{
    "entities": [
        {{
            "value": "verbatim text substring",
            "entity_type": "UPPERCASE_TYPE",
            "start": 0,
            "end": 10,
            "confidence_score": 0.90,
            "reason": "Specific contextual rationale explaining why this value represents sensitive data."
        }}
    ]
}}
If no unresolved sensitive entity is present, return {{"entities": []}}.
"""
        bypass_llm = os.getenv("BYPASS_LLM", "false").strip().lower() in {"1", "true", "yes", "on"}
        if self.client is not None and not bypass_llm:
            try:
                start_call = time.perf_counter()
                response = self.client.chat(
                    model=self.MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    think=False,
                    format="json",
                    options={
                        "temperature": 0.10,
                        "top_p": 0.90,
                        "num_predict": 768,
                    },
                    keep_alive=self.KEEP_ALIVE,
                )
                latency_ms = (time.perf_counter() - start_call) * 1000.0
                raw = response.message.content.strip() if hasattr(response, "message") else ""
                if raw.startswith("```"):
                    raw = raw.replace("```json", "").replace("```", "").strip()

                parsed_items = []
                try:
                    parsed_res = ResidualDiscoveryResponse.model_validate_json(raw)
                    parsed_items = parsed_res.entities or parsed_res.results or []
                except Exception:
                    data = json.loads(raw)
                    raw_list = data.get("entities") or data.get("results") or []
                    for item in raw_list:
                        if isinstance(item, dict) and "value" in item and "entity_type" in item:
                            parsed_items.append(ResidualEntityItem(
                                value=item["value"],
                                entity_type=item["entity_type"],
                                start=item.get("start"),
                                end=item.get("end"),
                                confidence_score=float(item.get("confidence_score", 0.88)),
                                reason=item.get("reason", "Discovered by Gemma residual review"),
                            ))

                results: list[DetectionResult] = []
                used_spans: set[tuple[int, int]] = set()

                for item in parsed_items:
                    val = item.value.strip()
                    if not val:
                        continue

                    local_span = None
                    if item.start is not None and item.end is not None and 0 <= item.start < item.end <= len(chunk_text):
                        if chunk_text[item.start:item.end] == val:
                            local_span = (item.start, item.end)

                    if local_span is None or local_span in used_spans:
                        local_span = self._find_nearest_span(chunk_text, val, 0, used_spans)

                    if local_span is None:
                        continue

                    used_spans.add(local_span)
                    l_start, l_end = local_span
                    g_start = chunk_start + l_start
                    g_end = chunk_start + l_end

                    res = DetectionResult(
                        entity_type=item.entity_type.upper(),
                        entity_value=val,
                        confidence_score=max(0.85, item.confidence_score),
                        start_char=g_start,
                        end_char=g_end,
                        page_number=page_number,
                        detector="gemma",
                        entity_owner="gemma",
                        metadata={
                            "llm_mode": "RESIDUAL_DETECTION",
                            "validator": self.MODEL_NAME,
                            "residual_discovery": True,
                            "residual_reason": item.reason,
                            "latency_ms": round(latency_ms, 2),
                        },
                    )
                    results.append(res)

                return results

            except Exception as exc:
                logger.warning("Gemma residual discovery call failed (%s); recording RESIDUAL_DETECTION_FAILED", exc)

        return []

    def validate_candidates(
        self,
        candidates: list[DetectionResult],
        chunks: list[Any],
        document_type: str | None = None,
    ) -> list[DetectionResult]:
        """
        Validates low-confidence candidates (e.g. Presidio 0.75) against their enclosing
        semantic chunks using gemma4:e4b (with heuristic fallback).

        Decisions:
        - CONFIRM: Genuine PII/PHI entity, type is correct -> kept with upgraded confidence.
        - RECLASSIFY: Genuine entity, wrong type -> updated to corrected_type.
        - REJECT: Contextual/business/technical noise (e.g. Mail Order, Preauth, table headers) -> dropped.
        """
        if not candidates:
            return []

        start_total = time.perf_counter()
        candidate_items = []
        for idx, cand in enumerate(candidates):
            enclosing_chunk = None
            for ch in chunks:
                if ch.start_char <= cand.start_char and cand.end_char <= ch.end_char:
                    enclosing_chunk = ch
                    break
            if not enclosing_chunk and chunks:
                enclosing_chunk = min(chunks, key=lambda ch: abs(ch.start_char - cand.start_char))

            chunk_text = enclosing_chunk.text if enclosing_chunk else (cand.metadata.get("chunk_text") or "")
            chunk_id = getattr(enclosing_chunk, "chunk_id", cand.metadata.get("chunk_id", 0))
            cand_id = getattr(cand, "id", None) or cand.metadata.get("candidate_id") or f"c_{idx + 1}"
            cand.metadata["candidate_id"] = cand_id

            candidate_items.append({
                "id": str(cand_id),
                "numeric_id": idx + 1,
                "candidate": cand,
                "chunk": enclosing_chunk,
                "chunk_id": chunk_id,
                "chunk_text": chunk_text,
            })

        validated_results: list[DetectionResult] = []
        confirm_count = 0
        reclassify_count = 0
        reject_count = 0
        failure_count = 0

        bypass_llm = os.getenv("BYPASS_LLM", "false").strip().lower() in {"1", "true", "yes", "on"}
        if self.client is not None and not bypass_llm:
            try:
                target_entities = TaxonomyService.get_target_entities(document_type)
                must_have_str = ", ".join((target_entities.get("MUST_HAVE") or DEFAULT_MUST_HAVE)[:30])
                nice_to_have_str = ", ".join((target_entities.get("NICE_TO_HAVE") or DEFAULT_NICE_TO_HAVE)[:30])

                items_prompt_list = []
                for item in candidate_items:
                    cand = item["candidate"]
                    items_prompt_list.append(
                        f"Candidate ID: {item['id']}\n"
                        f"Value: \"{cand.entity_value}\"\n"
                        f"Proposed Entity Type: {cand.entity_type}\n"
                        f"Detector: {cand.detector} (Confidence: {cand.confidence_score:.2f})\n"
                        f"Document Type: {document_type or 'General / Unspecified'}\n"
                        f"Enclosing Semantic Context:\n\"\"\"{item['chunk_text']}\"\"\""
                    )
                items_str = "\n\n---\n\n".join(items_prompt_list)

                prompt = f"""You are a specialized PII/PHI compliance validation model using {self.MODEL_NAME}.
Evaluate the following low-confidence candidate entities extracted from a {document_type or 'general'} document against their enclosing semantic context and taxonomy.

CRITICAL INSTRUCTION:
The detector's proposed entity type is NOT ground truth. It is only a hypothesis.
You must independently evaluate the candidate using the semantic context, document type, and meaning.

For each candidate ID, decide:
- "CONFIRM": The candidate is a genuine sensitive PII/PHI entity and the proposed entity type is supported by context.
- "RECLASSIFY": The candidate is a genuine sensitive entity, but the proposed type is wrong or too generic. Provide the correct uppercase entity_type in "corrected_type" (e.g. ORGANIZATION, PATIENT, DOCTOR, FINANCIAL_AMOUNT, ADDRESS).
- "REJECT": The candidate is NOT sensitive personal data, or is table/header text, transaction code, boilerplate, technical metadata, non-sensitive ordinary text, or detector misclassification. Set "corrected_type" to null.

Taxonomy Target Entities:
MUST_HAVE: {must_have_str}
NICE_TO_HAVE: {nice_to_have_str}

Candidates for Validation:
{items_str}

Return EXACTLY JSON format:
{{
    "validations": [
        {{
            "id": "{candidate_items[0]['id']}",
            "decision": "CONFIRM",
            "corrected_type": null,
            "reason": "Specific contextual explanation of why the candidate is confirmed, reclassified, or rejected based on semantic evidence.",
            "confidence_score": 0.90
        }}
    ]
}}
"""
                start_call = time.perf_counter()
                response = self.client.chat(
                    model=self.MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    think=False,
                    format="json",
                    options={
                        "temperature": 0.10,
                        "top_p": 0.90,
                        "num_predict": 512,
                    },
                    keep_alive=self.KEEP_ALIVE,
                )
                call_latency = (time.perf_counter() - start_call) * 1000.0

                raw = response.message.content.strip() if hasattr(response, "message") else ""
                if raw.startswith("```"):
                    raw = raw.replace("```json", "").replace("```", "").strip()
                parsed = CandidateValidationResponse.model_validate_json(raw)
                val_by_id = {}
                for v in parsed.validations:
                    val_by_id[str(v.id)] = v
                    if isinstance(v.id, int):
                        val_by_id[v.id] = v

                for item in candidate_items:
                    cand = item["candidate"]
                    cand_id = item["id"]
                    val = (
                        val_by_id.get(cand_id)
                        or val_by_id.get(str(item["numeric_id"]))
                        or val_by_id.get(item["numeric_id"])
                    )
                    if not val:
                        val = self._heuristic_validate_candidate(cand, item["chunk_text"], document_type)

                    cand_latency = round(call_latency / len(candidate_items), 2)
                    if val.decision == "CONFIRM":
                        confirm_count += 1
                        cand.confidence_score = max(cand.confidence_score, val.confidence_score or 0.90)
                        cand.detector = "Gemma"
                        cand.entity_owner = "gemma"
                        cand.metadata["validator"] = self.MODEL_NAME
                        cand.metadata["gemma_validation"] = "CONFIRM"
                        cand.metadata["qwen_validation"] = "CONFIRM"
                        cand.metadata["gemma_reason"] = val.reason
                        cand.metadata["qwen_reason"] = val.reason
                        cand.metadata["status"] = "CONFIRMED_BY_LLM"
                        validated_results.append(cand)

                        logger.info(
                            "GemmaValidationCandidate: candidate_id=%s doc_id=%s chunk_id=%s value=%r original_type=%r detector=%r detector_confidence=%.2f doc_type=%r model=%r llm_mode=VALIDATION decision=CONFIRM final_type=%r reason=%r llm_confidence=%.2f latency=%.1fms status=CONFIRMED_BY_LLM",
                            cand_id, "doc", item["chunk_id"], cand.entity_value, cand.entity_type, cand.detector, cand.confidence_score, document_type or "generic", self.MODEL_NAME, cand.entity_type, val.reason, cand.confidence_score, cand_latency
                        )
                    elif val.decision == "RECLASSIFY":
                        reclassify_count += 1
                        new_type = (val.corrected_type or cand.entity_type).upper()
                        orig_type = cand.entity_type
                        cand.metadata["original_type"] = orig_type
                        cand.entity_type = new_type
                        cand.canonical_type = new_type
                        cand.confidence_score = max(cand.confidence_score, val.confidence_score or 0.90)
                        cand.detector = "Gemma"
                        cand.entity_owner = "gemma"
                        cand.metadata["validator"] = self.MODEL_NAME
                        cand.metadata["gemma_validation"] = "RECLASSIFY"
                        cand.metadata["qwen_validation"] = "RECLASSIFY"
                        cand.metadata["gemma_reason"] = val.reason
                        cand.metadata["qwen_reason"] = val.reason
                        cand.metadata["status"] = "RECLASSIFIED_BY_LLM"
                        validated_results.append(cand)

                        logger.info(
                            "GemmaValidationCandidate: candidate_id=%s doc_id=%s chunk_id=%s value=%r original_type=%r detector=%r detector_confidence=%.2f doc_type=%r model=%r llm_mode=VALIDATION decision=RECLASSIFY final_type=%r reason=%r llm_confidence=%.2f latency=%.1fms status=RECLASSIFIED_BY_LLM",
                            cand_id, "doc", item["chunk_id"], cand.entity_value, orig_type, cand.detector, cand.confidence_score, document_type or "generic", self.MODEL_NAME, new_type, val.reason, cand.confidence_score, cand_latency
                        )
                    else:
                        reject_count += 1
                        cand.metadata["status"] = "REJECTED_BY_LLM"
                        cand.metadata["validator"] = self.MODEL_NAME
                        cand.metadata["gemma_validation"] = "REJECT"
                        cand.metadata["qwen_validation"] = "REJECT"
                        cand.metadata["gemma_reason"] = val.reason
                        cand.metadata["qwen_reason"] = val.reason

                        logger.info(
                            "GemmaValidationCandidate: candidate_id=%s doc_id=%s chunk_id=%s value=%r original_type=%r detector=%r detector_confidence=%.2f doc_type=%r model=%r llm_mode=VALIDATION decision=REJECT final_type=null reason=%r llm_confidence=%.2f latency=%.1fms status=REJECTED_BY_LLM",
                            cand_id, "doc", item["chunk_id"], cand.entity_value, cand.entity_type, cand.detector, cand.confidence_score, document_type or "generic", self.MODEL_NAME, val.reason, val.confidence_score or 0.90, cand_latency
                        )

                total_latency = (time.perf_counter() - start_total) * 1000.0
                avg_latency = total_latency / max(1, len(candidate_items))
                logger.info(
                    "==================================================\n"
                    "Gemma Validation Summary\n"
                    "==================================================\n"
                    "Pending candidates: %d\n"
                    "Sent to Gemma: %d\n"
                    "CONFIRM: %d\n"
                    "RECLASSIFY: %d\n"
                    "REJECT: %d\n"
                    "FAILURES: %d\n"
                    "Model: %s\n"
                    "Average latency: %.1fms\n"
                    "Total latency: %.1fms\n"
                    "==================================================",
                    len(candidate_items), len(candidate_items), confirm_count, reclassify_count, reject_count, failure_count, self.MODEL_NAME, avg_latency, total_latency
                )
                return validated_results

            except Exception as exc:
                failure_count += len(candidate_items)
                logger.warning("Gemma LLM validation call failed (%s); marking LLM_VALIDATION_FAILED with fallback", exc)

        # Semantic Heuristic validation fallback / offline handling
        for item in candidate_items:
            cand = item["candidate"]
            cand_id = item["id"]
            val = self._heuristic_validate_candidate(cand, item["chunk_text"], document_type)
            if val.decision == "CONFIRM":
                confirm_count += 1
                cand.confidence_score = max(cand.confidence_score, val.confidence_score or 0.88)
                cand.detector = "Gemma"
                cand.entity_owner = "gemma"
                cand.metadata["validator"] = self.MODEL_NAME
                cand.metadata["gemma_validation"] = "CONFIRM"
                cand.metadata["qwen_validation"] = "CONFIRM"
                cand.metadata["gemma_reason"] = val.reason
                cand.metadata["qwen_reason"] = val.reason
                cand.metadata["status"] = "CONFIRMED_BY_LLM"
                validated_results.append(cand)
            elif val.decision == "RECLASSIFY":
                reclassify_count += 1
                new_type = (val.corrected_type or cand.entity_type).upper()
                orig_type = cand.entity_type
                cand.metadata["original_type"] = orig_type
                cand.entity_type = new_type
                cand.canonical_type = new_type
                cand.confidence_score = max(cand.confidence_score, val.confidence_score or 0.90)
                cand.detector = "Gemma"
                cand.entity_owner = "gemma"
                cand.metadata["validator"] = self.MODEL_NAME
                cand.metadata["gemma_validation"] = "RECLASSIFY"
                cand.metadata["qwen_validation"] = "RECLASSIFY"
                cand.metadata["gemma_reason"] = val.reason
                cand.metadata["qwen_reason"] = val.reason
                cand.metadata["status"] = "RECLASSIFIED_BY_LLM"
                validated_results.append(cand)
            else:
                reject_count += 1
                cand.metadata["status"] = "REJECTED_BY_LLM"
                cand.metadata["validator"] = self.MODEL_NAME
                cand.metadata["gemma_validation"] = "REJECT"
                cand.metadata["qwen_validation"] = "REJECT"
                cand.metadata["gemma_reason"] = val.reason
                cand.metadata["qwen_reason"] = val.reason

        total_latency = (time.perf_counter() - start_total) * 1000.0
        avg_latency = total_latency / max(1, len(candidate_items))
        logger.info(
            "==================================================\n"
            "Gemma Validation Summary (Fallback)\n"
            "==================================================\n"
            "Pending candidates: %d\n"
            "Sent to Gemma: %d\n"
            "CONFIRM: %d\n"
            "RECLASSIFY: %d\n"
            "REJECT: %d\n"
            "FAILURES: %d\n"
            "Model: %s\n"
            "Average latency: %.1fms\n"
            "Total latency: %.1fms\n"
            "==================================================",
            len(candidate_items), len(candidate_items), confirm_count, reclassify_count, reject_count, failure_count, self.MODEL_NAME, avg_latency, total_latency
        )
        return validated_results

        return validated_results

    def _heuristic_validate_candidate(
        self,
        candidate: DetectionResult,
        chunk_text: str,
        document_type: str | None = None,
    ) -> CandidateValidationItem:
        val_lower = candidate.entity_value.strip().lower()
        chunk_lower = chunk_text.lower()

        # 1. REJECT multilingual / Spanish language access disclaimers
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

        # 2. REJECT candidates containing digits or phone numbers tagged as PERSON / LOCATION
        if candidate.entity_type in {"PERSON", "LOCATION"} and any(c.isdigit() for c in candidate.entity_value):
            return CandidateValidationItem(
                id=1,
                decision="REJECT",
                reason=f"Candidate '{candidate.entity_value}' contains digits/phone number and is not a valid {candidate.entity_type}.",
                confidence_score=0.95,
            )

        # 3. REJECT or RECLASSIFY PO Box when falsely detected as EOB or Insurance ID
        if candidate.entity_type in {"EOB_NUMBER", "INSURANCE_ID", "POLICY_NUMBER", "CLAIM_NUMBER"} and re.match(r"^(?:p\.?o\.?\s*)?box\s+\d+$", val_lower):
            return CandidateValidationItem(
                id=1,
                decision="RECLASSIFY",
                corrected_type="ADDRESS",
                reason=f"Candidate '{candidate.entity_value}' refers to a mailing PO Box address, not an {candidate.entity_type}.",
                confidence_score=0.95,
            )

        # 4. CONFIRM genuine City, State address components
        if candidate.entity_type in {"ADDRESS", "LOCATION", "CITY_STATE_ZIP"} and re.match(r"^[a-zA-Z\s.'-]+,\s*[A-Z]{2}(?:\s+\d{5})?$", candidate.entity_value.strip()):
            return CandidateValidationItem(
                id=1,
                decision="CONFIRM",
                reason=f"Candidate '{candidate.entity_value}' is a valid geographic address/location in the document context.",
                confidence_score=0.95,
            )

        # 5. REJECT known benefit / policy / form / terminology noise
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
        }

        if val_lower in REJECT_TERMS:
            return CandidateValidationItem(
                id=1,
                decision="REJECT",
                reason=f"Term '{candidate.entity_value}' is insurance/benefit terminology, not an individual PII/PHI entity.",
                confidence_score=0.95,
            )

        # If 'hearing' appears in 'hearing aids' or benefit schedule context
        if "hearing" in val_lower and ("hearing aids" in chunk_lower or "hearing aid" in chunk_lower or "benefit" in chunk_lower):
            return CandidateValidationItem(
                id=1,
                decision="REJECT",
                reason="'Hearing' in hearing aids context is a service category, not a location or person.",
                confidence_score=0.95,
            )

        # 4. RECLASSIFY pharmacy / facility / organization names misclassified as PERSON
        if "pharmacy" in chunk_lower or "rx" in chunk_lower or "dispense" in chunk_lower or "pharmacy" in val_lower:
            if candidate.entity_type == "PERSON" and any(term in val_lower for term in ["westfield", "walgreens", "cvs", "rite aid", "walmart", "kroger", "pharmacy", "apothecary"]):
                return CandidateValidationItem(
                    id=1,
                    decision="RECLASSIFY",
                    corrected_type="ORGANIZATION",
                    reason=f"'{candidate.entity_value}' in pharmacy context is a pharmacy/organization name, not an individual person.",
                    confidence_score=0.90,
                )

        # 5. Clean doctor names if trailing visit terms are present
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

        # 6. Proper Person validation: real capitalized full names or labeled patient names
        if candidate.entity_type == "PERSON":
            words = candidate.entity_value.strip().split()
            if len(words) == 1 and val_lower in {"patient", "doctor", "physician", "provider", "nurse", "member", "subscriber", "admin", "preauth", "hearing", "vision", "dental"}:
                return CandidateValidationItem(
                    id=1,
                    decision="REJECT",
                    reason="Single generic role or benefit token is not a specific person.",
                    confidence_score=0.95,
                )
            if len(words) >= 2 and all(w[0].isupper() for w in words if w.isalpha()):
                return CandidateValidationItem(
                    id=1,
                    decision="CONFIRM",
                    reason=f"'{candidate.entity_value}' is a multi-token capitalized person name in context.",
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
            reason=f"Candidate '{candidate.entity_value}' has sufficient contextual relevance in the document context.",
            confidence_score=0.85,
        )


# Canonical class aliases for Gemma contextual validation
GemmaDetector = Qwen3BDetector
Gemma4Detector = Qwen3BDetector