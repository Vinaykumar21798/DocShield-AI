import pytest
from unittest.mock import MagicMock

from modules.detection.pipeline_state import PipelineState
from modules.detection.semantic_chunker import SemanticChunker, DocumentChunk
from modules.detection.models.detection_result import DetectionResult
from modules.detection.service import DetectionService
from modules.detection.taxonomy import TaxonomyService


def test_high_confidence_entity_not_duplicated():
    """
    1. High-confidence entity (>= 0.80) is not duplicated by subsequent detectors.
    """
    text = "Patient John Doe visited the clinic."
    state = PipelineState(original_text=text)

    # Initial high-confidence entity detected by Presidio
    initial_person = DetectionResult(
        entity_type="PERSON",
        entity_value="John Doe",
        confidence_score=0.90,
        start_char=8,
        end_char=16,
        page_number=1,
        detector="presidio",
    )
    state.add_entities([initial_person], detector_name="presidio", mask_confidence_threshold=0.80)

    # Downstream detector attempts to re-detect the exact same span with lower or equal confidence
    duplicate_person = DetectionResult(
        entity_type="PERSON",
        entity_value="John Doe",
        confidence_score=0.85,
        start_char=8,
        end_char=16,
        page_number=1,
        detector="gliner",
    )

    accepted = DetectionService._filter_new_entities(
        [duplicate_person],
        state=state,
        detector_name="gliner",
        mask_confidence_threshold=0.80,
    )

    # Duplicate should be suppressed
    assert len(accepted) == 0
    assert len(state.resolved_entities) == 1
    assert state.resolved_entities[0].detector == "presidio"


def test_chunk_reaches_qwen_for_surrounding_unresolved_entities():
    """
    2. Same chunk still reaches Qwen for other missed entities (chunk not skipped).
    """
    text = (
        "Patient John Doe (SSN: 123-45-6789) was admitted with acute myocardial infarction. "
        "Prescribed Atorvastatin 40mg daily."
    )
    chunker = SemanticChunker(max_chunk_chars=300)
    chunks = chunker.chunk_document(text)
    assert len(chunks) == 1
    chunk = chunks[0]

    # Assume SSN was already detected with 0.99 confidence by Regex
    ssn_idx = text.index("123-45-6789")
    resolved_ssn = DetectionResult(
        entity_type="SSN",
        entity_value="123-45-6789",
        confidence_score=0.99,
        start_char=ssn_idx,
        end_char=ssn_idx + 11,
        page_number=1,
        detector="regex",
    )

    # select_relevant_chunks should NOT drop the chunk, because surrounding text exists!
    selected = chunker.select_relevant_chunks(
        chunks,
        candidates=[],
        low_confidence_entities=[],
        resolved_entities=[resolved_ssn],
    )

    assert len(selected) == 1
    assert selected[0].text == text


def test_must_have_entity_missed_by_fast_detectors_detected_by_qwen():
    """
    3. MUST_HAVE entity (e.g. Diagnosis) missed by fast detectors can still be detected by Qwen.
    """
    text = "Patient SSN: 123-45-6789. Clinical diagnosis: malignant hypertension."
    state = PipelineState(original_text=text)

    # Fast detector found SSN
    ssn_idx = text.index("123-45-6789")
    ssn = DetectionResult(
        entity_type="SSN",
        entity_value="123-45-6789",
        confidence_score=0.99,
        start_char=ssn_idx,
        end_char=ssn_idx + 11,
        page_number=1,
        detector="regex",
    )
    state.add_entities([ssn], detector_name="regex", mask_confidence_threshold=0.80)

    # Qwen detects missed diagnosis in the same chunk
    diag_idx = text.index("malignant hypertension")
    qwen_diag = DetectionResult(
        entity_type="DIAGNOSIS",
        entity_value="malignant hypertension",
        confidence_score=0.92,
        start_char=diag_idx,
        end_char=diag_idx + len("malignant hypertension"),
        page_number=1,
        detector="qwen3b",
    )

    accepted = DetectionService._filter_new_entities(
        [qwen_diag],
        state=state,
        detector_name="qwen3b",
        mask_confidence_threshold=0.80,
    )

    # Qwen diagnosis should be accepted
    assert len(accepted) == 1
    assert accepted[0].entity_value == "malignant hypertension"
    assert accepted[0].entity_type == "DIAGNOSIS"


def test_specialization_and_overlap_resolution():
    """
    4. Overlapping detections correctly resolve: generic entity can be specialized or upgraded.
    """
    text = "Dr. Alice Smith performed the consultation."
    state = PipelineState(original_text=text)

    # Generic PERSON detected earlier with moderate confidence
    person_idx = text.index("Alice Smith")
    generic_person = DetectionResult(
        entity_type="PERSON",
        entity_value="Alice Smith",
        confidence_score=0.75,
        start_char=person_idx,
        end_char=person_idx + len("Alice Smith"),
        page_number=1,
        detector="presidio",
    )
    state.add_entities([generic_person], detector_name="presidio", mask_confidence_threshold=0.80)

    # Downstream detector specializes PERSON -> DOCTOR with high confidence
    specialized_doctor = DetectionResult(
        entity_type="DOCTOR",
        entity_value="Alice Smith",
        confidence_score=0.92,
        start_char=person_idx,
        end_char=person_idx + len("Alice Smith"),
        page_number=1,
        detector="gliner",
    )

    accepted = DetectionService._filter_new_entities(
        [specialized_doctor],
        state=state,
        detector_name="gliner",
        mask_confidence_threshold=0.80,
    )

    # The existing entity is upgraded/specialized to DOCTOR
    assert state.resolved_entities[0].entity_type == "DOCTOR"
    assert state.resolved_entities[0].confidence_score == 0.92
    assert state.resolved_entities[0].detector == "gliner"
