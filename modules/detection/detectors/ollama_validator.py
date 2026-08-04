from __future__ import annotations

import json
import logging
import time
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple


from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError

from modules.detection.models.detection_result import DetectionResult

logger = logging.getLogger(__name__)


# ==========================================================
# Pydantic Models
# ==========================================================


class ValidationResponse(BaseModel):
    """
    Response for a single validated entity.
    """

    reasoning: str = Field(...)

    entity_type: str = Field(...)

    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    valid: bool


class BatchValidationResponse(BaseModel):
    """
    Response returned by Ollama.
    """

    results: List[ValidationResponse]


# ==========================================================
# Ollama Validator
# ==========================================================


class OllamaValidator:
    """
    LLM-assisted validator for LOW-confidence entities.

    This validator never replaces the main detectors.

    Instead it validates:

        Regex
            â†“
        Presidio
            â†“
        GLiNER
            â†“
        MedSpaCy
            â†“
        LOW confidence entities
            â†“
        Ollama
            â†“
        Final result

    Features

    âœ“ Batch validation
    âœ“ Retry logic
    âœ“ Pydantic validation
    âœ“ JSON enforcement
    âœ“ Confidence calibration
    âœ“ Audit metadata
    âœ“ Validation cache
    """

    MODEL_NAME = "qwen3:4b"

    TEMPERATURE = 0.10

    TOP_P = 0.90

    MAX_RETRIES = 2

    REQUEST_TIMEOUT = 120

    KEEP_ALIVE = "5m"

    CACHE_ENABLED = True

    MAX_BATCH_SIZE = 15

    ENTITY_TAXONOMY = [

        "PERSON",

        "AGE",

        "DATE",

        "PHONE_NUMBER",

        "FAX_NUMBER",

        "EMAIL",

        "SSN",

        "MRN",

        "INSURANCE_ID",

        "ACCOUNT_NUMBER",

        "LICENSE_NUMBER",

        "ADDRESS",

        "LOCATION",

        "ZIP_CODE",

        "HOSPITAL_OR_FACILITY",

        "ORGANIZATION",

        "URL",

        "IP_ADDRESS",

        "DEVICE_ID",

        "BIOMETRIC_ID",

        "VEHICLE_ID",

        "OTHER_PHI",

        "NOT_PII",

    ]

    def __init__(self):
        import os

        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.MODEL_NAME = os.getenv("OLLAMA_VALIDATOR_MODEL", self.MODEL_NAME)
        self.REQUEST_TIMEOUT = int(os.getenv("OLLAMA_REQUEST_TIMEOUT", self.REQUEST_TIMEOUT))
        self.client = None
        self.ollama_host = ollama_host

        try:
            from ollama import Client

            self.client = Client(
                host=ollama_host,
                timeout=self.REQUEST_TIMEOUT,
            )
        except ImportError:
            logger.warning(
                "Ollama package is not installed. LLM validation will be skipped."
            )

        self._cache: Dict[
            Tuple[str, str],
            ValidationResponse,
        ] = {}
    # ======================================================
    # Utility Methods
    # ======================================================

    def _cache_key(
        self,
        entity: DetectionResult,
    ) -> Tuple[str, str]:

        return (

            entity.entity_value.strip().lower(),

            entity.entity_type,

        )

    def _clamp_score(
        self,
        score: float,
    ) -> float:

        return max(

            0.0,

            min(

                1.0,

                float(score),

            ),

        )

    def _is_cached(
        self,
        entity: DetectionResult,
    ) -> bool:

        if not self.CACHE_ENABLED:

            return False

        return self._cache_key(entity) in self._cache

    def _get_cached(
        self,
        entity: DetectionResult,
    ) -> Optional[ValidationResponse]:

        if not self.CACHE_ENABLED:

            return None

        return self._cache.get(

            self._cache_key(entity)

        )

    def _store_cache(

        self,

        entity: DetectionResult,

        response: ValidationResponse,

    ):

        if not self.CACHE_ENABLED:

            return

        self._cache[

            self._cache_key(entity)

        ] = response

    # ======================================================
    # Prompt Utilities
    # ======================================================

    def _taxonomy_string(self) -> str:

        return ", ".join(

            self.ENTITY_TAXONOMY

        )

    def _entity_json(

        self,

        entity: DetectionResult,

    ):

        return {

            "value": entity.entity_value,

            "predicted_type": entity.entity_type,

            "predicted_confidence": entity.confidence_score,

        }
            # ======================================================
    # Few-Shot Examples
    # ======================================================

    FEW_SHOT_EXAMPLES = [
        {
            "context": (
                "Patient was referred by Dr. Washington for diabetes follow-up."
            ),
            "entity": {
                "value": "Washington",
                "predicted_type": "LOCATION",
                "predicted_confidence": 0.42,
            },
            "result": {
                "reasoning": (
                    "'Washington' follows the title 'Dr.' and therefore "
                    "represents a physician rather than a location."
                ),
                "entity_type": "PERSON",
                "confidence_score": 0.94,
                "valid": True,
            },
        },
        {
            "context": (
                "Patient has Parkinson's disease diagnosed in 2018."
            ),
            "entity": {
                "value": "Parkinson",
                "predicted_type": "PERSON",
                "predicted_confidence": 0.45,
            },
            "result": {
                "reasoning": (
                    "Part of a disease name rather than an identifiable person."
                ),
                "entity_type": "NOT_PII",
                "confidence_score": 0.93,
                "valid": False,
            },
        },
        {
            "context": (
                "Please call 555-0199 to confirm your appointment."
            ),
            "entity": {
                "value": "555-0199",
                "predicted_type": "ACCOUNT_NUMBER",
                "predicted_confidence": 0.41,
            },
            "result": {
                "reasoning": (
                    "The phrase 'call' clearly indicates a phone number."
                ),
                "entity_type": "PHONE_NUMBER",
                "confidence_score": 0.97,
                "valid": True,
            },
        },
        {
            "context": (
                "The patient was prescribed Paracetamol 500 mg twice daily."
            ),
            "entity": {
                "value": "Paracetamol",
                "predicted_type": "PERSON",
                "predicted_confidence": 0.39,
            },
            "result": {
                "reasoning": (
                    "Medication name with dosage information."
                ),
                "entity_type": "NOT_PII",
                "confidence_score": 0.95,
                "valid": False,
            },
        },
        {
            "context": (
                "MRN 00587142 was verified before admission."
            ),
            "entity": {
                "value": "00587142",
                "predicted_type": "OTHER_PHI",
                "predicted_confidence": 0.52,
            },
            "result": {
                "reasoning": (
                    "Immediately follows the MRN label."
                ),
                "entity_type": "MRN",
                "confidence_score": 0.98,
                "valid": True,
            },
        },
    ]

    # ======================================================
    # Prompt Builder
    # ======================================================

    def _format_examples(self) -> str:

        examples = []

        for index, example in enumerate(
            self.FEW_SHOT_EXAMPLES,
            start=1,
        ):

            examples.append(

                f"""
Example {index}

Context:
{example["context"]}

Entity:
{json.dumps(example["entity"], indent=2)}

Expected Output:
{json.dumps(example["result"], indent=2)}
""".strip()

            )

        return "\n\n".join(examples)

    def _build_batch_prompt(

        self,

        context: str,

        entities: List[DetectionResult],

    ) -> str:

        payload = []

        for entity in entities:

            payload.append(

                {

                    "value": entity.entity_value,

                    "predicted_type": entity.entity_type,

                    "predicted_confidence": round(
                        entity.confidence_score,
                        3,
                    ),

                }

            )

        taxonomy = self._taxonomy_string()

        examples = self._format_examples()

        return f"""
You are a senior PHI/PII validation specialist.

Your task is to validate LOW-confidence entities.

Use ONLY these entity types:

{taxonomy}

Rules:

1. Read the complete context.

2. Validate each entity independently.

3. Correct entity_type if necessary.

4. If the entity is not actually PII/PHI,
   return:

entity_type = NOT_PII

valid = false

5. If uncertain, prefer VALID.

6. Confidence must be between
0.0 and 1.0.

7. Never invent new entity types.

8. Return ONLY JSON.

------------------------------------------------

Examples

{examples}

------------------------------------------------

Document Context

{context}

------------------------------------------------

Entities

{json.dumps(payload, indent=2)}

------------------------------------------------

Return EXACTLY this JSON schema.

{{
    "results":[
        {{
            "reasoning":"...",

            "entity_type":"PERSON",

            "confidence_score":0.91,

            "valid":true
        }}
    ]
}}

The number of results MUST equal the number
of input entities.

Return ONLY JSON.

No markdown.

No explanation.
"""
    # ======================================================
    # Ollama Communication
    # ======================================================

    def _call_ollama(
        self,
        prompt: str,
    ) -> BatchValidationResponse:
        """
        Sends a batch validation request to Ollama.

        Retries automatically with exponential backoff if parsing or connection fails.
        """
        if self.client is None:
            raise RuntimeError(
                "Ollama validation is unavailable because the `ollama` "
                "Python package is not installed."
            )

        last_exception = None

        for attempt in range(1, self.MAX_RETRIES + 2):
            try:
                start = time.perf_counter()

                response = self.client.chat(
                    model=self.MODEL_NAME,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    format="json",
                    options={
                        "temperature": self.TEMPERATURE,
                        "top_p": self.TOP_P,
                        "num_predict": 512,
                    },
                    keep_alive=self.KEEP_ALIVE,
                )

                elapsed = round(
                    time.perf_counter() - start,
                    3,
                )

                logger.info(
                    "Ollama validation completed in %.3f sec",
                    elapsed,
                )

                raw = response["message"]["content"]
                cleaned = raw.strip()

                if cleaned.startswith("```"):
                    cleaned = (
                        cleaned
                        .replace("```json", "")
                        .replace("```", "")
                        .strip()
                    )

                parsed = BatchValidationResponse.model_validate_json(
                    cleaned
                )
                return parsed

            except ValidationError as exc:
                logger.warning(
                    "ValidationError (attempt %d): %s",
                    attempt,
                    exc,
                )
                last_exception = exc

            except json.JSONDecodeError as exc:
                logger.warning(
                    "JSON decode failed (attempt %d)",
                    attempt,
                )
                last_exception = exc

            except Exception as exc:
                # Connection or API request error
                backoff_delay = 2 ** attempt
                logger.warning(
                    "Ollama connection/request failed on attempt %d: %s. Retrying in %d seconds...",
                    attempt,
                    exc,
                    backoff_delay,
                )
                time.sleep(backoff_delay)
                last_exception = exc

        raise RuntimeError(
            f"Ollama validation failed after {self.MAX_RETRIES + 1} attempts. "
            f"Please verify that the Ollama host '{self.ollama_host}' is running and healthy. "
            f"Error details: {last_exception}"
        ) from last_exception

    # ======================================================
    # Cache Helpers
    # ======================================================

    def _cached_or_pending(

        self,

        entities: List[DetectionResult],

    ):

        """
        Splits entities into:

            cached

            pending

        """

        cached = []

        pending = []

        for entity in entities:

            if self._is_cached(entity):

                cached.append(

                    (

                        entity,

                        self._get_cached(entity),

                    )

                )

            else:

                pending.append(entity)

        return cached, pending

    # ======================================================
    # Response Processing
    # ======================================================

    def _apply_validation(

        self,

        entity: DetectionResult,

        validation: ValidationResponse,

    ) -> DetectionResult:

        #
        # Preserve originals.
        #

        entity.metadata["original_type"] = entity.entity_type

        entity.metadata["original_confidence"] = (
            entity.confidence_score
        )

        #
        # Update prediction.
        #

        entity.entity_type = validation.entity_type

        entity.confidence_score = self._clamp_score(
            validation.confidence_score
        )

        entity.metadata.update(

            {

                "validated_by": "ollama",

                "model": self.MODEL_NAME,

                "reasoning": validation.reasoning,

                "valid": validation.valid,

                "validation_version": "v2",

            }

        )

        return entity

    # ======================================================
    # Batch Validation
    # ======================================================

    def _validate_batch(

        self,

        context: str,

        entities: List[DetectionResult],

    ) -> List[DetectionResult]:

        """
        Validate one batch of entities.
        """

        if not entities:

            return []

        prompt = self._build_batch_prompt(

            context,

            entities,

        )

        response = self._call_ollama(

            prompt,

        )

        if len(response.results) != len(entities):

            logger.warning(

                "Batch size mismatch."

            )

            return entities

        validated = []

        for entity, result in zip(

            entities,

            response.results,

        ):

            self._store_cache(

                entity,

                result,

            )

            validated.append(

                self._apply_validation(

                    entity,

                    result,

                )

            )

        return validated
            # ======================================================
    # Public API
    # ======================================================

    def validate(
        self,
        context: str,
        entity: DetectionResult,
    ) -> DetectionResult:
        """
        Validate a single entity.

        This method is provided for backward compatibility.
        Internally it uses batch validation.
        """

        results = self.validate_batch(
            context=context,
            entities=[entity],
        )

        return results[0]

    def validate_batch(
        self,
        context: str,
        entities: List[DetectionResult],
    ) -> List[DetectionResult]:
        """
        Validate multiple low-confidence entities.

        Workflow

            Cache
                â†“
            Batch
                â†“
            Ollama
                â†“
            Pydantic Validation
                â†“
            Update DetectionResult
        """

        if not entities:
            return []

        if self.client is None:
            for entity in entities:
                entity.metadata.update(
                    {
                        "validated_by": "ollama",
                        "validation_status": "SKIPPED",
                        "validation_error": "Ollama client unavailable",
                    }
                )
            return entities

        #
        # Split cached vs pending
        #

        cached_entities, pending_entities = self._cached_or_pending(
            entities
        )

        validated_results: List[DetectionResult] = []

        #
        # Apply cached validations
        #

        for entity, cached in cached_entities:

            validated_results.append(
                self._apply_validation(
                    entity,
                    cached,
                )
            )

        #
        # Validate remaining entities
        #

        if pending_entities:

            try:

                #
                # Process in batches
                #

                for start in range(
                    0,
                    len(pending_entities),
                    self.MAX_BATCH_SIZE,
                ):

                    batch = pending_entities[
                        start:start + self.MAX_BATCH_SIZE
                    ]

                    validated_results.extend(
                        self._validate_batch(
                            context=context,
                            entities=batch,
                        )
                    )

            except Exception as exc:

                logger.exception(
                    "Batch validation failed: %s",
                    exc,
                )

                #
                # Fail-safe:
                # never lose detections.
                #

                for entity in pending_entities:

                    entity.metadata.update(

                        {

                            "validated_by": "ollama",

                            "validation_error": str(exc),

                            "validation_status": "FAILED",

                        }

                    )

                    validated_results.append(entity)

        #
        # Restore original order
        #

        lookup = {

            (
                item.entity_value,
                item.start_char,
                item.end_char,
            ): item

            for item in validated_results

        }

        ordered_results = []

        for entity in entities:

            key = (

                entity.entity_value,

                entity.start_char,

                entity.end_char,

            )

            ordered_results.append(
                lookup.get(
                    key,
                    entity,
                )
            )

        return ordered_results

