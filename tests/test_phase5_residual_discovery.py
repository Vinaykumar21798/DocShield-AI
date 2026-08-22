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


class FakeGemmaResidualDetector(BaseDetector):
    def __init__(self, residual_map: dict[str, list[dict]] | None = None):
        self._name = "gemma"
        self.MODEL_NAME = "gemma4:e4b"
        self.residual_map = residual_map or {}
        self.seen_residual_chunks = []

    @property
    def name(self) -> str:
        return self._name

    def should_run(self, text: str, state: PipelineState) -> bool:
        return True

    def detect(self, text: str, page_number: int = 1) -> list[DetectionResult]:
        return []

    def validate_candidates(
        self,
        candidates: list[DetectionResult],
        chunks: list[Any],
        document_type: str | None = None,
    ) -> list[DetectionResult]:
        return candidates

    def detect_residual_chunk(
        self,
        chunk_text: str,
        chunk_start: int,
        chunk_end: int,
        known_entities: list[DetectionResult] | None = None,
        document_type: str | None = None,
        page_number: int = 1,
    ) -> list[DetectionResult]:
        self.seen_residual_chunks.append({
            "chunk_text": chunk_text,
            "chunk_start": chunk_start,
            "chunk_end": chunk_end,
            "known_entities": known_entities or [],
            "document_type": document_type,
        })
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
                                    "validator": "gemma4:e4b",
                                    "residual_discovery": True,
                                    "residual_reason": item.get("reason", "Discovered in residual review"),
                                },
                            )
                        )
        return results


def create_mock_service(fake_gemma=None):
    service = DetectionService()
    service.regex = MockDetector("regex")
    service.presidio = MockDetector("presidio")
    service.gliner = MockDetector("gliner")
    service.medspacy = MockDetector("medspacy")
    service.gemma = fake_gemma or FakeGemmaResidualDetector()
    return service


def test_1_coverage_90_percent_with_unresolved_account_number():
    """Test 1: Coverage = 90%, but unresolved account number exists -> PARTIALLY_COVERED -> Sent to Gemma."""
    text = "A" * 900 + " Account Number: SB-500101013522943"
    chunk = DocumentChunk(chunk_id=1, start_char=0, end_char=len(text), text=text, section_name="ACCOUNT")
    resolved_entity = DetectionResult(
        entity_type="ORGANIZATION",
        entity_value="A" * 900,
        confidence_score=1.0,
        start_char=0,
        end_char=900,
        detector="Regex",
    )

    eval_result = DetectionService.evaluate_chunk_coverage(chunk, [resolved_entity], text)
    assert eval_result["coverage_percentage"] >= 90.0
    assert eval_result["coverage_status"] == "PARTIALLY_COVERED"
    assert eval_result["meaningful_unresolved_regions"] >= 1
    assert eval_result["skip_residual_detection"] is False
    assert eval_result["high_risk_context"] is True


def test_2_coverage_80_percent_with_unresolved_patient_name():
    """Test 2: Coverage = 80%, but unresolved patient name exists -> PARTIALLY_COVERED -> Sent to Gemma."""
    text = "HOSPITAL RECORD: " + "X" * 80 + " Patient: Eleanor Vance"
    chunk = DocumentChunk(chunk_id=1, start_char=0, end_char=len(text), text=text, section_name="CLINICAL")
    resolved_entity = DetectionResult(
        entity_type="FACILITY",
        entity_value="HOSPITAL RECORD: " + "X" * 80,
        confidence_score=0.95,
        start_char=0,
        end_char=len("HOSPITAL RECORD: " + "X" * 80),
        detector="Presidio",
    )

    eval_result = DetectionService.evaluate_chunk_coverage(chunk, [resolved_entity], text)
    assert eval_result["coverage_status"] in {"PARTIALLY_COVERED", "INSUFFICIENTLY_COVERED"}
    assert eval_result["skip_residual_detection"] is False
    assert eval_result["high_risk_context"] is True


def test_3_coverage_70_percent_all_meaningful_regions_resolved():
    """Test 3: Coverage = 70%, and remaining 30% is only whitespace/delimiters -> FULLY_COVERED -> Skip."""
    text = "Patient SSN: 123-45-6789\n\n   |   \n\n"
    ssn_start = text.index("123-45-6789")
    ssn_end = ssn_start + len("123-45-6789")
    chunk = DocumentChunk(chunk_id=1, start_char=0, end_char=len(text), text=text, section_name="ID")
    resolved_entity = DetectionResult(
        entity_type="SSN",
        entity_value="123-45-6789",
        confidence_score=1.0,
        start_char=ssn_start,
        end_char=ssn_end,
        detector="Regex",
    )

    eval_result = DetectionService.evaluate_chunk_coverage(chunk, [resolved_entity], text)
    assert eval_result["meaningful_unresolved_regions"] == 0
    assert eval_result["coverage_status"] == "FULLY_COVERED"
    assert eval_result["skip_residual_detection"] is True


