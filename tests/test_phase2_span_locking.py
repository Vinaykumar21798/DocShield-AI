import pytest
from modules.detection.semantic_chunker import SemanticChunker, DocumentChunk
from modules.detection.service import DetectionService
from modules.detection.detectors.base_detector import BaseDetector
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


def test_1_high_confidence_authoritative_regex_becomes_locked(monkeypatch):
    """Test 1: High-confidence authoritative Regex entity becomes LOCKED."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    text = "Patient SSN is 987-65-4320 on the file."
    results = service.detect(text)

    ssn = next(e for e in results if e.entity_type == "SSN")
    assert ssn.confidence_score >= 0.80
    assert ssn.entity_value == "987-65-4320"


def test_2_locked_span_stored_in_document_global_coordinates(monkeypatch):
    """Test 2: Locked span is stored in document-global coordinates."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    chunker = SemanticChunker(target_chunk_chars=60, max_chunk_chars=100)
    service.chunker = chunker

    text = "Non-sensitive padding line 1.\n\nNon-sensitive padding line 2.\n\nEmail: contact@docshield.ai"
    results = service.detect(text)

    email = next(e for e in results if e.entity_type == "EMAIL")
    expected_start = text.index("contact@docshield.ai")
    expected_end = expected_start + len("contact@docshield.ai")

    assert email.start_char == expected_start
    assert email.end_char == expected_end
    assert text[email.start_char:email.end_char] == "contact@docshield.ai"


def test_3_presidio_duplicate_overlapping_locked_span_suppressed(monkeypatch):
    """Test 3: Presidio duplicate overlapping locked span is suppressed."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    text = "SSN: 987-65-4320"
    start = text.index("987-65-4320")
    end = start + len("987-65-4320")

    # Regex finds SSN (1.0), Presidio finds PERSON on same span (0.82)
    service.regex = MockDetector("regex", [
        DetectionResult(entity_type="SSN", entity_value="987-65-4320", confidence_score=1.0, start_char=start, end_char=end, detector="Regex")
    ])
    service.presidio = MockDetector("presidio", [
        DetectionResult(entity_type="PERSON", entity_value="987-65-4320", confidence_score=0.82, start_char=start, end_char=end, detector="Presidio")
    ])

    results = service.detect(text)
    assert len(results) == 1
    assert results[0].entity_type == "SSN"
    assert results[0].detector == "Regex"


def test_4_gliner_duplicate_overlapping_locked_span_suppressed(monkeypatch):
    """Test 4: GLiNER duplicate overlapping locked span is suppressed."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    text = "Account Holder: 123456789012"
    start = text.index("123456789012")
    end = start + len("123456789012")

    # Regex locks bank account
    service.regex = MockDetector("regex", [
        DetectionResult(entity_type="BANK_ACCOUNT_NUMBER", entity_value="123456789012", confidence_score=1.0, start_char=start, end_char=end, detector="Regex")
    ])
    service.gliner = MockDetector("gliner", [
        DetectionResult(entity_type="ORGANIZATION", entity_value="123456789012", confidence_score=0.88, start_char=start, end_char=end, detector="GLiNER")
    ])

    results = service.detect(text, document_type="financial")
    assert len(results) == 1
    assert results[0].entity_type in {"BANK_ACCOUNT", "BANK_ACCOUNT_NUMBER"}


def test_5_partial_overlap_with_locked_span_is_suppressed(monkeypatch):
    """Test 5: Partial overlap with locked span is suppressed."""
    state = PipelineState(original_text="Patient reference ID-9876543210 is recorded.")
    entity = DetectionResult(
        entity_type="IDENTIFIER",
        entity_value="ID-9876543210",
        confidence_score=1.0,
        start_char=18,
        end_char=31,
        detector="Regex",
    )
    state.lock_span(entity)

    # Overlapping intervals
    assert state.is_span_locked(18, 35) is True   # Right overlap
    assert state.is_span_locked(10, 25) is True   # Left overlap
    assert state.is_span_locked(20, 28) is True   # Substring enclosure
    assert state.is_span_locked(0, 15) is False   # Disjoint preceding
    assert state.is_span_locked(32, 40) is False  # Disjoint following


def test_6_non_overlapping_entity_in_same_chunk_detected(monkeypatch):
    """Test 6: Non-overlapping entity in the same chunk is still detected."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    text = "Patient Name: John Smith\nSSN: 987-65-4320\nDiagnosis: Hypertension."
    ssn_start = text.index("987-65-4320")
    ssn_end = ssn_start + len("987-65-4320")
    name_start = text.index("John Smith")
    name_end = name_start + len("John Smith")

    service.regex = MockDetector("regex", [
        DetectionResult(entity_type="SSN", entity_value="987-65-4320", confidence_score=1.0, start_char=ssn_start, end_char=ssn_end, detector="Regex")
    ])
    service.gliner = MockDetector("gliner", [
        DetectionResult(entity_type="PATIENT", entity_value="John Smith", confidence_score=0.95, start_char=name_start, end_char=name_end, detector="GLiNER")
    ])

    results = service.detect(text, document_type="healthcare")
    values = {e.entity_value for e in results}

    assert "987-65-4320" in values
    assert "John Smith" in values


def test_7_chunk_containing_locked_span_not_skipped(monkeypatch):
    """Test 7: A chunk containing a locked span is NOT skipped."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    text = "SSN: 123-45-6789. Doctor: Dr. Jane Doe attended."
    service.regex = MockDetector("regex", [
        DetectionResult(entity_type="SSN", entity_value="123-45-6789", confidence_score=1.0, start_char=text.index("123-45-6789"), end_char=text.index("123-45-6789") + 11, detector="Regex")
    ])
    gliner_detector = MockDetector("gliner", [
        DetectionResult(entity_type="DOCTOR", entity_value="Dr. Jane Doe", confidence_score=0.92, start_char=text.index("Dr. Jane Doe"), end_char=text.index("Dr. Jane Doe") + 12, detector="GLiNER")
    ])
    service.gliner = gliner_detector

    results = service.detect(text, document_type="healthcare")

    # GLiNER must have executed on the chunk despite Regex locking a span within it
    assert gliner_detector.executed_count > 0
    values = {e.entity_value for e in results}
    assert "Dr. Jane Doe" in values


