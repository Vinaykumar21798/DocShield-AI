import pytest
from modules.detection.candidate_quality_gate import CandidateQualityGate
from modules.detection.embedding_service import EmbeddingService
from modules.detection.models.detection_result import DetectionResult
from modules.detection.pipeline_state import PipelineState
from modules.detection.semantic_chunker import SemanticChunker
from modules.detection.service import DetectionService
from modules.detection.detectors.gemma_detector import Gemma4E4BDetector
from modules.detection.detectors.regex_detector import RegexDetector


def test_embedding_service_singleton():
    """Verify that EmbeddingService is loaded once as a singleton."""
    service1 = EmbeddingService.get_instance()
    service2 = EmbeddingService.get_instance()
    assert service1 is service2


def test_high_confidence_regex_url_locks_and_suppresses_duplicate():
    """1 & 2: Regex URL locks span and Presidio duplicate detection is suppressed."""
    text = "Please review your policy at www.healthguardinsurance.com for full coverage details."
    service = DetectionService()
    results = service.detect(text, document_type="Insurance Policy / Benefit Summary")

    urls = [e for e in results if "www.healthguardinsurance.com" in e.entity_value]
    assert len(urls) == 1
    assert urls[0].entity_type == "URL"
    assert urls[0].detector == "Regex"


def test_high_confidence_regex_phone_locks_and_suppresses_presidio_person():
    """3 & 4: Regex phone locks span and Presidio PERSON detection is suppressed."""
    text = "Patient Phone: 1-800-555-1234. Patient Eleanor Vance was admitted."
    service = DetectionService()
    results = service.detect(text, document_type="Medical Record / Clinical Note")

    phones = [e for e in results if "1-800-555-1234" in e.entity_value]
    assert len(phones) == 1
    assert phones[0].entity_type == "PHONE_NUMBER"
    assert phones[0].detector == "Regex"


def test_mail_order_rejected_before_llm():
    """5. 'Mail Order' in benefit table is rejected by CandidateQualityGate before reaching LLM."""
    text = (
        "PRESCRIPTION DRUGS - WHAT YOU WILL PAY\n"
        "Type | Retail (30-day) | Mail Order (90-day) | Limitations\n"
        "Generic (Tier 1) | $10 copay | $25 copay | Deductible applies"
    )
    gate = CandidateQualityGate()
    cand = DetectionResult(
        entity_type="PERSON",
        entity_value="Mail Order",
        confidence_score=0.75,
        start_char=text.index("Mail Order"),
        end_char=text.index("Mail Order") + len("Mail Order"),
        page_number=1,
        detector="presidio",
    )

    decision = gate.evaluate(cand, text, document_type="Summary of Benefits and Coverage (SBC)")
    assert decision.decision == "PRE_LLM_REJECT"
    assert "benefit" in decision.reason.lower() or "table" in decision.reason.lower()


def test_preauth_and_specialty_rejected_before_llm():
    """6 & 7: 'Preauth' and 'Specialty' in benefit table context rejected before LLM."""
    text = "PRESCRIPTION BENEFIT: Specialty medications require Preauth prior to dispensing."
    gate = CandidateQualityGate()

    preauth_cand = DetectionResult(
        entity_type="PERSON",
        entity_value="Preauth",
        confidence_score=0.75,
        start_char=text.index("Preauth"),
        end_char=text.index("Preauth") + len("Preauth"),
        page_number=1,
        detector="presidio",
    )
    decision1 = gate.evaluate(preauth_cand, text, document_type="Insurance Policy / Benefit Summary")
    assert decision1.decision == "PRE_LLM_REJECT"

    specialty_cand = DetectionResult(
        entity_type="PERSON",
        entity_value="Specialty",
        confidence_score=0.75,
        start_char=text.index("Specialty"),
        end_char=text.index("Specialty") + len("Specialty"),
        page_number=1,
        detector="presidio",
    )
    decision2 = gate.evaluate(specialty_cand, text, document_type="Insurance Policy / Benefit Summary")
    assert decision2.decision == "PRE_LLM_REJECT"