def test_4_locked_ssn_with_ordinary_label_only():
    """Test 4: Only a locked SSN exists and surrounding text is ordinary label/whitespace -> FULLY_COVERED -> Skip."""
    text = "SSN: 999-88-7777\n"
    chunk = DocumentChunk(chunk_id=1, start_char=0, end_char=len(text), text=text, section_name="ID")
    resolved_entity = DetectionResult(
        entity_type="SSN",
        entity_value="999-88-7777",
        confidence_score=1.0,
        start_char=text.index("999-88-7777"),
        end_char=text.index("999-88-7777") + 11,
        detector="Regex",
    )

    eval_result = DetectionService.evaluate_chunk_coverage(chunk, [resolved_entity], text)
    assert eval_result["coverage_status"] == "FULLY_COVERED"
    assert eval_result["skip_residual_detection"] is True


def test_5_locked_ssn_with_unresolved_diagnosis():
    """Test 5: Sparse SSN coverage with unresolved diagnosis is sent to Gemma."""
    text = "SSN: 999-88-7777\nDiagnosis: malignant hypertension"
    chunk = DocumentChunk(chunk_id=1, start_char=0, end_char=len(text), text=text, section_name="CLINICAL")
    resolved_entity = DetectionResult(
        entity_type="SSN",
        entity_value="999-88-7777",
        confidence_score=1.0,
        start_char=text.index("999-88-7777"),
        end_char=text.index("999-88-7777") + 11,
        detector="Regex",
    )

    eval_result = DetectionService.evaluate_chunk_coverage(chunk, [resolved_entity], text)
    assert eval_result["meaningful_unresolved_regions"] >= 1
    assert eval_result["coverage_status"] == "INSUFFICIENTLY_COVERED"
    assert eval_result["skip_residual_detection"] is False


def test_6_locked_phone_with_unresolved_account_number():
    """Test 6: Locked phone exists, but account number remains unresolved -> Sent to Gemma."""
    text = "Phone: 555-123-4567\nAccount Number: SB-5001010135"
    chunk = DocumentChunk(chunk_id=1, start_char=0, end_char=len(text), text=text, section_name="CONTACT")
    resolved_entity = DetectionResult(
        entity_type="PHONE_NUMBER",
        entity_value="555-123-4567",
        confidence_score=1.0,
        start_char=text.index("555-123-4567"),
        end_char=text.index("555-123-4567") + 12,
        detector="Regex",
    )

    eval_result = DetectionService.evaluate_chunk_coverage(chunk, [resolved_entity], text)
    assert eval_result["skip_residual_detection"] is False
    assert eval_result["meaningful_unresolved_regions"] >= 1


def test_7_no_detector_found_anything():
    """Test 7: No detector found anything -> UNCOVERED -> Sent to Gemma."""
    text = "Completely unextracted clinical text regarding patient treatment."
    chunk = DocumentChunk(chunk_id=1, start_char=0, end_char=len(text), text=text, section_name="NOTES")

    eval_result = DetectionService.evaluate_chunk_coverage(chunk, [], text)
    assert eval_result["coverage_status"] == "UNCOVERED"
    assert eval_result["skip_residual_detection"] is False


def test_8_several_entities_detected_with_unresolved_region():
    """Test 8: Multiple entities detected but important semantic region remains unresolved -> Sent to Gemma."""
    text = "Dr. Alice evaluated John Doe at City Hospital. Medication prescribed: Metformin 500mg."
    chunk = DocumentChunk(chunk_id=1, start_char=0, end_char=len(text), text=text, section_name="RX")
    resolved_entities = [
        DetectionResult(entity_type="DOCTOR", entity_value="Dr. Alice", confidence_score=0.95, start_char=0, end_char=9, detector="GLiNER"),
        DetectionResult(entity_type="PERSON", entity_value="John Doe", confidence_score=0.95, start_char=20, end_char=28, detector="Presidio"),
        DetectionResult(entity_type="ORGANIZATION", entity_value="City Hospital", confidence_score=0.95, start_char=32, end_char=45, detector="Presidio"),
    ]

    eval_result = DetectionService.evaluate_chunk_coverage(chunk, resolved_entities, text)
    assert eval_result["meaningful_unresolved_regions"] >= 1
    assert eval_result["skip_residual_detection"] is False


