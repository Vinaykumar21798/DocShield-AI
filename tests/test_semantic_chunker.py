import pytest
from modules.detection.semantic_chunker import SemanticChunker, DocumentChunk
from modules.detection.models.detection_result import DetectionResult

def test_semantic_chunker_small_text():
    text = "Patient Name: Jane Doe. Diagnosis: Hypertension."
    chunker = SemanticChunker(max_chunk_chars=1000)
    chunks = chunker.chunk_document(text)
    assert len(chunks) == 1
    assert chunks[0].start_char == 0
    assert chunks[0].end_char == len(text)
    assert chunks[0].text == text

def test_semantic_chunker_paragraph_splitting():
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
    chunker = SemanticChunker(max_chunk_chars=120, overlap_chars=20)
    chunks = chunker.chunk_document(text)
    assert len(chunks) > 1

    for chunk in chunks:
        # Verify slice in original text equals chunk text
        assert text[chunk.start_char:chunk.end_char] == chunk.text

def test_semantic_chunker_relevance_selection():
    text = (
        "Header information and standard hospital notice.\n\n"
        "Patient Name: John Smith, DOB: 1980-01-01.\n\n"
        "Legal disclaimer and privacy footer without any PII."
    )
    chunker = SemanticChunker(max_chunk_chars=80, overlap_chars=10)
    chunks = chunker.chunk_document(text)
    
    # Candidate pointing to John Smith
    patient_pos = text.index("John Smith")
    candidates = [{"start": patient_pos, "end": patient_pos + 10, "text": "John Smith"}]
    
    selected = chunker.select_relevant_chunks(chunks, candidates=candidates)
    assert len(selected) >= 1
    assert any("John Smith" in c.text for c in selected)

def test_semantic_chunker_text_normalization():
    raw_ocr_text = "Patient\ufeff Name:\r\n\r\n\r\n\r\n‘John\u200b Doe’ \u2014 DOB: 1980-01-01  \n\n\n\nNotes: Normal  "
    normalized = SemanticChunker.normalize_text(raw_ocr_text)
    assert "\ufeff" not in normalized
    assert "\u200b" not in normalized
    assert "\r" not in normalized
    assert "‘" not in normalized
    assert "’" not in normalized
    assert "—" not in normalized
    assert "\n\n\n" not in normalized
    assert "John Doe" in normalized
