import pytest
from modules.detection.pipeline_state import PipelineState
from modules.detection.semantic_chunker import SemanticChunker
from modules.detection.models.detection_result import DetectionResult
from modules.detection.service import DetectionService
from modules.detection.detectors.qwen_detector import Qwen3BDetector
from modules.detection.detectors.regex_detector import RegexDetector
from modules.detection.detectors.presidio_detector import PresidioDetector


def test_high_confidence_regex_url_suppresses_presidio():
    """
    1. High-confidence Regex URL suppresses duplicate Presidio detection.
    """
    text = "Please visit www.healthguardinsurance.com for policy details."
    service = DetectionService()
    results = service.detect(text, document_type="Insurance Policy / Benefit Summary")

    urls = [e for e in results if "www.healthguardinsurance.com" in e.entity_value]
    assert len(urls) == 1
    assert urls[0].entity_type == "URL"
    assert urls[0].detector == "Regex"


def test_high_confidence_regex_phone_suppresses_presidio_person():
    """
    2. High-confidence Regex phone suppresses duplicate Presidio PERSON detection.
    """
    text = "Patient Phone: 1-800-555-1234."
    service = DetectionService()
    results = service.detect(text, document_type="Medical Record / Clinical Note")

    phones = [e for e in results if "1-800-555-1234" in e.entity_value]
    assert len(phones) == 1
    assert phones[0].entity_type == "PHONE_NUMBER"
    assert phones[0].detector == "Regex"


def test_low_confidence_mail_order_rejected():
    """
    3. Low-confidence 'Mail Order' in benefit context is rejected by contextual validation.
    """
    text = "PRESCRIPTION DRUG BENEFITS:\nMail Order: $20 Copay for 90-day supply."
    qwen = Qwen3BDetector()
    chunker = SemanticChunker()
    chunks = chunker.chunk_document(text)

    mail_order_cand = DetectionResult(
        entity_type="PERSON",
        entity_value="Mail Order",
        confidence_score=0.75,
        start_char=text.index("Mail Order"),
        end_char=text.index("Mail Order") + len("Mail Order"),
        page_number=1,
        detector="presidio",
    )

    validated = qwen.validate_candidates([mail_order_cand], chunks, document_type="Summary of Benefits and Coverage (SBC)")
    # 'Mail Order' must be REJECTED (empty validated results)
    assert len(validated) == 0


def test_low_confidence_preauth_rejected():
    """
    4. Low-confidence 'Preauth' is rejected by contextual validation.
    """
    text = "Specialty drugs require Preauth before dispensing."
    qwen = Qwen3BDetector()
    chunks = SemanticChunker().chunk_document(text)

    preauth_cand = DetectionResult(
        entity_type="PERSON",
        entity_value="Preauth",
        confidence_score=0.75,
        start_char=text.index("Preauth"),
        end_char=text.index("Preauth") + len("Preauth"),
        page_number=1,
        detector="presidio",
    )

    validated = qwen.validate_candidates([preauth_cand], chunks, document_type="Insurance Policy / Benefit Summary")
    assert len(validated) == 0


def test_low_confidence_minimum_value_rejected():
    """
    5. Low-confidence 'Minimum Value' is rejected.
    """
    text = "This coverage meets the Minimum Value standard under the Affordable Care Act."
    qwen = Qwen3BDetector()
    chunks = SemanticChunker().chunk_document(text)

    min_val_cand = DetectionResult(
        entity_type="PERSON",
        entity_value="Minimum Value",
        confidence_score=0.75,
        start_char=text.index("Minimum Value"),
        end_char=text.index("Minimum Value") + len("Minimum Value"),
        page_number=1,
        detector="presidio",
    )

    validated = qwen.validate_candidates([min_val_cand], chunks, document_type="Summary of Benefits and Coverage (SBC)")
    assert len(validated) == 0


def test_low_confidence_hearing_rejected():
    """
    6. Low-confidence 'Hearing' in 'Hearing aids' context is rejected.
    """
    text = "Coverage excludes Hearing aids and routine vision care."
    qwen = Qwen3BDetector()
    chunks = SemanticChunker().chunk_document(text)

    hearing_cand = DetectionResult(
        entity_type="LOCATION",
        entity_value="Hearing",
        confidence_score=0.75,
        start_char=text.index("Hearing"),
        end_char=text.index("Hearing") + len("Hearing"),
        page_number=1,
        detector="presidio",
    )

    validated = qwen.validate_candidates([hearing_cand], chunks, document_type="Insurance Policy / Benefit Summary")
    assert len(validated) == 0


def test_westfield_contextually_reclassified():
    """
    7. 'Westfield' in pharmacy context is contextually reclassified to ORGANIZATION.
    """
    text = "Prescription dispensed at Westfield Pharmacy on Main Street."
    qwen = Qwen3BDetector()
    chunks = SemanticChunker().chunk_document(text)

    westfield_cand = DetectionResult(
        entity_type="PERSON",
        entity_value="Westfield",
        confidence_score=0.75,
        start_char=text.index("Westfield"),
        end_char=text.index("Westfield") + len("Westfield"),
        page_number=1,
        detector="presidio",
    )

    validated = qwen.validate_candidates([westfield_cand], chunks, document_type="Explanation of Benefits (EOB) / Medical Claim")
    assert len(validated) == 1
    assert validated[0].entity_type == "ORGANIZATION"
    assert validated[0].confidence_score >= 0.85


def test_valid_low_confidence_person_confirmed():
    """
    8. A valid low-confidence person in real person context is CONFIRMED.
    """
    text = "Patient Eleanor Vance presented with symptoms of acute asthma."
    qwen = Qwen3BDetector()
    chunks = SemanticChunker().chunk_document(text)

    person_cand = DetectionResult(
        entity_type="PERSON",
        entity_value="Eleanor Vance",
        confidence_score=0.75,
        start_char=text.index("Eleanor Vance"),
        end_char=text.index("Eleanor Vance") + len("Eleanor Vance"),
        page_number=1,
        detector="presidio",
    )

    validated = qwen.validate_candidates([person_cand], chunks, document_type="Medical Record / Clinical Note")
    assert len(validated) == 1
    assert validated[0].entity_type == "PERSON"
    assert validated[0].confidence_score >= 0.85


def test_qwen_residual_discovery_in_same_chunk():
    """
    9. Qwen can discover missed MUST_HAVE entity in the same semantic chunk.
    """
    text = "Patient SSN: 123-45-6789. Clinical diagnosis: malignant hypertension."
    state = PipelineState(original_text=text)

    # Fast detector locks SSN
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

    # Qwen discovers missed diagnosis
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

    assert len(accepted) == 1
    assert accepted[0].entity_value == "malignant hypertension"


def test_locked_high_confidence_entities_never_duplicated():
    """
    10. Locked high-confidence entities are never duplicated by downstream detectors or Qwen.
    """
    text = "Patient SSN: 123-45-6789."
    state = PipelineState(original_text=text)

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

    # Attempt duplicate by Presidio
    presidio_dup = DetectionResult(
        entity_type="SSN",
        entity_value="123-45-6789",
        confidence_score=0.85,
        start_char=ssn_idx,
        end_char=ssn_idx + 11,
        page_number=1,
        detector="presidio",
    )

    accepted = DetectionService._filter_new_entities(
        [presidio_dup],
        state=state,
        detector_name="presidio",
        mask_confidence_threshold=0.80,
    )

    assert len(accepted) == 0
    assert len(state.resolved_entities) == 1
    assert state.resolved_entities[0].detector == "regex"
