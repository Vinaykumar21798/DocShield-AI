import json
import logging
import os
import re
import time
from typing import List, Literal
from pydantic import BaseModel, Field

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult

logger = logging.getLogger(__name__)


class Qwen3BEntity(BaseModel):
    entity_type: Literal[
        "PERSON", "PATIENT", "DOCTOR", "PROVIDER", "NURSE",
        "LOCATION", "ADDRESS", "DATE", "DATE_TIME", "DATE_OF_BIRTH",
        "VISIT_DATE", "ORGANIZATION", "HOSPITAL", "MEDICAL_FACILITY",
        "HEALTHCARE_ORGANIZATION", "EMAIL", "PHONE_NUMBER",
        "US_PHONE_NUMBER", "SSN", "MRN", "MEDICAL_RECORD_NUMBER",
        "INSURANCE_ID", "POLICY_NUMBER", "CLAIM_NUMBER", "MEMBER_ID",
        "GROUP_NUMBER", "EOB_NUMBER", "NPI_NUMBER", "TAX_ID",
        "ICD10_CODE", "CPT_CODE", "DISEASE", "DIAGNOSIS",
        "MEDICATION", "DOSAGE", "PROCEDURE", "SYMPTOM", "LAB",
        "LAB_RESULT", "VITAL_SIGN", "CLINICAL_FINDING",
        "CLINICAL_MEASUREMENT", "BANK_ACCOUNT_NUMBER",
        "CREDIT_CARD_NUMBER", "PAN_NUMBER", "AADHAAR_NUMBER",
        "PASSPORT_NUMBER", "DRIVING_LICENSE", "IFSC_CODE", "UPI_ID",
        "URL", "IP_ADDRESS", "ZIP_CODE", "OTHER_PHI",
    ]
    entity_value: str
    confidence_score: float
    start_char: int
    end_char: int


class Qwen3BResponse(BaseModel):
    results: List[Qwen3BEntity]


class Qwen3BDetector(BaseDetector):
    """
    Semantic extractor using Qwen3:4b via Ollama.
    """

    MODEL_NAME = "qwen3:4b"
    TEMPERATURE = 0.10
    TOP_P = 0.90
    KEEP_ALIVE = "5m"

    def __init__(self):
        super().__init__()
        import os

        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = None
        self.ollama_host = ollama_host

        try:
            from ollama import Client

            self.client = Client(host=ollama_host)
        except ImportError:
            logger.warning(
                "Ollama package is not installed. Qwen3:4b detection will be skipped."
            )
    @property
    def name(self) -> str:
        return "qwen3b"

    def should_run(self, text: str, state: "PipelineState") -> bool:
        """
        Qwen3:4b runs whenever:
        - BYPASS_LLM is false and Ollama client is active.
        - Remaining unmasked text is available to process.
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
            lines.append(
                "- {entity_type} at chars {start_char}-{end_char} "
                "(already detected; do not return)".format(
                    entity_type=entity.get("entity_type", "ENTITY"),
                    start_char=entity.get("start_char"),
                    end_char=entity.get("end_char"),
                )
            )
        return "\n".join(lines)

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

        prompt = f"""You are a senior clinical and PII/PHI information extraction assistant.
Extract unresolved PII and PHI entities from the input text below.
Use ONLY the following entity categories:
- PERSON
- PATIENT
- DOCTOR
- PROVIDER
- NURSE
- LOCATION
- ADDRESS
- DATE
- DATE_TIME
- DATE_OF_BIRTH
- VISIT_DATE
- ORGANIZATION
- HOSPITAL
- MEDICAL_FACILITY
- HEALTHCARE_ORGANIZATION
- EMAIL
- PHONE_NUMBER
- US_PHONE_NUMBER
- SSN
- MRN
- MEDICAL_RECORD_NUMBER
- INSURANCE_ID
- POLICY_NUMBER
- CLAIM_NUMBER
- MEMBER_ID
- GROUP_NUMBER
- EOB_NUMBER
- NPI_NUMBER
- TAX_ID
- ICD10_CODE
- CPT_CODE
- DISEASE
- DIAGNOSIS
- MEDICATION
- DOSAGE
- PROCEDURE
- SYMPTOM
- LAB
- LAB_RESULT
- VITAL_SIGN
- CLINICAL_FINDING
- CLINICAL_MEASUREMENT
- BANK_ACCOUNT_NUMBER
- CREDIT_CARD_NUMBER
- PAN_NUMBER
- AADHAAR_NUMBER
- PASSPORT_NUMBER
- DRIVING_LICENSE
- IFSC_CODE
- UPI_ID
- URL
- IP_ADDRESS
- ZIP_CODE
- OTHER_PHI

Return EXACTLY this JSON schema:
{{
    "results": [
        {{
            "entity_type": "PERSON",
            "entity_value": "John Doe",
            "confidence_score": 0.90,
            "start_char": 15,
            "end_char": 23
        }}
    ]
}}

Strict ensure start_char and end_char indices represent the exact 0-indexed boundaries in the input text.
Return at most 12 results. If no real entity values exist, return {{"results": []}}.
Do not return labels, headings, or field names such as "Date of Service" unless the label itself is the sensitive value.
DATE values must be real calendar dates. Never classify money, CPT/HCPCS codes, or ICD-10 codes as DATE.
ICD10_CODE and CPT_CODE must follow their standard code shapes and appear in matching clinical context.
Known high-confidence spans are already detected. Use them only as context. Do not return any entity whose character range overlaps a known span.
Return ONLY valid JSON. No reasoning, no markdown wrappers, no explanation.

Known high-confidence spans:
{known_entities_text}

Input Text:
{text}
"""
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
                    "num_predict": 1536,
                },
                keep_alive=self.KEEP_ALIVE,
            )
            elapsed = time.perf_counter() - start
            logger.info("Qwen3:4b extraction completed in %.3f sec", elapsed)

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
                results.append(
                    DetectionResult(
                        entity_type=item.entity_type.upper(),
                        entity_value=entity_value,
                        confidence_score=confidence_score,
                        start_char=start_char,
                        end_char=end_char,
                        page_number=page_number,
                        detector=self.name,
                        metadata={
                            "model": self.MODEL_NAME,
                            "resolved": True,
                        },
                    )
                )
            return results
        except Exception as exc:
            logger.exception("Qwen3:4b detection failed: %s", exc)
            return []
