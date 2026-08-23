import json
from types import SimpleNamespace

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.detectors.medspacy_detector import MedSpaCyDetector
from modules.detection.detectors.gemma_detector import Gemma4E4BDetector
from modules.detection.detectors.azure_detector import AzureOpenAIDetector
from modules.detection.detectors.regex_detector import RegexDetector
from modules.detection.models.detection_result import DetectionResult
from modules.detection.pipeline_state import PipelineState
from modules.detection.service import DetectionService
from modules.detection.validators.entity_validator import EntityValidator
from orchestration.workflow import DocumentProcessingWorkflow




MEDICAL_RECORD_SAMPLE = """SUNRISE FAMILY MEDICINE
Date Generated: May 14, 2025
PATIENT INFORMATION:
â€¢ Name: Sophia Garcia
â€¢ Date of Birth: 11/04/1992
Provider: Dr. James Wilson Location:
Sunrise Family Medicine, Suite 302 Address: 875 Wellness Boulevard, Farmington Hills, MI 48334
Continue Dicyclomine 10mg as needed.
You reported abdominal pain and loose stools.
LABORATORY RESULTS:
â€¢ Complete Blood Count (CBC)
Comprehensive Metabolic Panel (CMP)
Celiac Disease Antibody Panel
Calprotectin Test
Phone: (248) 555-7890
This communication contains Protected Health Information and mentions FSA and HIPAA.
Please notify us at (248) 555-
7890."""


BREACH_LETTER_SAMPLE = """EVERGREEN HEALTHCARE SYSTEM
DATE: May 14, 2025
SENT VIA: Certified Mail #7389 5421 0089 6542
PATIENT NAME: Michael J. Roberts
ADDRESS: 542 Willow Lane
On April 18, 2025, an employee email account was accessed between April 10-15, 2025.
â€¢ Full name and date of birth (08/23/1962)
â€¢ Medical Record Number: EHS-78245912
â€¢ Health insurance information: Medicare #8752A69JK21
â€¢ Implemented additional security measures
â€¢ Secured all affected systems
Enroll in the monitoring service using code: EHS-2025-04-BR
Contact (800) 555-9876 or breach_response@evergreenhealthcare.org.
Sarah Johnson, CISO
the Health Insurance Portability and Accountability Act (HIPAA)"""




def _result(text, value, entity_type, confidence=0.95, detector="gemma4e4b"):
    start = text.index(value)
    return DetectionResult(
        entity_type=entity_type,
        entity_value=value,
        confidence_score=confidence,
        start_char=start,
        end_char=start + len(value),
        page_number=1,
        detector=detector,
    )


def test_regex_rejects_identifier_labels_and_keeps_real_identifiers():
    text = """Claim Received
Claim Processed
Claim MESSAGES
Group Name
Member ID number
Claim Number: CLM24042587196
Member ID: MBR123456
Group Number: GRP9876
EOB Number: EOB24042587"""

    detected = {
        (entity.entity_type, entity.entity_value)
        for entity in RegexDetector().detect(text)
    }

    assert ("CLAIM_NUMBER", "Received") not in detected
    assert ("CLAIM_NUMBER", "Processed") not in detected
    assert ("CLAIM_NUMBER", "MESSAGES") not in detected
    assert ("GROUP_NUMBER", "Name") not in detected
    assert ("MEMBER_ID", "number") not in detected
    assert ("CLAIM_NUMBER", "CLM24042587196") in detected
    assert ("MEMBER_ID", "MBR123456") in detected
    assert ("GROUP_NUMBER", "GRP9876") in detected
    assert ("EOB_NUMBER", "EOB24042587") in detected


def test_regex_captures_patient_name_with_initial_as_one_span():
    results = RegexDetector().detect("Patient Name: David A. Wilson")

    patients = [entity for entity in results if entity.entity_type == "PATIENT"]
    assert len(patients) == 1
    assert patients[0].entity_value == "David A. Wilson"


