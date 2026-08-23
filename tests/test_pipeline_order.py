import pytest
import os
from typing import Any
from modules.detection.semantic_chunker import SemanticChunker, DocumentChunk
from modules.detection.service import DetectionService, DynamicDetectionConfig
from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.detectors.gemma_detector import GemmaDetector, ResidualEntityItem, ResidualDiscoveryResponse
from modules.detection.models.detection_result import DetectionResult
from modules.detection.pipeline_state import PipelineState


class MockDetector(BaseDetector):
    def __init__(
        self,
        name: str,
        results: list[DetectionResult] | None = None,
        should_run_flag: bool = True,
    ):
        self._name = name
        self.results = results or []
        self.should_run_flag = should_run_flag
        self.seen_texts: list[str] = []
        self.executed_count = 0

    @property
    def name(self) -> str:
        return self._name

    def should_run(self, text: str, state: PipelineState) -> bool:
        return self.should_run_flag

    def detect(self, text: str, page_number: int = 1) -> list[DetectionResult]:
        self.seen_texts.append(text)
        self.executed_count += 1
        return [
            DetectionResult(
                entity_type=r.entity_type,
                entity_value=r.entity_value,
                confidence_score=r.confidence_score,
                start_char=r.start_char,
                end_char=r.end_char,
                page_number=page_number,
                detector=self.name,
                metadata=dict(r.metadata or {}),
            )
            for r in self.results
            if r.entity_value in text
        ]


class MockGemmaDualDetector(BaseDetector):
    """Mock Gemma detector capable of both Phase 4 Residual Discovery and Phase 5 Validation."""
    def __init__(
        self,
        residual_map: dict[str, list[dict]] | None = None,
        validation_map: dict[str, dict] | None = None,
    ):
        self._name = "gemma"
        self.MODEL_NAME = "gemma4:e4b"
        self.residual_map = residual_map or {}
        self.validation_map = validation_map or {}
        self.call_history: list[str] = []
        self.validated_candidate_values: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    def should_run(self, text: str, state: PipelineState) -> bool:
        return True

    def detect(self, text: str, page_number: int = 1) -> list[DetectionResult]:
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
        self.call_history.append("RESIDUAL_DETECTION")
        results: list[DetectionResult] = []
        for key, entity_list in self.residual_map.items():
            if key in chunk_text:
                for item in entity_list:
                    val = item["value"]
                    if val in chunk_text:
                        l_start = chunk_text.index(val)
                        l_end = l_start + len(val)
                        results.append(
                            DetectionResult(
                                entity_type=item["entity_type"],
                                entity_value=val,
                                confidence_score=item.get("confidence_score", 0.90),
                                start_char=chunk_start + l_start,
                                end_char=chunk_start + l_end,
                                page_number=page_number,
                                detector="gemma",
                                metadata={
                                    "llm_mode": "RESIDUAL_DETECTION",
                                    "original_detector": "gemma4:e4b",
                                    "validator": "gemma4:e4b",
                                    "residual_discovery": True,
                                    "residual_reason": item.get("reason", "Discovered in residual review"),
                                },
                            )
                        )
        return results

    def validate_candidates(
        self,
        candidates: list[DetectionResult],
        chunks: list[Any],
        document_type: str | None = None,
    ) -> list[DetectionResult]:
        self.call_history.append("VALIDATION")
        validated: list[DetectionResult] = []
        for cand in candidates:
            self.validated_candidate_values.append(cand.entity_value)
            rule = self.validation_map.get(cand.entity_value, {"decision": "CONFIRM"})
            decision = rule.get("decision", "CONFIRM")
            if decision == "CONFIRM":
                validated.append(
                    DetectionResult(
                        entity_type=cand.entity_type,
                        entity_value=cand.entity_value,
                        confidence_score=0.95,
                        start_char=cand.start_char,
                        end_char=cand.end_char,
                        page_number=cand.page_number,
                        detector="gemma",
                        metadata={
                            **cand.metadata,
                            "gemma_validation": "CONFIRM",
                            "gemma_reason": rule.get("reason", "Confirmed genuine sensitive entity"),
                            "status": "CONFIRMED_BY_LLM",
                        },
                    )
                )
            elif decision == "RECLASSIFY":
                validated.append(
                    DetectionResult(
                        entity_type=rule.get("corrected_type", cand.entity_type),
                        entity_value=cand.entity_value,
                        confidence_score=0.95,
                        start_char=cand.start_char,
                        end_char=cand.end_char,
                        page_number=cand.page_number,
                        detector="gemma",
                        metadata={
                            **cand.metadata,
                            "gemma_validation": "RECLASSIFY",
                            "gemma_reason": rule.get("reason", "Reclassified by Gemma"),
                            "status": "RECLASSIFIED_BY_LLM",
                        },
                    )
                )
            # If REJECT, omit from validated list
        return validated


def create_mock_service(fake_gemma):
    service = DetectionService()
    service.regex = MockDetector("regex")
    service.presidio = MockDetector("presidio")
    service.gliner = MockDetector("gliner")
    service.medspacy = MockDetector("medspacy")
    service.gemma = fake_gemma
    service.azure = fake_gemma
    return service