def test_9_unresolved_region_only_punctuation_delimiters():
    """Test 9: Unresolved region contains only delimiters/formatting -> FULLY_COVERED -> Skip."""
    text = "Name: [Alice Smith] | ID: [99281]"
    chunk = DocumentChunk(chunk_id=1, start_char=0, end_char=len(text), text=text, section_name="HEADER")
    resolved_entities = [
        DetectionResult(entity_type="PERSON", entity_value="Alice Smith", confidence_score=1.0, start_char=text.index("Alice Smith"), end_char=text.index("Alice Smith") + 11, detector="Presidio"),
        DetectionResult(entity_type="CUSTOMER_ID", entity_value="99281", confidence_score=1.0, start_char=text.index("99281"), end_char=text.index("99281") + 5, detector="Regex"),
    ]

    eval_result = DetectionService.evaluate_chunk_coverage(chunk, resolved_entities, text)
    assert eval_result["coverage_status"] == "FULLY_COVERED"
    assert eval_result["skip_residual_detection"] is True


def test_10_residual_gemma_entity_overlaps_locked_span(monkeypatch):
    """Test 10: Residual Gemma entity overlapping an already locked span is suppressed as duplicate."""
    monkeypatch.setenv("BYPASS_LLM", "false")
    text = "SSN: 999-88-7777\nPatient: John Doe"
    ssn_start = text.index("999-88-7777")
    ssn_end = ssn_start + len("999-88-7777")

    fake_gemma = FakeGemmaResidualDetector({
        "999-88-7777": [
            {"value": "999-88-7777", "entity_type": "SSN", "confidence_score": 0.90, "reason": "SSN"},
            {"value": "John Doe", "entity_type": "PERSON", "confidence_score": 0.92, "reason": "Patient name"},
        ]
    })
    service = create_mock_service(fake_gemma)
    service.regex = MockDetector("regex", [
        DetectionResult(entity_type="SSN", entity_value="999-88-7777", confidence_score=1.0, start_char=ssn_start, end_char=ssn_end, detector="Regex")
    ])

    results = service.detect(text, document_type="healthcare")
    ssn_matches = [r for r in results if r.entity_value == "999-88-7777"]
    assert len(ssn_matches) == 1
    assert ssn_matches[0].detector == "Regex"
    assert any(r.entity_value == "John Doe" for r in results)


def test_11_security_regression_test_proves_old_percentage_rule_failure(monkeypatch):
    """
    Test 11 (Security Regression Test):
    Chunk = 1000 characters.
    Detected text = 900 characters (90% coverage).
    Unresolved text = 100 characters containing 'Account Number: SB-500101013522943'.

    Under the old 65% rule:
      Coverage = 90% >= 65% -> FULLY_COVERED -> Skipped! (FALSE NEGATIVE BREACH).

    Under the new Span-Level Coverage Logic:
      Meaningful unresolved region detected -> PARTIALLY_COVERED -> Sent to Gemma -> Entity Recovered!
    """
    monkeypatch.setenv("BYPASS_LLM", "false")
    header_block = "STATEMENT HEADER RECORD " * 37 + "DATA "
    header_block = header_block[:900]
    unresolved_block = "\nAccount Number: SB-500101013522943"
    text = header_block + unresolved_block

    fake_gemma = FakeGemmaResidualDetector({
        "SB-500101013522943": [{
            "value": "SB-500101013522943",
            "entity_type": "BANK_ACCOUNT_NUMBER",
            "confidence_score": 0.96,
            "reason": "Non-standard bank account number in unresolved statement region",
        }]
    })
    service = create_mock_service(fake_gemma)

    # Upstream detector only detected the 900-char header block
    service.presidio = MockDetector("presidio", [
        DetectionResult(entity_type="ORGANIZATION", entity_value=header_block[:20], confidence_score=1.0, start_char=0, end_char=900, detector="Presidio")
    ])

    results = service.detect(text, document_type="financial")
    # Verify the chunk was NOT skipped and the account number was successfully recovered
    assert any(r.entity_value == "SB-500101013522943" for r in results)
    recovered = next(r for r in results if r.entity_value == "SB-500101013522943")
    assert recovered.entity_type == "BANK_ACCOUNT_NUMBER"
    assert recovered.metadata.get("llm_mode") == "RESIDUAL_DETECTION"
    assert recovered.metadata.get("residual_discovery") is True