def test_regex_captures_phone_split_across_ocr_lines():
    text = "Please notify us at (248) 555-\n7890."

    phones = [
        entity
        for entity in RegexDetector().detect(text)
        if entity.entity_type == "US_PHONE_NUMBER"
    ]

    assert len(phones) == 1
    assert phones[0].entity_value == "(248) 555-\n7890"
    assert text[phones[0].start_char:phones[0].end_char] == phones[0].entity_value
    assert phones[0].confidence_score == 1.0


def test_medspacy_rules_cover_medical_record_symptoms_and_labs():
    detector = MedSpaCyDetector()
    results = detector._detect_with_fallback_rules(MEDICAL_RECORD_SAMPLE, 1)
    detected = {(entity.entity_type, entity.entity_value.lower()) for entity in results}

    assert ("SYMPTOM", "abdominal pain") in detected
    assert ("SYMPTOM", "loose stools") in detected
    assert ("LAB", "complete blood count") in detected
    assert ("LAB", "comprehensive metabolic panel (cmp)") in detected
    assert ("LAB", "celiac disease antibody panel") in detected
    assert ("LAB", "calprotectin test") in detected


def test_validator_rejects_headings_and_reclassifies_known_labs():
    text = (
        "HIPAA FSA Complete NEEDED Protected Health Information Medical Record "
        "Comprehensive Metabolic Panel CMP Celiac Disease Antibody Panel"
    )
    candidates = [
        _result(text, "HIPAA", "ORGANIZATION", detector="presidio"),
        _result(text, "FSA", "ORGANIZATION", detector="presidio"),
        _result(text, "Complete", "PERSON", detector="presidio"),
        _result(text, "NEEDED", "LOCATION", detector="presidio"),
        _result(
            text,
            "Protected Health Information",
            "ORGANIZATION",
            detector="presidio",
        ),
        _result(text, "Medical Record", "ORGANIZATION", detector="presidio"),
        _result(
            text,
            "Comprehensive Metabolic Panel",
            "ORGANIZATION",
            detector="presidio",
        ),
        _result(text, "CMP", "ORGANIZATION", detector="presidio"),
        _result(
            text,
            "Celiac Disease Antibody Panel",
            "DISEASE",
            detector="presidio",
        ),
    ]

    results = EntityValidator.validate_candidates(candidates, text)
    detected = {(entity.entity_type, entity.entity_value) for entity in results}

    assert detected == {
        ("LAB", "Comprehensive Metabolic Panel"),
        ("LAB", "CMP"),
        ("LAB", "Celiac Disease Antibody Panel"),
    }


def test_medical_record_regression_is_clean_without_llm(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "true")
    monkeypatch.setenv("GLINER_ENABLED", "false")

    results = DetectionService().detect(
        MEDICAL_RECORD_SAMPLE,
        document_type="MEDICAL_RECORD",
    )
    detected = {(entity.entity_type, entity.entity_value) for entity in results}

    assert ("DATE_TIME", "May 14, 2025") in detected
    assert ("ADDRESS", "875 Wellness Boulevard, Farmington Hills, MI 48334") in detected
    assert ("DOSAGE", "10mg") in detected
    assert ("SYMPTOM", "abdominal pain") in detected
    assert ("SYMPTOM", "loose stools") in detected
    assert ("LAB", "Complete Blood Count") in detected
    assert ("LAB", "Comprehensive Metabolic Panel (CMP)") in detected
    assert ("LAB", "Celiac Disease Antibody Panel") in detected
    assert ("LAB", "Calprotectin Test") in detected

    phone_values = [
        entity.entity_value
        for entity in results
        if entity.entity_type == "US_PHONE_NUMBER"
    ]
    assert phone_values == ["(248) 555-7890", "(248) 555-\n7890"]

    dosage = next(entity for entity in results if entity.entity_type == "DOSAGE")
    assert dosage.privacy_category == "PHI"
    assert not {
        "HIPAA",
        "FSA",
        "Complete",
        "NEEDED",
        "Protected Health Information",
        "Medical Record",
    } & {entity.entity_value for entity in results}


