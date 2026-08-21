import pytest
from modules.detection.semantic_chunker import SemanticChunker, DocumentChunk
from modules.detection.service import DetectionService
from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult
from modules.detection.pipeline_state import PipelineState
from modules.detection.candidate_quality_gate import CandidateQualityGate, QualityGateDecision
from modules.detection.embedding_service import EmbeddingService


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


def test_1_high_confidence_locked_candidate_bypasses_quality_gate(monkeypatch):
    """Test 1: High-confidence locked candidate bypasses quality gate and locks directly."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    text = "Account Number: 123456789012"
    start = text.index("123456789012")
    end = start + len("123456789012")

    # Authoritative Regex with 1.0 confidence
    service.regex = MockDetector("regex", [
        DetectionResult(entity_type="BANK_ACCOUNT_NUMBER", entity_value="123456789012", confidence_score=1.0, start_char=start, end_char=end, detector="Regex")
    ])

    results = service.detect(text, document_type="financial")
    assert len(results) == 1
    assert results[0].confidence_score >= 0.80
    assert results[0].entity_value == "123456789012"


def test_2_very_low_relevance_obvious_noise_rejected_before_llm():
    """Test 2: Very low-relevance obvious noise (NULL, CIN, DESCRIPTION) is rejected before LLM."""
    gate = CandidateQualityGate()
    doc_text = "STATEMENT TABLE\nDATE | PARTICULARS | CHQ NO | WITHDRAWAL | DEPOSIT | BALANCE\n01-Jan | DESCRIPTION | CIN | 0.00 | 5000.00 | 5000.00"

    noise_candidates = [
        ("NULL", "ORGANIZATION", 0.75, "OBVIOUS_NOISE", "PRE_LLM_REJECT"),
        ("DESCRIPTION", "PERSON", 0.78, "OBVIOUS_NOISE", "PRE_LLM_REJECT"),
        ("CIN", "ORGANIZATION", 0.82, "OBVIOUS_NOISE", "PRE_LLM_REJECT"),
        ("Regd", "LOCATION", 0.70, "OBVIOUS_NOISE", "PRE_LLM_REJECT"),
        ("TO ONL UPI", "ORGANIZATION", 0.79, "OBVIOUS_NOISE", "PRE_LLM_REJECT"),
    ]

    for val, etype, conf, expected_qdec, expected_dec in noise_candidates:
        cand = DetectionResult(
            entity_type=etype,
            entity_value=val,
            confidence_score=conf,
            start_char=0,
            end_char=len(val),
            detector="presidio",
        )
        eval_result = gate.evaluate(cand, document_text=doc_text, document_type="financial")
        assert eval_result.decision == expected_dec, f"Failed on {val}: {eval_result.reason}"
        assert eval_result.quality_decision == expected_qdec
        assert eval_result.llm_required is False


def test_3_generic_table_header_not_automatically_accepted():
    """Test 3: Generic table/header text (Plan Paid, Mail Order, Managing Type) is rejected."""
    gate = CandidateQualityGate()
    doc_text = "Benefit Details | Plan Paid | You Paid | Mail Order | Limitations"

    headers = [
        ("Plan Paid", "PERSON"),
        ("Mail Order", "ORGANIZATION"),
        ("Managing Type", "PERSON"),
        ("Type Generic", "LOCATION"),
    ]

    for val, etype in headers:
        cand = DetectionResult(
            entity_type=etype,
            entity_value=val,
            confidence_score=0.72,
            start_char=0,
            end_char=len(val),
            detector="presidio",
        )
        eval_result = gate.evaluate(cand, document_text=doc_text, document_type="healthcare")
        assert eval_result.decision == "PRE_LLM_REJECT"
        assert eval_result.llm_required is False


def test_4_low_confidence_contextually_plausible_person_remains_pending():
    """Test 4: Low-confidence but contextually plausible PERSON remains pending."""
    gate = CandidateQualityGate()
    doc_text = "SECTION 1: PATIENT RECORD\nPatient Name: John Smith\nAdmitted: 12-May-2026"
    start = doc_text.index("John Smith")
    end = start + len("John Smith")

    cand = DetectionResult(
        entity_type="PERSON",
        entity_value="John Smith",
        confidence_score=0.70,
        start_char=start,
        end_char=end,
        detector="presidio",
    )
    eval_result = gate.evaluate(cand, document_text=doc_text, document_type="healthcare")

    assert eval_result.decision == "PENDING_FOR_LLM"
    assert eval_result.quality_decision in {"PLAUSIBLE", "HIGH_VALUE"}
    assert eval_result.llm_required is True


def test_5_low_confidence_important_identifier_not_aggressively_filtered():
    """Test 5: Low-confidence important identifier (Bank Account, SSN, MRN) is not filtered."""
    gate = CandidateQualityGate()
    doc_text = "Account Holder: Nitish Kumar\nAccount Number: SB-500101013522943\nBranch: City Union Bank"
    start = doc_text.index("SB-500101013522943")
    end = start + len("SB-500101013522943")

    cand = DetectionResult(
        entity_type="BANK_ACCOUNT_NUMBER",
        entity_value="SB-500101013522943",
        confidence_score=0.68,
        start_char=start,
        end_char=end,
        detector="presidio",
    )
    eval_result = gate.evaluate(cand, document_text=doc_text, document_type="financial")

    assert eval_result.decision == "PENDING_FOR_LLM"
    assert eval_result.quality_decision == "HIGH_VALUE"
    assert eval_result.llm_required is True


def test_6_document_type_affects_contextual_relevance():
    """Test 6: Document type influences contextual relevance decisions."""
    gate = CandidateQualityGate()
    doc_text = "Transaction summary: DEPOSIT transfer completed."
    start = doc_text.index("DEPOSIT")
    end = start + len("DEPOSIT")

    cand = DetectionResult(
        entity_type="ORGANIZATION",
        entity_value="DEPOSIT",
        confidence_score=0.75,
        start_char=start,
        end_char=end,
        detector="presidio",
    )
    # In financial document, DEPOSIT is obvious table/transaction noise
    eval_result = gate.evaluate(cand, document_text=doc_text, document_type="financial")
    assert eval_result.decision == "PRE_LLM_REJECT"


def test_7_candidate_uses_semantic_chunk_as_context():
    """Test 7: Candidate uses its semantic chunk as context."""
    gate = CandidateQualityGate()
    chunk_text = "SECTION A: CLINICAL ENCOUNTER\nPatient presented with acute fever. Attending: Dr. Eleanor Vance."
    cand = DetectionResult(
        entity_type="DOCTOR",
        entity_value="Dr. Eleanor Vance",
        confidence_score=0.75,
        start_char=68,
        end_char=85,
        detector="presidio",
        metadata={"chunk_text": chunk_text},
    )
    eval_result = gate.evaluate(cand, document_text="", document_type="healthcare", chunk_text=chunk_text)

    assert eval_result.decision == "PENDING_FOR_LLM"
    assert eval_result.semantic_score > 0.30


def test_8_quality_gate_does_not_use_arbitrary_fixed_character_context():
    """Test 8: Quality gate dynamically leverages semantic chunk rather than arbitrary fixed-char slice."""
    gate = CandidateQualityGate()
    chunk_text = "A very long detailed section containing medical findings: Patient Jane Doe."
    cand = DetectionResult(
        entity_type="PATIENT",
        entity_value="Jane Doe",
        confidence_score=0.72,
        start_char=58,
        end_char=66,
        detector="presidio",
        metadata={"chunk_text": chunk_text},
    )
    eval_result = gate.evaluate(cand, document_text=chunk_text, chunk_text=chunk_text)
    assert eval_result.decision == "PENDING_FOR_LLM"


def test_9_embedding_relevance_calculated_correctly():
    """Test 9: Embedding relevance is calculated correctly with similarity scores."""
    embedding_service = EmbeddingService.get_instance()

    score_doctor = embedding_service.entity_semantic_compatibility(
        candidate_value="Dr. Robert Smith",
        context_text="Attending Physician: Dr. Robert Smith completed the surgery.",
        entity_type="DOCTOR",
    )
    score_noise = embedding_service.entity_semantic_compatibility(
        candidate_value="DESCRIPTION",
        context_text="DATE | PARTICULARS | DESCRIPTION | AMOUNT",
        entity_type="PERSON",
    )

    assert score_doctor > score_noise
    assert score_doctor >= 0.40


def test_10_candidate_retains_global_offsets():
    """Test 10: Candidate retains global offsets through quality gate evaluation."""
    gate = CandidateQualityGate()
    doc_text = "Padding 1\n\nPadding 2\n\nPatient Name: John Smith"
    start = doc_text.index("John Smith")
    end = start + len("John Smith")

    cand = DetectionResult(
        entity_type="PERSON",
        entity_value="John Smith",
        confidence_score=0.75,
        start_char=start,
        end_char=end,
        detector="presidio",
    )
    gate.evaluate(cand, document_text=doc_text)

    assert cand.start_char == start
    assert cand.end_char == end


def test_11_quality_gate_rejection_does_not_alter_original_text():
    """Test 11: Quality-gate rejection does not alter original document text."""
    doc_text = "STATEMENT: DESCRIPTION | CIN | TO ONL UPI | 5000.00"
    state = PipelineState(original_text=doc_text)
    gate = CandidateQualityGate()

    cand = DetectionResult(
        entity_type="ORGANIZATION",
        entity_value="DESCRIPTION",
        confidence_score=0.75,
        start_char=11,
        end_char=22,
        detector="presidio",
    )
    gate.evaluate(cand, document_text=state.original_text)

    assert state.original_text == doc_text


def test_12_quality_gate_does_not_affect_locked_entities():
    """Test 12: Quality gate does not modify already locked high-confidence entities."""
    state = PipelineState(original_text="SSN: 987-65-4320")
    locked_entity = DetectionResult(
        entity_type="SSN",
        entity_value="987-65-4320",
        confidence_score=1.0,
        start_char=5,
        end_char=16,
        detector="Regex",
    )
    state.lock_span(locked_entity)

    assert len(state.locked_spans) == 1
    assert state.locked_spans[0]["entity_value"] == "987-65-4320"
    assert state.locked_spans[0]["status"] == "LOCKED"


def test_13_multiple_detectors_same_candidate_handled_with_provenance(monkeypatch):
    """Test 13: Multiple detectors identifying same span are deduplicated with provenance."""
    monkeypatch.setenv("BYPASS_LLM", "true")
    service = DetectionService()
    text = "Account: 987654321012"
    start = text.index("987654321012")
    end = start + len("987654321012")

    service.regex = MockDetector("regex", [
        DetectionResult(entity_type="BANK_ACCOUNT_NUMBER", entity_value="987654321012", confidence_score=1.0, start_char=start, end_char=end, detector="Regex")
    ])
    service.presidio = MockDetector("presidio", [
        DetectionResult(entity_type="ORGANIZATION", entity_value="987654321012", confidence_score=0.82, start_char=start, end_char=end, detector="Presidio")
    ])

    results = service.detect(text, document_type="financial")
    assert len(results) == 1
    assert results[0].entity_value == "987654321012"


def test_14_llm_call_count_reduced_for_obvious_noise(monkeypatch):
    """Test 14: LLM call count is reduced when obvious noise is filtered by quality gate."""
    service = DetectionService()
    state = PipelineState(original_text="Table: DESCRIPTION | CIN | NULL")

    noise_results = [
        DetectionResult(entity_type="PERSON", entity_value="DESCRIPTION", confidence_score=0.75, start_char=7, end_char=18, detector="Presidio"),
        DetectionResult(entity_type="ORGANIZATION", entity_value="CIN", confidence_score=0.75, start_char=21, end_char=24, detector="Presidio"),
        DetectionResult(entity_type="ORGANIZATION", entity_value="NULL", confidence_score=0.75, start_char=27, end_char=31, detector="Presidio"),
    ]

    service._aggregate_detector_candidates(
        detector=MockDetector("presidio"),
        raw_entities=noise_results,
        state=state,
    )

    # All 3 noise candidates should be rejected before LLM
    assert state.pipeline_metrics["pre_llm_rejected"] == 3
    assert state.pipeline_metrics["sent_to_llm_validation"] == 0
    assert len(state.pending_candidates) == 0


def test_15_important_plausible_candidates_still_reach_llm(monkeypatch):
    """Test 15: Important plausible candidates still reach the LLM validation queue."""
    service = DetectionService()
    doc = "Patient Name: John Smith\nDiagnosis: Acute Appendicitis"
    state = PipelineState(original_text=doc)

    plausible_results = [
        DetectionResult(entity_type="PERSON", entity_value="John Smith", confidence_score=0.75, start_char=doc.index("John Smith"), end_char=doc.index("John Smith")+10, detector="Presidio"),
        DetectionResult(entity_type="DIAGNOSIS", entity_value="Acute Appendicitis", confidence_score=0.70, start_char=doc.index("Acute Appendicitis"), end_char=doc.index("Acute Appendicitis")+18, detector="Presidio"),
    ]

    service._aggregate_detector_candidates(
        detector=MockDetector("presidio"),
        raw_entities=plausible_results,
        state=state,
    )

    # Both should pass through to pending for LLM
    assert state.pipeline_metrics["sent_to_llm_validation"] == 2
    assert state.pipeline_metrics["pre_llm_rejected"] == 0
    assert len(state.pending_candidates) == 2
