import pytest
from modules.detection.service import DetectionService
from modules.detection.detectors.presidio_detector import PresidioDetector
from modules.detection.detectors.medspacy_detector import MedSpaCyDetector
from modules.detection.detectors.regex_detector import RegexDetector


def test_multiline_address_merging():
    service = DetectionService()
    text = (
        "PATIENT RECORD\n"
        "Name: Eleanor Vance\n"
        "ADDRESS: 542 Willow Lane\n"
        "CITY, STATE ZIP: Farmington Hills, MI 48334\n"
        "Phone: (248) 555-0199"
    )
    results = service.detect(text, document_type="Medical Record / Clinical Note")
    address_entities = [e for e in results if e.entity_type == "ADDRESS"]
    assert len(address_entities) >= 1
    # Full address must contain both the street and the city/state/zip
    full_address = address_entities[0].entity_value
    assert "542 Willow Lane" in full_address
    assert "Farmington Hills, MI 48334" in full_address


def test_contextual_phone_and_date_reclassification():
    service = DetectionService()
    text = (
        "EXPLANATION OF BENEFITS\n"
        "EOB Date: 05/14/2024\n"
        "Date(s) of Service: 04/17/2024 - 04/17/2024\n"
        "Customer Service Phone: (800) 555-9000\n"
        "Patient Phone: (248) 555-0199\n"
        "Total Billed: $1,250.00\n"
        "Copay: $25.00"
    )
    results = service.detect(text, document_type="Explanation of Benefits (EOB) / Medical Claim")
    
    # EOB Date reclassified
    eob_dates = [e for e in results if "05/14/2024" in e.entity_value]
    assert len(eob_dates) >= 1
    assert eob_dates[0].entity_type == "DOCUMENT_CREATION_DATE"

    # Customer service phone reclassified
    cs_phones = [e for e in results if "(800) 555-9000" in e.entity_value]
    assert len(cs_phones) >= 1
    assert cs_phones[0].entity_type == "ORGANIZATION_CONTACT_INFO"

    # Patient phone remains personal phone
    patient_phones = [e for e in results if "(248) 555-0199" in e.entity_value]
    assert len(patient_phones) >= 1
    assert patient_phones[0].entity_type == "PHONE_NUMBER"

    # Financial amounts detected
    amounts = [e for e in results if e.entity_type == "FINANCIAL_AMOUNT"]
    assert len(amounts) >= 1


def test_presidio_medication_not_classified_as_person():
    detector = PresidioDetector()
    text = "Prescribed Lisinopril 10 mg daily and Atorvastatin 20 mg for hyperlipidemia."
    results = detector.detect(text)
    person_entities = [e for e in results if e.entity_type == "PERSON"]
    # Neither Lisinopril nor Atorvastatin should be tagged as PERSON
    for p in person_entities:
        assert "lisinopril" not in p.entity_value.lower()
        assert "atorvastatin" not in p.entity_value.lower()


def test_medspacy_clean_lab_detection():
    detector = MedSpaCyDetector()
    text = "Hemoglobin A1c: 7.2%, Blood Glucose: 134 mg/dL."
    results = detector.detect(text)
    # Ensure no entity has the noisy string "a1c results"
    for e in results:
        assert e.entity_value.lower() != "a1c results"