def test_final_pii_safety_net_restores_a_missing_multiline_phone():
    text = "Please notify us at (248) 555-\n7890."

    results = DetectionService()._add_final_pii_safety_net(text, [], 1)

    assert len(results) == 1
    assert results[0].entity_type == "US_PHONE_NUMBER"
    assert results[0].entity_value == "(248) 555-\n7890"
    assert results[0].metadata["pii_safety_net"] is True


def test_breach_letter_identifiers_and_context_are_deterministic(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "true")
    monkeypatch.setenv("GLINER_ENABLED", "false")

    results = DetectionService().detect(
        BREACH_LETTER_SAMPLE,
        document_type="MEDICAL_RECORD",
    )
    detected = {(entity.entity_type, entity.entity_value) for entity in results}

    assert ("TRACKING_NUMBER", "7389 5421 0089 6542") in detected
    assert ("PATIENT", "Michael J. Roberts") in detected
    assert ("DATE_OF_BIRTH", "08/23/1962") in detected
    assert ("DATE_RANGE", "April 10-15, 2025") in detected
    assert ("ACCESS_CODE", "EHS-2025-04-BR") in detected
    assert not any(
        entity.entity_type == "POLICY_NUMBER"
        and entity.entity_value == "EHS-2025-04-BR"
        for entity in results
    )

    dob = next(entity for entity in results if entity.entity_type == "DATE_OF_BIRTH")
    assert dob.privacy_category == "PII"
    assert not {
        "Certified Mail",
        "CISO",
        "â€¢ Implemented",
        "â€¢ Secured",
        "the Health Insurance Portability",
    } & {entity.entity_value for entity in results}

    redacted = DocumentProcessingWorkflow._apply_redactions(
        BREACH_LETTER_SAMPLE,
        results,
    )
    assert "7389 5421 0089 6542" not in redacted
    assert "April 10-15, 2025" not in redacted
    assert "EHS-2025-04-BR" not in redacted


def test_validator_normalizes_insurance_and_healthcare_organizations():
    text = "Medicare and Evergreen Healthcare System"
    candidates = [
        _result(text, "Medicare", "ORGANIZATION", detector="presidio"),
        _result(
            text,
            "Evergreen Healthcare System",
            "ORGANIZATION",
            detector="presidio",
        ),
    ]

    results = EntityValidator.validate_candidates(candidates, text)

    assert {
        (entity.entity_type, entity.entity_value, entity.privacy_category)
        for entity in results
    } == {
        ("INSURANCE_PROVIDER", "Medicare", "PHI"),
        (
            "HEALTHCARE_ORGANIZATION",
            "Evergreen Healthcare System",
            "PHI",
        ),
    }


def test_gemma_policy_requires_policy_context():
    access_text = "Enroll using code: EHS-2025-04-BR"
    access_candidate = _result(
        access_text,
        "EHS-2025-04-BR",
        "POLICY_NUMBER",
    )
    unrelated_text = "Reference: EHS-2025-04-BR"
    unrelated_candidate = _result(
        unrelated_text,
        "EHS-2025-04-BR",
        "POLICY_NUMBER",
    )

    access_result = EntityValidator.validate_candidate(
        access_candidate,
        access_text,
    )
    unrelated_result = EntityValidator.validate_candidate(
        unrelated_candidate,
        unrelated_text,
    )

    assert access_result is not None
    assert access_result.entity_type == "ACCESS_CODE"
    assert unrelated_result is None