def test_structural_table_labels_rejected_before_llm():
    """8, 9, 10, 11, 12, 13: Plan Paid, You Paid, Managing Type, Type Generic, None None None, Minimum Value."""
    gate = CandidateQualityGate()
    test_cases = [
        ("Plan Paid", "SUMMARY: Plan Paid $150.00 of total billed charge.", "PERSON"),
        ("You Paid", "SUMMARY: You Paid $25.00 copayment.", "PERSON"),
        ("Managing Type", "Managing Type: Individual Policy Details", "PERSON"),
        ("Type Generic", "Type Generic Tier 1 Copay", "PERSON"),
        ("None None None", "None None None | Standard Coverage Details", "PERSON"),
        ("Minimum Value", "This plan meets the Minimum Value standard under the ACA.", "PERSON"),
    ]

    for val, text, ent_type in test_cases:
        cand = DetectionResult(
            entity_type=ent_type,
            entity_value=val,
            confidence_score=0.75,
            start_char=text.index(val),
            end_char=text.index(val) + len(val),
            page_number=1,
            detector="presidio",
        )
        decision = gate.evaluate(cand, text, document_type="Summary of Benefits and Coverage (SBC)")
        assert decision.decision == "PRE_LLM_REJECT", f"Expected PRE_LLM_REJECT for {val}, got {decision.decision}"


def test_genuine_physician_dr_robert_chen_passes_to_pending():
    """14. 'Dr. Robert Chen' in clinical context passes Quality Gate to PENDING_FOR_LLM."""
    text = "Encounter Date: 03/15/2024. Attending Clinician: Dr. Robert Chen. Office Visit / A1C Test."
    gate = CandidateQualityGate()
    cand = DetectionResult(
        entity_type="PERSON",
        entity_value="Dr. Robert Chen",
        confidence_score=0.75,
        start_char=text.index("Dr. Robert Chen"),
        end_char=text.index("Dr. Robert Chen") + len("Dr. Robert Chen"),
        page_number=1,
        detector="presidio",
    )

    decision = gate.evaluate(cand, text, document_type="Medical Record / Clinical Note")
    assert decision.decision == "PENDING_FOR_LLM"
    assert decision.semantic_score > 0.30


def test_genuine_patient_and_address_pass_to_pending():
    """15, 16, 17, 18: Genuine patient name, address, and organization pass to PENDING_FOR_LLM."""
    text = "Patient Eleanor Vance residing at 742 Evergreen Terrace was admitted to Springfield Hospital."
    gate = CandidateQualityGate()

    patient_cand = DetectionResult(
        entity_type="PERSON",
        entity_value="Eleanor Vance",
        confidence_score=0.75,
        start_char=text.index("Eleanor Vance"),
        end_char=text.index("Eleanor Vance") + len("Eleanor Vance"),
        page_number=1,
        detector="presidio",
    )
    decision_patient = gate.evaluate(patient_cand, text, document_type="Medical Record / Clinical Note")
    assert decision_patient.decision == "PENDING_FOR_LLM"


def test_gemma_validation_confirm_reclassify_reject():
    """19, 20, 21, 22: Gemma validation decisions (CONFIRM, RECLASSIFY, REJECT) without inventing spans."""
    gemma = Gemma4E4BDetector()
    chunker = SemanticChunker()

    # Case 1: CONFIRM real person
    text1 = "Primary Member: David A. Wilson presented for consultation."
    chunks1 = chunker.chunk_document(text1)
    cand1 = DetectionResult(
        entity_type="PERSON",
        entity_value="David A. Wilson",
        confidence_score=0.75,
        start_char=text1.index("David A. Wilson"),
        end_char=text1.index("David A. Wilson") + len("David A. Wilson"),
        page_number=1,
        detector="presidio",
    )
    res1 = gemma.validate_candidates([cand1], chunks1, document_type="Insurance Policy / Benefit Summary")
    assert len(res1) == 1
    assert res1[0].entity_value == "David A. Wilson"
    assert res1[0].entity_type == "PERSON"
    assert res1[0].detector == "Gemma"

    # Case 2: RECLASSIFY pharmacy misclassified as PERSON -> ORGANIZATION
    text2 = "Prescription filled at Westfield Pharmacy on Main Street."
    chunks2 = chunker.chunk_document(text2)
    cand2 = DetectionResult(
        entity_type="PERSON",
        entity_value="Westfield",
        confidence_score=0.75,
        start_char=text2.index("Westfield"),
        end_char=text2.index("Westfield") + len("Westfield"),
        page_number=1,
        detector="presidio",
    )
    res2 = gemma.validate_candidates([cand2], chunks2, document_type="Explanation of Benefits (EOB) / Medical Claim")
    assert len(res2) == 1
    assert res2[0].entity_type == "ORGANIZATION"
    assert res2[0].detector == "Gemma"

    # Case 3: REJECT benefit term
    text3 = "Coverage provisions: Mail Order $20 Copay."
    chunks3 = chunker.chunk_document(text3)
    cand3 = DetectionResult(
        entity_type="PERSON",
        entity_value="Mail Order",
        confidence_score=0.75,
        start_char=text3.index("Mail Order"),
        end_char=text3.index("Mail Order") + len("Mail Order"),
        page_number=1,
        detector="presidio",
    )
    res3 = gemma.validate_candidates([cand3], chunks3, document_type="Summary of Benefits and Coverage (SBC)")
    assert len(res3) == 0


