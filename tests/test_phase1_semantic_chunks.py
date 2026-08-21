import pytest
from modules.detection.semantic_chunker import SemanticChunker, DocumentChunk
from modules.detection.service import DetectionService
from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult
from modules.detection.pipeline_state import PipelineState


class TrackingDetector(BaseDetector):
    def __init__(self, name: str, detections_by_text: dict[str, list[DetectionResult]] | None = None, should_run_flag: bool = True):
        self._name = name
        self.detections_by_text = detections_by_text or {}
        self.should_run_flag = should_run_flag
        self.seen_texts: list[str] = []
        self.seen_spans: list[tuple[int, int]] = []
        self.executed_count = 0

    @property
    def name(self) -> str:
        return self._name

    def should_run(self, text: str, state: PipelineState) -> bool:
        return self.should_run_flag

    def detect(self, text: str, page_number: int = 1) -> list[DetectionResult]:
        self.seen_texts.append(text)
        self.executed_count += 1
        for key, results in self.detections_by_text.items():
            if key in text:
                return results
        return []


class FailingDetector(BaseDetector):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def should_run(self, text: str, state: PipelineState) -> bool:
        return True

    def detect(self, text: str, page_number: int = 1) -> list[DetectionResult]:
        raise RuntimeError(f"Simulated failure in {self.name} detector")


def test_1_document_split_into_semantic_chunks():
    """Test 1: Document is split into semantic chunks."""
    chunker = SemanticChunker(target_chunk_chars=100, max_chunk_chars=200, min_chunk_chars=50)
    text = (
        "SECTION 1: PATIENT INFORMATION\n"
        "Patient Name: Jane Doe\n"
        "Date of Birth: 01/15/1980\n\n"
        "SECTION 2: CLINICAL COURSE & DIAGNOSIS\n"
        "The patient presented with acute abdominal pain and fever.\n"
        "Preliminary diagnosis indicates acute appendicitis.\n\n"
        "SECTION 3: DISCHARGE INSTRUCTIONS & MEDICATION\n"
        "Prescribed Amoxicillin 500mg three times daily for 7 days.\n"
        "Follow up with primary care physician in one week.\n\n"
        "SECTION 4: BILLING AND INSURANCE\n"
        "Policy Number: POL-99887766\n"
        "Insurance Provider: Blue Cross Blue Shield\n"
    )
    chunks = chunker.chunk_document(text)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert isinstance(chunk, DocumentChunk)
        assert chunk.text == text[chunk.start_char:chunk.end_char]
        assert chunk.length == len(chunk.text)


def test_2_every_relevant_chunk_passed_to_regex(monkeypatch):
    """Test 2: Every relevant chunk is passed to Regex."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    chunker = SemanticChunker(target_chunk_chars=80, max_chunk_chars=120)
    service.chunker = chunker

    tracking_regex = TrackingDetector("regex")
    service.regex = tracking_regex

    text = (
        "Part A:\nEmail: alice@example.com\nPhone: +1-202-555-0199\n\n"
        "Part B:\nSSN: 123-45-6789\nInvoice: INV-2026-001\n\n"
        "Part C:\nBank Account: 987654321012\nVisit Date: 12-May-2026\n"
    )
    service.detect(text)

    # All generated chunks were processed by regex
    chunks = chunker.chunk_document(text)
    assert tracking_regex.executed_count == len(chunks)
    assert len(tracking_regex.seen_texts) == len(chunks)
    for i, chunk in enumerate(chunks):
        assert tracking_regex.seen_texts[i] == chunk.text


def test_3_every_relevant_chunk_passed_to_presidio(monkeypatch):
    """Test 3: Every relevant chunk is passed to Presidio."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    chunker = SemanticChunker(target_chunk_chars=80, max_chunk_chars=120)
    service.chunker = chunker

    tracking_presidio = TrackingDetector("presidio")
    service.presidio = tracking_presidio

    text = (
        "First Section: Dr. Robert Smith visited Springfield Medical Center.\n\n"
        "Second Section: Dr. Alice Johnson consulted at Boston Memorial Hospital.\n\n"
        "Third Section: Jane Doe was admitted to Chicago General Clinic.\n"
    )
    service.detect(text)

    chunks = chunker.chunk_document(text)
    assert tracking_presidio.executed_count == len(chunks)
    for i, chunk in enumerate(chunks):
        assert tracking_presidio.seen_texts[i] == chunk.text