def test_validator_reclassifies_gemma_codes_and_rejects_false_dates():
    text = "CPT/HCPCS: 99214 Diagnosis: E11.9 Charge: $95.00 Date: 04/17/2024 Bad: 99/99/9999"
    candidates = [
        _result(text, "99214", "DATE"),
        _result(text, "E11.9", "DATE"),
        _result(text, "$95.00", "DATE"),
        _result(text, "04/17/2024", "DATE"),
        _result(text, "99/99/9999", "DATE"),
    ]

    results = EntityValidator.validate_candidates(candidates, text)
    detected = {(item.entity_type, item.entity_value) for item in results}

    assert ("CPT_CODE", "99214") in detected
    assert ("ICD10_CODE", "E11.9") in detected
    assert ("DATE", "04/17/2024") in detected
    assert not any(item.entity_value == "$95.00" for item in results)
    assert not any(item.entity_value == "99/99/9999" for item in results)


def test_validator_runs_before_masking():
    class BadDateDetector(BaseDetector):
        @property
        def name(self):
            return "gemma4e4b"

        def detect(self, text, page_number=1):
            return [_result(text, "$95.00", "DATE")]

    text = "Charge: $95.00"
    service = DetectionService()
    state = PipelineState(text)

    accepted = service._run_detector(BadDateDetector(), state, 1)

    assert accepted == []
    assert state.resolved_entities == []
    assert state.is_span_unmasked(text.index("$95.00"), len(text)) is True


def test_adjacent_patient_fragments_merge_using_source_span():
    text = "Patient Name: David A. Wilson"
    david_start = text.index("David")
    wilson_start = text.index("Wilson")
    entities = [
        DetectionResult(
            entity_type="PATIENT",
            entity_value="David A",
            confidence_score=0.90,
            start_char=david_start,
            end_char=david_start + len("David A"),
            page_number=1,
            detector="regex",
        ),
        DetectionResult(
            entity_type="PERSON",
            entity_value="Wilson",
            confidence_score=0.88,
            start_char=wilson_start,
            end_char=wilson_start + len("Wilson"),
            page_number=1,
            detector="presidio",
        ),
    ]

    merged = DetectionService()._merge_adjacent_person_spans(text, entities)

    assert len(merged) == 1
    assert merged[0].entity_type == "PATIENT"
    assert merged[0].entity_value == "David A. Wilson"


def test_review_rule_uses_only_final_confidence_threshold():
    high_confidence_cases = [
        ("ICD10_CODE", "I10", 0.95, {}),
        (
            "US_PHONE_NUMBER",
            "555-123-4567",
            0.98,
            {"conflicting_types": ["US_PHONE_NUMBER", "PHONE_NUMBER"]},
        ),
        (
            "ORGANIZATION",
            "Acme Health",
            0.95,
            {"conflicting_types": ["ORGANIZATION", "PERSON"]},
        ),
    ]

    for entity_type, value, confidence, metadata in high_confidence_cases:
        detection = SimpleNamespace(
            entity_type=entity_type,
            entity_value=value,
            confidence_score=confidence,
            metadata=metadata,
            detector="presidio",
        )
        assert DocumentProcessingWorkflow._is_review_required(detection) is False

    low_confidence = SimpleNamespace(confidence_score=0.79)
    assert DocumentProcessingWorkflow._is_review_required(low_confidence) is True


def test_gemma_recovery_uses_distinct_nearest_occurrences(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "false")

    class FakeClient:
        def chat(self, **kwargs):
            payload = {
                "results": [
                    {
                        "entity_type": "ICD10_CODE",
                        "entity_value": "I10",
                        "confidence_score": 0.90,
                        "start_char": 99,
                        "end_char": 102,
                    },
                    {
                        "entity_type": "ICD10_CODE",
                        "entity_value": "I10",
                        "confidence_score": 0.90,
                        "start_char": 9,
                        "end_char": 12,
                    },
                ]
            }
            return {"message": {"content": json.dumps(payload)}}

    detector = Gemma4E4BDetector()
    detector.client = FakeClient()

    results = detector.detect("I10 then I10")

    assert {(item.start_char, item.end_char) for item in results} == {
        (0, 3),
        (9, 12),
    }





