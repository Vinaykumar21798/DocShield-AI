import pytest
from modules.detection.pipeline_state import PipelineState
from modules.detection.semantic_chunker import SemanticChunker
from modules.detection.taxonomy import TaxonomyService
from modules.detection.entity_mapper import EntityMapper
from modules.detection.models.detection_result import DetectionResult

def test_mask_manager_absence():
    # Verify MaskManager cannot be imported and PipelineState uses direct span tracking
    with pytest.raises(ImportError):
        from modules.detection import mask_manager  # type: ignore

    text = "Patient John Doe visited City Hospital on 2024-01-15."
    state = PipelineState(original_text=text)
    
    # Add a high-confidence entity
    entity = DetectionResult(
        entity_type="PERSON",
        entity_value="John Doe",
        confidence_score=0.95,
        start_char=8,
        end_char=16,
        page_number=1,
        detector="regex",
    )
    state.add_entities([entity], detector_name="regex")
    
    # Overlapping span should now be masked (claimed)
    assert state.is_span_unmasked(8, 16) is False
    assert state.is_span_unmasked(10, 14) is False
    
    # Non-overlapping span should remain unmasked
    assert state.is_span_unmasked(25, 38) is True
    assert state.current_text == text

def test_semantic_chunker_offset_and_overlap():
    text = (
        "SECTION 1: CLINICAL SUMMARY\n\n"
        "Patient Jane Doe presented with severe headache.\n"
        "Blood pressure was recorded as 140/90.\n\n"
        "SECTION 2: TREATMENT PLAN\n\n"
        "Prescribed Lisinopril 10mg daily.\n"
        "Follow up in two weeks.\n\n"
        "SECTION 3: BILLING INFORMATION\n\n"
        "Insurance Member ID: W123456789. Group: G9876.\n"
    )
    chunker = SemanticChunker(max_chunk_chars=150, overlap_chars=25)
    chunks = chunker.chunk_document(text)
    assert len(chunks) >= 2

    # Verify global offsets
    for chunk in chunks:
        assert text[chunk.start_char:chunk.end_char] == chunk.text

    # Verify candidate relevance selection
    member_idx = text.index("W123456789")
    candidates = [{"start": member_idx, "end": member_idx + 10, "text": "W123456789"}]
    selected = chunker.select_relevant_chunks(chunks, candidates=candidates)
    assert len(selected) >= 1
    assert any("W123456789" in c.text for c in selected)

def test_taxonomy_must_have_nice_to_have_and_drop():
    doc_type = "Medical Record / Clinical Note"
    
    # MUST_HAVE checks
    assert TaxonomyService.get_priority("FULL NAME / PERSON NAME", doc_type) == "MUST_HAVE"
    assert TaxonomyService.should_mask("FULL NAME / PERSON NAME", doc_type) is True
    assert TaxonomyService.is_must_have("MEDICAL RECORD NUMBER (MRN)", doc_type) is True
    assert TaxonomyService.should_mask("MEDICAL RECORD NUMBER (MRN)", doc_type) is True

    # NICE_TO_HAVE checks
    assert TaxonomyService.get_priority("PROCEDURE CODE / DESCRIPTION", doc_type) == "NICE_TO_HAVE"
    assert TaxonomyService.should_mask("PROCEDURE CODE / DESCRIPTION", doc_type) is True
    assert TaxonomyService.is_nice_to_have("ALLERGY INFORMATION", doc_type) is True
    assert TaxonomyService.should_mask("ALLERGY INFORMATION", doc_type) is True

    # DROP checks
    assert TaxonomyService.get_priority("MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER", "Lab Report / Pathology Report") == "DROP"
    assert TaxonomyService.is_drop("MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER", "Lab Report / Pathology Report") is True
    assert TaxonomyService.should_mask("MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER", "Lab Report / Pathology Report") is False
    assert TaxonomyService.should_target("MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER", "Lab Report / Pathology Report") is False

def test_entity_mapper_taxonomy_enrichment():
    entities = [
        DetectionResult(
            entity_type="PERSON",
            entity_value="John Doe",
            confidence_score=0.90,
            start_char=0,
            end_char=8,
            page_number=1,
            detector="presidio",
        ),
        DetectionResult(
            entity_type="PROCEDURE",
            entity_value="Appendectomy",
            confidence_score=0.85,
            start_char=20,
            end_char=32,
            page_number=1,
            detector="medspacy",
        ),
        DetectionResult(
            entity_type="DEVICE_SERIAL_NUMBER",
            entity_value="SN-998822",
            confidence_score=0.80,
            start_char=40,
            end_char=49,
            page_number=1,
            detector="regex",
        ),
    ]

    normalized = EntityMapper.normalize(entities, document_type="Medical Record / Clinical Note")
    
    person = next(e for e in normalized if e.entity_value == "John Doe")
    assert person.metadata["policy_priority"] == "MUST_HAVE"
    assert person.metadata["should_mask"] is True

    proc = next(e for e in normalized if e.entity_value == "Appendectomy")
    assert proc.metadata["policy_priority"] in {"MUST_HAVE", "NICE_TO_HAVE"}
    assert proc.metadata["should_mask"] is True