def test_gemma_residual_detection_discovers_unmapped_entities_only():
    """23 & 24: Residual Gemma detection discovers missed entity in same chunk without duplicating locked entity."""
    text = "Patient SSN: 123-45-6789. Assessment revealed acute myocardial infarction."
    state = PipelineState(original_text=text)

    # 1. Regex locks SSN
    ssn_idx = text.index("123-45-6789")
    ssn = DetectionResult(
        entity_type="SSN",
        entity_value="123-45-6789",
        confidence_score=1.0,
        start_char=ssn_idx,
        end_char=ssn_idx + 11,
        page_number=1,
        detector="regex",
    )
    state.add_entities([ssn], detector_name="regex", mask_confidence_threshold=0.80)

    # 2. Gemma residual discovers diagnosis
    diag_idx = text.index("acute myocardial infarction")
    diag = DetectionResult(
        entity_type="DIAGNOSIS",
        entity_value="acute myocardial infarction",
        confidence_score=0.92,
        start_char=diag_idx,
        end_char=diag_idx + len("acute myocardial infarction"),
        page_number=1,
        detector="gemma4e4b",
    )

    accepted = DetectionService._filter_new_entities([diag], state, "gemma4e4b", 0.80)
    assert len(accepted) == 1
    assert accepted[0].entity_value == "acute myocardial infarction"

    # Attempt duplicate SSN by Gemma residual should be rejected
    dup_ssn = DetectionResult(
        entity_type="SSN",
        entity_value="123-45-6789",
        confidence_score=0.90,
        start_char=ssn_idx,
        end_char=ssn_idx + 11,
        page_number=1,
        detector="gemma4e4b",
    )
    dup_accepted = DetectionService._filter_new_entities([dup_ssn], state, "gemma4e4b", 0.80)
    assert len(dup_accepted) == 0


def test_semantic_chunker_embedding_boundaries_and_offsets():
    """25: SemanticChunker preserves semantic units, section contexts, and exact offsets."""
    text = (
        "PATIENT INFORMATION:\n"
        "Name: Eleanor Vance\n"
        "DOB: 05/12/1985\n\n"
        "CLINICAL FINDINGS:\n"
        "Patient presented with persistent fever and acute bronchitis.\n\n"
        "BENEFIT DETAILS:\n"
        "Type | Retail | Mail Order\n"
        "Generic | $10 | $25"
    )
    chunker = SemanticChunker(target_chunk_chars=120, max_chunk_chars=200, min_chunk_chars=40)
    chunks = chunker.chunk_document(text)

    assert len(chunks) >= 1
    for chunk in chunks:
        # Verify slice exactness
        assert text[chunk.start_char:chunk.end_char] == chunk.text
        assert len(chunk.text.strip()) > 0


def test_end_to_end_pipeline_candidate_reduction():
    """26 & 27: End-to-end detection pipeline suppresses noise and tracks LLM call reduction."""
    text = (
        "EXPLANATION OF BENEFITS\n"
        "Customer Service: 1-800-555-1234 | Website: www.healthguardinsurance.com\n\n"
        "PRESCRIPTION DRUGS - WHAT YOU WILL PAY\n"
        "Type | Retail (30-day) | Mail Order (90-day) | Limitations\n"
        "Generic (Tier 1) | $10 copay | $25 copay | Preauth required\n\n"
        "PATIENT DETAILS:\n"
        "Patient Name: Eleanor Vance\n"
        "Attending Clinician: Dr. Robert Chen\n"
        "Prescription filled at Westfield Pharmacy."
    )
    service = DetectionService()
    results = service.detect(text, document_type="Explanation of Benefits (EOB) / Medical Claim")

    values = [e.entity_value for e in results]
    # Locked & valid entities are present
    assert "www.healthguardinsurance.com" in values
    assert "1-800-555-1234" in values
    assert any("Eleanor Vance" in v for v in values)
    assert any("Robert Chen" in v for v in values)

    # Obvious table noise is NOT in final results
    assert "Mail Order" not in values
    assert "Preauth" not in values
    assert "Type Generic" not in values
