import pytest
from modules.detection.detectors.regex_detector import RegexDetector
from modules.detection.detectors.presidio_detector import PresidioDetector
from modules.detection.service import DetectionService
from modules.detection.deduplicator import Deduplicator
from modules.detection.models.detection_result import DetectionResult
from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.pipeline_state import PipelineState

def test_npi_luhn_validator():
    # Valid NPI (10-digit, Luhn compliant)
    assert BaseDetector.is_valid_npi("1592847603") is True
    # Invalid NPI
    assert BaseDetector.is_valid_npi("1592847604") is False
    assert BaseDetector.is_valid_npi("12345") is False

def test_regex_eob_classifications():
    detector = RegexDetector()

    # 1. "Box 45678" -> ADDRESS (PO Box) instead of INSURANCE_ID
    res1 = detector.detect("Address: Box 45678")
    types1 = {r.entity_type for r in res1}
    assert "ADDRESS" in types1 or "PO_BOX" in types1
    assert "INSURANCE_ID" not in types1

    # 2. Provider NPI (1592847603) -> NPI_NUMBER instead of PHONE
    res2 = detector.detect("Provider NPI: 1592847603")
    types2 = {r.entity_type for r in res2}
    assert "NPI_NUMBER" in types2
    assert "US_PHONE_NUMBER" not in types2
    assert "PHONE_NUMBER" not in types2

    # 3. 80053 -> CPT_CODE / LAB_CODE instead of DATE_TIME
    res3 = detector.detect("CPT: 80053")
    types3 = {r.entity_type for r in res3}
    assert "CPT_CODE" in types3

    # 4. 83036 -> LAB_CODE / CPT_CODE instead of DATE_TIME
    res4 = detector.detect("CPT: 83036")
    types4 = {r.entity_type for r in res4}
    assert "CPT_CODE" in types4

def test_presidio_eob_filters():
    detector = PresidioDetector()
    
    # "Annual" and "Plan Year" should be ignored (not matched as DATE_TIME)
    res1 = detector.detect("Annual Plan Year review date")
    types1 = {r.entity_type for r in res1}
    assert "DATE_TIME" not in types1

    # "Hyperlipidemia" should be classified as DISEASE instead of PERSON
    res2 = detector.detect("The patient has Hyperlipidemia")
    types2 = {r.entity_type for r in res2}
    assert "PERSON" not in types2

def test_longest_span_overlap_resolution():
    # If David A, Wilson, and David A. Wilson overlap, keep David A. Wilson
    detections = [
        DetectionResult(
            entity_type="PERSON",
            entity_value="David A",
            confidence_score=0.8,
            start_char=0,
            end_char=7,
            page_number=1,
            detector="gliner"
        ),
        DetectionResult(
            entity_type="PERSON",
            entity_value="Wilson",
            confidence_score=0.8,
            start_char=10,
            end_char=16,
            page_number=1,
            detector="gliner"
        ),
        DetectionResult(
            entity_type="PATIENT",
            entity_value="David A. Wilson",
            confidence_score=0.9,
            start_char=0,
            end_char=16,
            page_number=1,
            detector="regex"
        )
    ]
    resolved = Deduplicator.deduplicate(detections)
    assert len(resolved) == 1
    assert resolved[0].entity_value == "David A. Wilson"
    assert resolved[0].entity_type == "PATIENT"

def test_medication_dosage_association():
    service = DetectionService()
    # Mocking text containing Medication and close Dosage
    text = "Patient was prescribed Metformin 1000mg once daily."
    results = service.detect(text)
    
    medications = [r for r in results if r.entity_type == "MEDICATION"]
    dosages = [r for r in results if r.entity_type == "DOSAGE"]
    
    # Metformin should be detected
    assert len(medications) > 0
    # Dosage 1000mg should be detected and associated
    assert len(dosages) > 0
    
    metformin_entity = medications[0]
    assert metformin_entity.metadata.get("associated_dosage") == "1000mg"


def test_pipeline_cascading_and_masking():
    # Setup text: "John Doe"
    text = "John Doe"
    state = PipelineState(text)
    
    # 1. First detector returns a low confidence detection
    entity1 = DetectionResult(
        entity_type="PERSON",
        entity_value="John Doe",
        confidence_score=0.42,
        start_char=0,
        end_char=8,
        page_number=1,
        detector="regex"
    )
    
    # Add it with mask threshold 0.85
    state.add_entities([entity1], detector_name="regex", mask_confidence_threshold=0.85)
    
    # Verify low-confidence detection is not masked
    assert state.is_span_unmasked(0, 8) is True
    assert len(state.resolved_entities) == 1
    assert state.resolved_entities[0].confidence_score == 0.42
    
    # 2. Duplicate detection with lower confidence
    entity_lower = DetectionResult(
        entity_type="PERSON",
        entity_value="John Doe",
        confidence_score=0.30,
        start_char=0,
        end_char=8,
        page_number=1,
        detector="presidio"
    )
    # Check duplicate matching using helper
    from modules.detection.service import DetectionService
    is_dup1 = DetectionService._matches_previous_entity(entity_lower, state, mask_confidence_threshold=0.85)
    assert is_dup1 is True
    # Ensure confidence score is still 0.42 (lower duplicate didn't overwrite)
    assert state.resolved_entities[0].confidence_score == 0.42
    assert state.resolved_entities[0].detector == "regex"
    assert len(state.resolved_entities) == 1
    
    # 3. Duplicate detection with higher confidence (above threshold)
    entity_higher = DetectionResult(
        entity_type="PERSON",
        entity_value="John Doe",
        confidence_score=0.97,
        start_char=0,
        end_char=8,
        page_number=1,
        detector="presidio"
    )
    is_dup2 = DetectionService._matches_previous_entity(entity_higher, state, mask_confidence_threshold=0.85)
    assert is_dup2 is True
    # Ensure it updated the confidence and detector, and triggered masking
    assert state.resolved_entities[0].confidence_score == 0.97
    assert state.resolved_entities[0].detector == "presidio"
    assert state.is_span_unmasked(0, 8) is False
    assert len(state.resolved_entities) == 1
    
    # 4. Adding a high confidence entity directly masks it
    state2 = PipelineState("Alice")
    entity_high = DetectionResult(
        entity_type="PERSON",
        entity_value="Alice",
        confidence_score=0.90,
        start_char=0,
        end_char=5,
        page_number=1,
        detector="regex"
    )
    state2.add_entities([entity_high], detector_name="regex", mask_confidence_threshold=0.85)
    assert state2.is_span_unmasked(0, 5) is False
