import json
import logging
import os
import re
import time
from typing import List
import ollama
from pydantic import BaseModel, Field

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult

logger = logging.getLogger(__name__)


class Qwen3BEntity(BaseModel):
    entity_type: str
    entity_value: str
    confidence_score: float
    start_char: int
    end_char: int


class Qwen3BResponse(BaseModel):
    results: List[Qwen3BEntity]


class Qwen3BDetector(BaseDetector):
    """
    Semantic extractor using a 3B/4B Qwen SLM via Ollama.
    """

    MODEL_NAME = "qwen3:4b"  # Maps to the 3B/4B class SLM pulled locally
    TEMPERATURE = 0.10
    TOP_P = 0.90
    KEEP_ALIVE = "5m"

    def __init__(self):
        super().__init__()
        import os
        from ollama import Client
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = Client(host=ollama_host)

    @property
    def name(self) -> str:
        return "qwen3b"

    def should_run(self, text: str, state: "PipelineState") -> bool:
        """
        Qwen 3B runs only when semantic reasoning is required:
        - Traditional detectors have run and unresolved text remains.
        - And there is either an entity type conflict (ambiguity) or low confidence detections.
        """
        if os.getenv("BYPASS_LLM") == "true":
            return False

        if not text or not text.strip():
            return False

        cleaned = self.clean_text_of_labels(text)
        if not cleaned:
            return False

        # Verify traditional detectors have executed (Task 10)
        traditional_run = any(name in state.executed_detectors for name in {"presidio", "gliner", "medspacy"})
        if not traditional_run:
            return False

        # Criteria 1: Overlapping boundary conflicts (semantic ambiguity)
        has_conflict = False
        resolved = state.resolved_entities
        for i in range(len(resolved)):
            for j in range(i + 1, len(resolved)):
                e1, e2 = resolved[i], resolved[j]
                if e1.start_char < e2.end_char and e1.end_char > e2.start_char:
                    if e1.entity_type != e2.entity_type:
                        has_conflict = True
                        break
            if has_conflict:
                break

        # Criteria 2: Unresolved entities have low confidence scores (< 0.80)
        has_low_confidence = any(e.confidence_score < 0.80 for e in resolved)

        # Only run if there is active ambiguity (conflict) or low confidence traditional output
        return has_conflict or has_low_confidence


    def detect(
        self,
        text: str,
        page_number: int = 1,
    ) -> list[DetectionResult]:
        if not text or not text.strip():
            return []

        prompt = f"""You are a senior clinical and PII/PHI information extraction assistant.
Extract all PII and PHI entities from the input text below.
Use ONLY the following entity categories:
- PERSON
- LOCATION
- DATE_TIME
- ORGANIZATION
- DISEASE
- DIAGNOSIS
- MEDICATION
- PROCEDURE
- SYMPTOM

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

Strictly ensure start_char and end_char indices represent the exact 0-indexed boundaries in the input text.
Return ONLY valid JSON. No reasoning, no markdown wrappers, no explanation.

Input Text:
{text}
"""
        try:
            start = time.perf_counter()
            response = self.client.chat(
                model=self.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                format="json",
                options={
                    "temperature": self.TEMPERATURE,
                    "top_p": self.TOP_P,
                    "num_predict": 256,
                },
                keep_alive=self.KEEP_ALIVE,
            )
            elapsed = time.perf_counter() - start
            logger.info("Qwen 3B extraction completed in %.3f sec", elapsed)

            raw = response["message"]["content"].strip()
            if raw.startswith("```"):
                raw = (
                    raw.replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

            parsed = Qwen3BResponse.model_validate_json(raw)
            results = []
            for item in parsed.results:
                # Double-check offsets match the expected text segment
                val = text[item.start_char : item.end_char]
                if val.strip() == "" or item.entity_value not in val:
                    # Attempt simple recovery via regex search
                    match = re.search(
                        re.escape(item.entity_value), text
                    )
                    if match:
                        start_char = match.start()
                        end_char = match.end()
                    else:
                        continue
                else:
                    start_char = item.start_char
                    end_char = item.end_char

                results.append(
                    DetectionResult(
                        entity_type=item.entity_type.upper(),
                        entity_value=item.entity_value,
                        confidence_score=item.confidence_score,
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
            logger.exception("Qwen 3B detection failed: %s", exc)
            return []
