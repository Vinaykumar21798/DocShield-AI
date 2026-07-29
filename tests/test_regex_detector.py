from modules.detection.detectors.regex_detector import RegexDetector

text = """
Email: john@gmail.com
Phone: +91 9876543210
PAN: ABCDE1234F
Aadhaar: 1234 5678 9012
Passport: M1234567
Credit Card: 4111 1111 1111 1111
"""

detector = RegexDetector()

results = detector.detect(text)

print("\n========== REGEX TEST ==========\n")

for entity in results:
    print(entity)

def test_regex_labeled_patient_provider_rejects_generic_values():
    text = """
Patient Name: Michael Robinson
Patient Name: Account Holder
Patient: Unknown
Provider: Rojas-Gutierrez
Provider: Dr. Jane Smith
Provider: Customer Service
Provider: Main Hospital
"""

    results = RegexDetector().detect(text)
    detected = {
        (entity.entity_type, entity.entity_value)
        for entity in results
    }

    assert ("PATIENT", "Michael Robinson") in detected
    assert ("PROVIDER", "Rojas-Gutierrez") in detected
    assert ("PROVIDER", "Dr. Jane Smith") in detected
    assert ("PATIENT", "Account Holder") not in detected
    assert ("PATIENT", "Unknown") not in detected
    assert ("PROVIDER", "Customer Service") not in detected
    assert ("PROVIDER", "Main Hospital") not in detected

def test_regex_labeled_military_address_wins_over_zip_code():
    text = "- Address: USCGC Miller, FPO AE 99567"

    results = RegexDetector().detect(text)
    detected_types = [entity.entity_type for entity in results]

    assert detected_types == ["ADDRESS"]
    assert results[0].entity_value == "USCGC Miller, FPO AE 99567"
    assert results[0].confidence_score == 1.0


def test_regex_mixed_document_structured_fields_and_legal_party_spans():
    text = """Customer Name     : Michael Robinson
Phone             : +1-202-555-0148
Employee ID       : EMP-10452
Passport No       : M12345678
Driving License   : KA01 20240012345
Organization       : ABC Technologies Pvt Ltd
GSTIN              : 29ABCDE1234F1Z5
Bank Account       : 1234567890123456
Invoice Number     : INV-2026-1045
Visit Date         : 27-Jul-2026
This agreement is signed between ABC Technologies Pvt Ltd
and Michael Robinson.
Address:
221B Baker Street
London
NW1 6XE
"""

    results = RegexDetector().detect(text)
    detected = {(entity.entity_type, entity.entity_value) for entity in results}

    assert ("PERSON", "Michael Robinson") in detected
    assert ("US_PHONE_NUMBER", "+1-202-555-0148") in detected
    assert ("EMPLOYEE_ID", "EMP-10452") in detected
    assert ("PASSPORT_NUMBER", "M12345678") in detected
    assert ("DRIVING_LICENSE", "KA01 20240012345") in detected
    assert ("ORGANIZATION", "ABC Technologies Pvt Ltd") in detected
    assert ("GSTIN", "29ABCDE1234F1Z5") in detected
    assert ("BANK_ACCOUNT", "1234567890123456") in detected
    assert ("INVOICE_NUMBER", "INV-2026-1045") in detected
    assert ("VISIT_DATE", "27-Jul-2026") in detected
    assert ("ADDRESS", "221B Baker Street\nLondon\nNW1 6XE") in detected
    assert not any(entity.entity_type == "CREDIT_CARD" for entity in results)
    assert len([
        entity for entity in results
        if entity.entity_type == "ORGANIZATION"
        and entity.entity_value == "ABC Technologies Pvt Ltd"
    ]) == 2
    assert len([
        entity for entity in results
        if entity.entity_type == "PERSON"
        and entity.entity_value == "Michael Robinson"
    ]) == 2