def test_4_every_relevant_chunk_passed_to_gliner_when_routed(monkeypatch):
    """Test 4: Every relevant chunk is passed to GLiNER when routing says it is appropriate."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    chunker = SemanticChunker(target_chunk_chars=80, max_chunk_chars=120)
    service.chunker = chunker

    tracking_gliner = TrackingDetector("gliner")
    service.gliner = tracking_gliner

    # Financial domain route includes regex -> presidio -> gliner -> qwen3b
    text = (
        "Statement 1: Account Holder: Nitish Kumar\nBranch: City Union Bank\n\n"
        "Statement 2: Beneficiary: Ramesh Patel\nIFSC: CIUB0000528\n\n"
        "Statement 3: Transferred to Rajesh Sharma via UPI\n"
    )
    service.detect(text, document_type="financial")

    chunks = chunker.chunk_document(text)
    assert tracking_gliner.executed_count == len(chunks)
    for i, chunk in enumerate(chunks):
        assert tracking_gliner.seen_texts[i] == chunk.text


def test_5_every_relevant_chunk_passed_to_medspacy_when_appropriate(monkeypatch):
    """Test 5: Every relevant chunk is passed to MedSpaCy when appropriate."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    chunker = SemanticChunker(target_chunk_chars=80, max_chunk_chars=120)
    service.chunker = chunker

    tracking_medspacy = TrackingDetector("medspacy")
    service.medspacy = tracking_medspacy

    # Healthcare domain route includes regex -> medspacy -> presidio -> gliner -> qwen3b
    text = (
        "Medical Section 1: Patient diagnosed with Hypertension and Type 2 Diabetes.\n\n"
        "Medical Section 2: Started on Metformin 500mg and Lisinopril 10mg daily.\n\n"
        "Medical Section 3: Patient reports occasional chest pain and shortness of breath.\n"
    )
    service.detect(text, document_type="healthcare")

    chunks = chunker.chunk_document(text)
    assert tracking_medspacy.executed_count == len(chunks)
    for i, chunk in enumerate(chunks):
        assert tracking_medspacy.seen_texts[i] == chunk.text


def test_6_detector_local_offsets_correctly_converted_to_global_offsets(monkeypatch):
    """Test 6: Detector local offsets are correctly converted to global offsets."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    chunker = SemanticChunker(target_chunk_chars=60, max_chunk_chars=100)
    service.chunker = chunker

    text = (
        "Prefix block 1 with non-sensitive text padding here.\n\n"
        "Prefix block 2 with more text padding.\n\n"
        "Target Section:\nEmail: target.user@docshield.ai\n"
    )
    chunks = chunker.chunk_document(text)
    assert len(chunks) >= 2

    # Find which chunk contains target.user@docshield.ai
    target_chunk = next(c for c in chunks if "target.user@docshield.ai" in c.text)
    local_start = target_chunk.text.index("target.user@docshield.ai")
    local_end = local_start + len("target.user@docshield.ai")

    # Global expected
    expected_global_start = text.index("target.user@docshield.ai")
    expected_global_end = expected_global_start + len("target.user@docshield.ai")

    assert target_chunk.start_char + local_start == expected_global_start
    assert target_chunk.start_char + local_end == expected_global_end

    results = service.detect(text)
    email_entity = next(e for e in results if e.entity_value == "target.user@docshield.ai")

    assert email_entity.start_char == expected_global_start
    assert email_entity.end_char == expected_global_end
    assert text[email_entity.start_char:email_entity.end_char] == "target.user@docshield.ai"


def test_7_overlapping_semantic_chunks_do_not_create_duplicate_entities(monkeypatch):
    """Test 7: Overlapping semantic chunks do not create duplicate final entities."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    # High overlap
    chunker = SemanticChunker(target_chunk_chars=120, max_chunk_chars=200, overlap_chars=80)
    service.chunker = chunker

    text = (
        "Patient Name: Johnathan Edwards was admitted for evaluation.\n\n"
        "Johnathan Edwards had routine lab blood tests performed yesterday.\n\n"
        "Contact Person: Johnathan Edwards at Phone: 9876543210.\n"
    )
    results = service.detect(text)

    # Ensure no exact duplicate spans exist in resolved output
    spans = [(e.start_char, e.end_char, e.entity_type) for e in results]
    assert len(spans) == len(set(spans)), "Duplicate entity spans detected!"