EOB_REGRESSION_SAMPLE = """EXPLANATION OF BENEFITS (EOB)
HEALTHGUARD INSURANCE COMPANY
P.O. Box 45678, Grand Rapids, MI 49501
MEMBER INFORMATION
Patient Name: David A. Wilson
Group Name: Midwest Technology Solutions
Plan Type: PPO
CLAIMS SUMMARY
Provider: Farmington Medical Center
Provider NPI: 1592847603
SERVICE DETAILS
Date of Service	Procedure Diagnosis Provider Allowed Not
Service Description Code Code Charges Amount Covered
Office Visit,
04/17/2024 Established 99214 E11.9, I10 $225.00 $175.00 $50.00 $0.00 $35.
Patient, Level 4
Comprehensive
04/17/2024 Metabolic 80053 E11.9 $85.00 $65.00 $20.00 $0.00 $13.
Panel
Hemoglobin
04/17/2024	83036 E11.9 $95.00 $75.00 $20.00 $0.00 $15.
A1c
04/17/2024 Lipid Panel 80061 E78.5 $120.00 $90.00 $30.00 $0.00 $18.
ECG, routine,
04/17/2024 with	93000 I10, R00.2 $175.00 $140.00 $35.00 $0.00 $28.
interpretation
TOTALS	$700.00 $545.00 $155.00 $0.00 $10
PATIENT MEDICALINFORMATION
Current Medications:
â€¢ Metformin 1000mg twice daily
â€¢ Lisinopril 20mg daily
â€¢ Atorvastatin 40mg daily
â€¢ Aspirin 81mg daily
Recent Test Results:
â€¢ Hemoglobin A1c: 7.4%
YOUR APPEAL RIGHTS
Send your appeal to:
HealthGuard Insurance Company
Appeals Department
P.O. Box 87654
Grand Rapids, MI 49501
NOTES
â€¢ Keep this document for your tax records.
CONFIDENTIAL HEALTH INFORMATION: This document contains protected health information (PHI).
"""


def test_eob_regression_detects_deterministic_healthcare_entities(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "true")
    monkeypatch.setenv("GLINER_ENABLED", "false")

    results = DetectionService().detect(
        EOB_REGRESSION_SAMPLE,
        document_type="MEDICAL_RECORD",
    )
    detected = {(entity.entity_type, entity.entity_value) for entity in results}

    assert ("PROVIDER", "Farmington Medical Center") in detected
    assert ("INSURANCE_PROVIDER", "HEALTHGUARD INSURANCE COMPANY") in detected
    assert ("INSURANCE_PROVIDER", "HealthGuard Insurance Company") in detected
    for code in {"99214", "80053", "83036", "80061", "93000"}:
        assert ("CPT_CODE", code) in detected
    for medication in {"Lisinopril", "Atorvastatin", "Aspirin"}:
        assert ("MEDICATION", medication) in detected
    assert ("CLINICAL_MEASUREMENT", "7.4%") in detected

    rejected_values = {
        "PPO",
        "Individual /",
        "Date of Service",
        "Level 4",
        "TOTALS",
        "PHI",
        "â€¢ Keep",
        "Comprehensive",
        "Metabolic",
        "Panel",
    }
    assert not rejected_values & {entity.entity_value for entity in results}

    redacted = DocumentProcessingWorkflow._apply_redactions(
        EOB_REGRESSION_SAMPLE,
        results,
    )
    assert "Farmington Medical Center" not in redacted
    assert "HealthGuard Insurance Company" not in redacted
    assert "80053" not in redacted
    assert "Lisinopril" not in redacted
    assert "7.4%" not in redacted
    assert "Plan Type: PPO" in redacted
    assert "Patient, Level 4" in redacted
    assert "TOTALS" in redacted
    assert "Keep this document" in redacted