def test_1_residual_runs_before_validation(monkeypatch):
    """Test 1: Residual detection executes BEFORE candidate validation in call history."""
    monkeypatch.setenv("BYPASS_LLM", "false")
    text = "Westfield Pharmacy\nAccount Number: SB-5001010135"

    fake_gemma = MockGemmaDualDetector(
        residual_map={
            "SB-5001010135": [{"value": "SB-5001010135", "entity_type": "BANK_ACCOUNT_NUMBER", "confidence_score": 0.95}]
        },
        validation_map={
            "Westfield": {"decision": "RECLASSIFY", "corrected_type": "ORGANIZATION"},
            "SB-5001010135": {"decision": "CONFIRM"},
        },
    )
    service = create_mock_service(fake_gemma)
    # Presidio produced low-confidence candidate for Westfield
    service.presidio = MockDetector("presidio", [
        DetectionResult(entity_type="PERSON", entity_value="Westfield", confidence_score=0.70, start_char=0, end_char=9, detector="Presidio")
    ])

    service.detect(text, document_type="financial")
    # Verify call sequence: RESIDUAL_DETECTION comes before VALIDATION
    assert fake_gemma.call_history == ["RESIDUAL_DETECTION", "VALIDATION"]


def test_2_residual_candidate_enters_validation_pool(monkeypatch):
    """Test 2: Newly discovered residual entity is pooled and validated in Phase 5."""
    monkeypatch.setenv("BYPASS_LLM", "false")
    text = "Clinical note: Patient has malignant hypertension."

    fake_gemma = MockGemmaDualDetector(
        residual_map={
            "malignant hypertension": [{"value": "malignant hypertension", "entity_type": "DIAGNOSIS", "confidence_score": 0.90}]
        },
        validation_map={
            "malignant hypertension": {"decision": "CONFIRM", "reason": "Confirmed clinical diagnosis"},
        },
    )
    service = create_mock_service(fake_gemma)

    results = service.detect(text, document_type="healthcare")
    # Verified it entered the validation pool
    assert "malignant hypertension" in fake_gemma.validated_candidate_values
    diag = next(r for r in results if r.entity_value == "malignant hypertension")
    assert diag.entity_type == "DIAGNOSIS"


def test_3_residual_candidate_can_be_rejected_by_validation(monkeypatch):
    """Test 3: A candidate proposed in residual detection can be REJECTED in validation."""
    monkeypatch.setenv("BYPASS_LLM", "false")
    text = "Summary Table: Total Amount Billed"

    fake_gemma = MockGemmaDualDetector(
        residual_map={
            "Amount Billed": [{"value": "Amount Billed", "entity_type": "FINANCIAL_DATA", "confidence_score": 0.85}]
        },
        validation_map={
            "Amount Billed": {"decision": "REJECT", "reason": "Table header label, non-sensitive"},
        },
    )
    service = create_mock_service(fake_gemma)

    results = service.detect(text, document_type="financial")
    # "Amount Billed" was rejected in validation and should not appear in final output
    assert not any(r.entity_value == "Amount Billed" for r in results)


def test_4_residual_candidate_can_be_reclassified_by_validation(monkeypatch):
    """Test 4: A residual candidate can be RECLASSIFIED to corrected type in validation."""
    monkeypatch.setenv("BYPASS_LLM", "false")
    text = "Account Holder: City Union Bank"

    fake_gemma = MockGemmaDualDetector(
        residual_map={
            "City Union Bank": [{"value": "City Union Bank", "entity_type": "PERSON", "confidence_score": 0.88}]
        },
        validation_map={
            "City Union Bank": {"decision": "RECLASSIFY", "corrected_type": "ORGANIZATION", "reason": "Bank name, not person"},
        },
    )
    service = create_mock_service(fake_gemma)

    # This test exercises reclassification itself. A financial document policy
    # may independently mark generic organizations as DROP.
    results = service.detect(text)
    bank = next(r for r in results if r.entity_value == "City Union Bank")
    assert bank.entity_type == "ORGANIZATION"


def test_5_locked_spans_bypass_validation(monkeypatch):
    """Test 5: High-confidence authoritative locked entities bypass validation."""
    monkeypatch.setenv("BYPASS_LLM", "false")
    text = "SSN: 999-88-7777\nPatient: John Doe"
    ssn_start = text.index("999-88-7777")
    ssn_end = ssn_start + len("999-88-7777")

    fake_gemma = MockGemmaDualDetector(
        residual_map={
            "John Doe": [{"value": "John Doe", "entity_type": "PERSON", "confidence_score": 0.92}]
        },
        validation_map={
            "John Doe": {"decision": "CONFIRM"},
        },
    )
    service = create_mock_service(fake_gemma)
    # Regex locks SSN with 1.0 confidence
    service.regex = MockDetector("regex", [
        DetectionResult(entity_type="SSN", entity_value="999-88-7777", confidence_score=1.0, start_char=ssn_start, end_char=ssn_end, detector="Regex")
    ])

    results = service.detect(text, document_type="healthcare")
    # SSN should NOT be sent to validation (it's locked)
    assert "999-88-7777" not in fake_gemma.validated_candidate_values
    # John Doe WAS sent to validation
    assert "John Doe" in fake_gemma.validated_candidate_values
    # Both are present in final results
    values = {r.entity_value for r in results}
    assert "999-88-7777" in values
    assert "John Doe" in values