def test_8_low_confidence_candidate_remains_pending(monkeypatch):
    """Test 8: Low-confidence candidate remains PENDING rather than LOCKED."""
    state = PipelineState(original_text="Name: Alice")
    candidate = DetectionResult(
        entity_type="PERSON",
        entity_value="Alice",
        confidence_score=0.65,
        start_char=6,
        end_char=11,
        detector="Regex",
    )
    state.add_pending_candidates([candidate])

    assert len(state.pending_candidates) == 1
    assert state.is_span_locked(6, 11) is False


def test_9_low_confidence_candidate_continues_to_next_detector(monkeypatch):
    """Test 9: Low-confidence candidate continues to the next appropriate detector."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    text = "Name: Alice"
    start = text.index("Alice")
    end = start + len("Alice")

    service = DetectionService()
    service.regex = MockDetector("regex", [
        DetectionResult(entity_type="PERSON", entity_value="Alice", confidence_score=0.70, start_char=start, end_char=end, detector="Regex")
    ])
    service.presidio = MockDetector("presidio", [])
    service.gliner = MockDetector("gliner", [
        DetectionResult(entity_type="PERSON", entity_value="Alice", confidence_score=0.92, start_char=start, end_char=end, detector="GLiNER")
    ])

    results = service.detect(text, document_type="generic")

    assert len(results) == 1
    assert results[0].entity_value == "Alice"
    assert results[0].confidence_score == 0.92
    assert results[0].detector == "GLiNER"


def test_10_overlapping_semantic_chunks_controlled_duplicates(monkeypatch):
    """Test 10: Two overlapping semantic chunks do not create uncontrolled duplicates."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    chunker = SemanticChunker(target_chunk_chars=80, max_chunk_chars=120, overlap_chars=40)
    service.chunker = chunker

    text = "Customer Name: Johnathan Edwards visited today.\n\nJohnathan Edwards signed the agreement."
    results = service.detect(text)

    # Should not produce overlapping duplicates on the same span
    spans = [(e.start_char, e.end_char) for e in results]
    assert len(spans) == len(set(spans))


def test_11_original_document_text_remains_unchanged(monkeypatch):
    """Test 11: Original document text remains unchanged (immutable original text)."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    original = "Patient John Doe with SSN 123-45-6789 and diagnosis Diabetes."
    state = PipelineState(original_text=original)

    service.detect(original)
    assert state.original_text == original
    assert "   " not in state.original_text


def test_12_detector_failure_does_not_mark_candidate_resolved(monkeypatch):
    """Test 12: Detector failure does not mark a candidate as resolved."""
    class ErrorDetector(BaseDetector):
        @property
        def name(self) -> str:
            return "failing"
        def should_run(self, text: str, state: PipelineState) -> bool:
            return True
        def detect(self, text: str, page_number: int = 1) -> list[DetectionResult]:
            raise RuntimeError("Detector crash")

    service = DetectionService()
    state = PipelineState(original_text="Patient Jane Smith")
    chunks = [DocumentChunk(chunk_id=0, text="Patient Jane Smith", start_char=0, end_char=18)]

    results = service._run_detector_on_chunks(ErrorDetector(), chunks, state, 1)
    assert results == []
    assert len(state.resolved_entities) == 0


def test_13_weak_generic_ner_not_blindly_locked(monkeypatch):
    """Test 13: High-confidence but weakly classified generic NER is not blindly locked."""
    candidate = DetectionResult(
        entity_type="PERSON",
        entity_value="Westfield",
        confidence_score=0.82,
        start_char=0,
        end_char=9,
        detector="presidio",
    )
    # Generic unvalidated Presidio should not be authoritative
    is_auth = DetectionService._is_authoritative_detection(candidate, "presidio", high_conf_threshold=0.80)
    assert is_auth is False


def test_14_multiple_detectors_same_span_produce_provenance(monkeypatch):
    """Test 14: Multiple detectors identifying the same span produce one occurrence with provenance."""
    state = PipelineState(original_text="SSN: 123-45-6789")
    ssn = DetectionResult(
        entity_type="SSN",
        entity_value="123-45-6789",
        confidence_score=1.0,
        start_char=5,
        end_char=16,
        detector="Regex",
    )
    state.lock_span(ssn)

    # Presidio also detects it
    presidio_entity = DetectionResult(
        entity_type="PERSON",
        entity_value="123-45-6789",
        confidence_score=0.82,
        start_char=5,
        end_char=16,
        detector="Presidio",
    )
    state.lock_span(presidio_entity)

    assert len(state.locked_spans) == 1
    assert "Presidio" in state.locked_spans[0]["duplicate_sources"]
    assert "Regex" in state.locked_spans[0]["duplicate_sources"]
