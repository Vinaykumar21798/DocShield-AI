import pytest
from modules.detection.pipeline_state import PipelineState

def test_structured_label_value_separation():
    # 1. Structured text with colons
    text = (
        "Patient Name: Michael Jordan\n"
        "DOB: 1967-04-15\n"
        "Diagnosis: Hypertension\n"
        "Medication: NovoRapid\n"
        "Provider: Apollo Hospital\n"
        "Primary Physician: Dr. Brown\n"
        "Amount Billed: $2845.00\n"
    )
    state = PipelineState(original_text=text)
    summary = state.remaining_candidate_summary()
    preview = summary["preview"]

    # Verify that labels are NOT in candidates
    assert "Patient Name" not in preview
    assert "DOB" not in preview
    assert "Diagnosis" not in preview
    assert "Medication" not in preview
    assert "Provider" not in preview
    assert "Primary Physician" not in preview
    assert "Amount Billed" not in preview

    # Verify that values ARE generated as candidates
    all_texts = [c["text"] for c in summary["candidates"]]
    assert "Michael Jordan" in all_texts
    assert "Hypertension" in all_texts
    assert "NovoRapid" in all_texts
    assert "Dr. Brown" in all_texts

def test_unstructured_text_proper_nouns():
    # 2. Unstructured plain text - proper nouns must remain valid
    text = (
        "Michael Jordan visited Apollo Hospital yesterday.\n"
        "Dr. Brown diagnosed Stage II hypertension.\n"
        "Revision surgery was recommended.\n"
        "United approved the insurance claim.\n"
    )
    state = PipelineState(original_text=text)
    summary = state.remaining_candidate_summary()
    all_texts = [c["text"] for c in summary["candidates"]]

    # Verify valid proper nouns and signal words are extracted
    assert "Michael Jordan" in all_texts
    assert "Dr. Brown" in all_texts
    assert "hypertension" in all_texts  # Matches domain signal word

def test_mixed_text_headers_ignored():
    # 3. Mixed text with standalone section headers
    text = (
        "Patient Name: Michael Jordan\n"
        "Clinical Notes\n"
        "Michael Jordan visited Apollo Hospital.\n"
        "Dr. Brown reviewed the MRI.\n"
        "Explanation of Benefits\n"
    )
    state = PipelineState(original_text=text)
    summary = state.remaining_candidate_summary()
    all_texts = [c["text"] for c in summary["candidates"]]

    # Verify headers are ignored
    assert "Clinical Notes" not in all_texts
    assert "Explanation of Benefits" not in all_texts
    assert "Patient Name" not in all_texts

    # Verify real proper nouns are extracted
    assert "Michael Jordan" in all_texts
    assert "Dr. Brown" in all_texts