def test_validator_rejects_eob_table_labels_and_gemma_lab_fragments():
    text = (
        "Plan Type: PPO\nDate of Service\nPatient, Level 4\nTOTALS\n"
        "CONFIDENTIAL HEALTH INFORMATION (PHI)\n"
        "â€¢ Keep this document\nComprehensive\nMetabolic\nPanel\n"
    )
    candidates = [
        _result(text, "PPO", "ORGANIZATION", detector="presidio"),
        _result(text, "Date of Service", "ORGANIZATION", detector="presidio"),
        _result(text, "Level 4", "PERSON", detector="presidio"),
        _result(text, "TOTALS", "ORGANIZATION", detector="presidio"),
        _result(text, "PHI", "ORGANIZATION", detector="presidio"),
        _result(text, "â€¢ Keep", "PERSON", detector="presidio"),
        _result(text, "Comprehensive", "MEDICAL_FACILITY", detector="gemma4e4b"),
        _result(text, "Metabolic", "MEDICAL_FACILITY", detector="gemma4e4b"),
        _result(text, "Panel", "MEDICAL_FACILITY", detector="gemma4e4b"),
    ]

    assert EntityValidator.validate_candidates(candidates, text) == []


def test_validator_rejects_amount_covered_and_field_headers():
    text = "Amount Billed: $93.00\nAmountCovered: $176.00\nVisitDate: 2024-07-23\n"
    candidates = [
        _result(text, "Amount Billed", "ORGANIZATION", detector="gemma4e4b"),
        _result(text, "AmountCovered", "ORGANIZATION", detector="gemma4e4b"),
        _result(text, "VisitDate", "ORGANIZATION", detector="gemma4e4b"),
    ]
    assert EntityValidator.validate_candidates(candidates, text) == []


def test_validator_rejects_bullet_labels_and_form_headers():
    text = (
        "• Patient Responsibility\n"
        "EXCLUDED SERVICES & OTHER COVERED SERVICES Not Covered: Cosmetic\n"
        "Weight Loss Programs\n"
    )
    candidates = [
        _result(text, "• Patient", "ORGANIZATION", detector="presidio"),
        _result(text, "EXCLUDED SERVICES & OTHER COVERED SERVICES Not Covered: Cosmetic", "ORGANIZATION", detector="presidio"),
        _result(text, "Weight", "ORGANIZATION", detector="presidio"),
    ]
    assert EntityValidator.validate_candidates(candidates, text) == []

    azure = AzureOpenAIDetector()
    item1 = azure._heuristic_validate_candidate(_result(text, "• Patient", "ORGANIZATION"), text)
    item2 = azure._heuristic_validate_candidate(_result(text, "Weight", "ORGANIZATION"), text)
    assert item1.decision == "REJECT"
    assert item2.decision == "REJECT"


def test_validator_rejects_sentence_fragments_and_trims_prefixes():
    text = (
        "SSN: 123-45-6789\n"
        "Contact Numbers: Listed in follow-up and provider sections\n"
        "Full name repeated in multiple sections\n"
        "Direct references to diagnosis, treatment, and outcomes\n"
    )
    candidates = [
        _result(text, "Contact Numbers: Listed in follow-up and provider sections", "PHONE_NUMBER", detector="azure"),
        _result(text, "Full name repeated in multiple sections", "PERSON", detector="azure"),
        _result(text, "Direct references to diagnosis, treatment, and outcomes", "CLINICAL_NOTES", detector="azure"),
    ]
    assert EntityValidator.validate_candidates(candidates, text) == []

    ssn_candidate = _result(text, "SSN: 123-45-6789", "SSN", detector="regex")
    validated_ssn = EntityValidator.validate_candidate(ssn_candidate, text)
    assert validated_ssn is not None
    assert validated_ssn.entity_value == "123-45-6789"


def test_validator_keeps_neighborhood_names_as_locations():
    text = "Office Location: Jubilee Hills"
    candidate = _result(
        text,
        "Jubilee Hills",
        "LOCATION",
        detector="gliner",
    )

    validated = EntityValidator.validate_candidates([candidate], text)

    assert len(validated) == 1
    assert validated[0].entity_type == "LOCATION"

