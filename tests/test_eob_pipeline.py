import pytest
from modules.detection.detectors.regex_detector import RegexDetector
from modules.detection.detectors.presidio_detector import PresidioDetector
from modules.detection.service import DetectionService
from modules.detection.deduplicator import Deduplicator
from modules.detection.models.detection_result import DetectionResult
from modules.detection.detectors.base_detector import BaseDetector

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