def test_8_no_document_text_is_physically_masked_before_detectors_process(monkeypatch):
    """Test 8: No document text is physically masked/removed before detectors process it."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    chunker = SemanticChunker(target_chunk_chars=200, max_chunk_chars=400)
    service.chunker = chunker

    tracking_regex = TrackingDetector("regex")
    tracking_presidio = TrackingDetector("presidio")
    service.regex = tracking_regex
    service.presidio = tracking_presidio

    text = "Patient Name: Dr. Robert Chen has Account Number: 123456789 and Diagnosis: Diabetes."
    service.detect(text)

    # Verify both detectors received exact untouched text without spaces replacing characters
    for seen in tracking_regex.seen_texts:
        assert "  " not in seen or "  " in text
        assert "Dr. Robert Chen" in seen or "Account Number" in seen
    for seen in tracking_presidio.seen_texts:
        assert seen in text or text in seen


def test_9_detector_failure_is_logged_separately_from_zero_detections(monkeypatch, caplog):
    """Test 9: Detector failure is logged separately from zero detections."""
    import logging
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    chunker = SemanticChunker(target_chunk_chars=200, max_chunk_chars=400)
    service.chunker = chunker

    # Test directly via chunk runner and pipeline
    failing_detector = FailingDetector("presidio")
    chunks = [DocumentChunk(chunk_id=0, text="Some medical notes for patient John Doe", start_char=0, end_char=39)]
    state = PipelineState(original_text="Some medical notes for patient John Doe")

    with caplog.at_level(logging.ERROR):
        results = service._run_detector_on_chunks(
            detector=failing_detector,
            chunks=chunks,
            state=state,
            page_number=1,
        )

    # Pipeline should not crash, and status=FAILED should be logged
    assert results == []
    assert any("status=FAILED" in record.message for record in caplog.records)
    assert any("Simulated failure in presidio detector" in record.message for record in caplog.records)


def test_10_all_document_characters_covered_by_semantic_chunks():
    """Test 10: All document characters are covered by semantic chunks."""
    chunker = SemanticChunker(target_chunk_chars=150, max_chunk_chars=250, overlap_chars=50)
    text = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer nec odio. Praesent libero.\n\n"
        "Sed cursus ante dapibus diam. Sed nisi. Nulla quis sem at nibh elementum imperdiet.\n\n"
        "Duis sagittis ipsum. Praesent mauris. Fusce nec tellus sed augue semper porta.\n\n"
        "Mauris massa. Vestibulum lacinia arcu eget nulla. Class aptent taciti sociosqu ad litora.\n\n"
        "Torquent per conubia nostra, per inceptos himenaeos. Curabitur sodales ligula in libero."
    )
    chunks = chunker.chunk_document(text)
    assert len(chunks) > 1

    total_len = len(text)
    covered_indices = set()
    for chunk in chunks:
        assert chunk.start_char < chunk.end_char
        assert chunk.text == text[chunk.start_char:chunk.end_char]
        covered_indices.update(range(chunk.start_char, chunk.end_char))

    covered_chars = len(covered_indices)
    assert covered_chars == total_len, f"Gaps found! Covered {covered_chars}/{total_len} chars"
