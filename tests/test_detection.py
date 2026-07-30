from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult
from modules.detection.service import DetectionService


sample_text = """
Patient Name: John Doe
Age: 45

Hospital:
Apollo Hospital

Email:
john.doe@gmail.com

Phone:
9876543210

Aadhaar:
1234 5678 9012

PAN:
ABCDE1234F

Diagnosis:
Diabetes Mellitus

Medication:
Metformin 500mg

Address:
Hyderabad, Telangana
"""


service = DetectionService()

results = service.detect(sample_text)

print("\nDetected Entities\n")
print("-" * 60)

for entity in results:

    print(f"Entity Type : {entity.entity_type}")
    print(f"Value       : {entity.entity_value}")
    print(f"Confidence  : {entity.confidence_score:.2f}")
    print(f"Detector    : {entity.detector}")
    print(f"Metadata    : {entity.metadata}")
    print("-" * 60)


class FakeDetector(BaseDetector):
    def __init__(
        self,
        name,
        result=None,
        should_run=True,
    ):
        self._name = name
        self.result = result
        self._should_run = should_run
        self.seen_texts = []
        self.should_run_texts = []
        self.contexts = []

    @property
    def name(self):
        return self._name

    def should_run(self, text, state):
        self.should_run_texts.append(text)
        return self._should_run

    def detect(self, text, page_number=1):
        self.seen_texts.append(text)
        self.contexts.append(getattr(self, "orchestration_context", None))
        if self.result is None:
            return []
        return [
            DetectionResult(
                entity_type=self.result["type"],
                entity_value=self.result["value"],
                confidence_score=self.result.get("confidence", 0.91),
                start_char=self.result["start"],
                end_char=self.result["end"],
                page_number=page_number,
                detector=self.name,
                metadata={"test_detector": True},
            )
        ]


class FailDetector(FakeDetector):
    def should_run(self, text, state):
        raise AssertionError(f"{self.name} should not be selected")

    def detect(self, text, page_number=1):
        raise AssertionError(f"{self.name} should not execute")


class FakeValidator:
    def __init__(self):
        self.context = None
        self.entities = None

    def validate_batch(self, context, entities):
        self.context = context
        self.entities = list(entities)
        for entity in entities:
            entity.metadata["validated_by"] = "fake_validator"
            entity.metadata["valid"] = True
        return entities


def service_with_detectors(regex, presidio, gliner, medspacy):
    service = DetectionService()
    service.regex = regex
    service._presidio = presidio
    service._gliner = gliner
    service._medspacy = medspacy
    return service


def test_dynamic_orchestrator_masks_text_between_detector_stages(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "true")
    text = "Name: Alpha\nName: Beta\nName: Gamma"

    regex = FakeDetector(
        "regex",
        {"type": "PERSON", "value": "Alpha", "start": 6, "end": 11},
    )
    presidio = FakeDetector(
        "presidio",
        {"type": "PERSON", "value": "Beta", "start": 18, "end": 22},
    )
    gliner = FakeDetector(
        "gliner",
        {"type": "PERSON", "value": "Gamma", "start": 29, "end": 34},
    )
    medspacy = FailDetector("medspacy")
    service = service_with_detectors(regex, presidio, gliner, medspacy)

    results = service.detect(text)

    assert [item.entity_value for item in results] == ["Alpha", "Beta", "Gamma"]
    assert presidio.seen_texts == ["Name:      \nName: Beta\nName: Gamma"]
    assert gliner.seen_texts == ["Name:      \nName:     \nName: Gamma"]
    assert medspacy.seen_texts == []
    assert presidio.contexts[0]["remaining_text"] == presidio.seen_texts[0]
    assert [e.entity_value for e in presidio.contexts[0]["previous_entities"]] == ["Alpha"]


def test_financial_route_runs_presidio_before_gliner(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "true")
    text = (
        "Bank statement\n"
        "Account holder: Ravi Kumar\n"
        "Email: ravi@example.com"
    )
    email_start = text.index("ravi@example.com")
    name_start = text.index("Ravi Kumar")

    regex = FakeDetector(
        "regex",
        {
            "type": "EMAIL",
            "value": "ravi@example.com",
            "start": email_start,
            "end": email_start + len("ravi@example.com"),
        },
    )
    presidio = FakeDetector("presidio", result=None)
    gliner = FakeDetector(
        "gliner",
        {
            "type": "PERSON",
            "value": "Ravi Kumar",
            "start": name_start,
            "end": name_start + len("Ravi Kumar"),
        },
    )
    service = service_with_detectors(
        regex,
        presidio,
        gliner,
        FailDetector("medspacy"),
    )

    results = service.detect(text)

    assert [item.detector for item in results] == ["gliner", "regex"]
    assert presidio.seen_texts
    assert gliner.seen_texts
    assert "ravi@example.com" not in presidio.seen_texts[0]
    assert "ravi@example.com" not in gliner.seen_texts[0]
    assert gliner.contexts[0]["executed_detectors"] == ["regex", "presidio"]


def test_healthcare_route_runs_medspacy_before_gliner(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "true")
    text = "Clinical note\nPatient Name: Maya Rao\nDiagnosis: Back Pain"
    diagnosis_start = text.index("Back Pain")
    medspacy = FakeDetector(
        "medspacy",
        {
            "type": "DIAGNOSIS",
            "value": "Back Pain",
            "start": diagnosis_start,
            "end": diagnosis_start + len("Back Pain"),
        },
    )
    gliner = FakeDetector("gliner", result=None)
    service = service_with_detectors(
        FakeDetector("regex", result=None),
        FakeDetector("presidio", result=None),
        gliner,
        medspacy,
    )

    results = service.detect(text)

    assert [item.entity_value for item in results] == ["Back Pain"]
    assert medspacy.contexts[0]["executed_detectors"] == [
        "regex",
        "presidio",
    ]
    assert gliner.contexts[0]["executed_detectors"] == [
        "regex",
        "presidio",
        "medspacy",
    ]
    assert "Back Pain" not in gliner.seen_texts[0]


def test_llm_validation_receives_only_low_confidence_entities_with_bounded_context(
    monkeypatch,
):
    monkeypatch.setenv("BYPASS_LLM", "false")
    monkeypatch.setenv("DETECTION_LLM_CONTEXT_WINDOW", "10")
    text = "." * 500 + "SSN: 123-45-6789" + "." * 500
    ssn_start = text.index("123-45-6789")

    regex = FakeDetector(
        "regex",
        {
            "type": "SSN",
            "value": "123-45-6789",
            "start": ssn_start,
            "end": ssn_start + len("123-45-6789"),
            "confidence": 0.50,
        },
    )
    service = service_with_detectors(
        regex,
        FailDetector("presidio"),
        FailDetector("gliner"),
        FailDetector("medspacy"),
    )
    validator = FakeValidator()
    service.validator = validator

    results = service.detect(text)

    assert len(results) == 1
    assert validator.entities == results
    assert "123-45-6789" in validator.context
    assert validator.context != text
    assert len(validator.context) < len(text)


def test_detector_with_no_entities_routes_to_next_candidate_detector(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "true")
    text = "Name: Beta"

    regex = FakeDetector("regex", result=None)
    presidio = FakeDetector(
        "presidio",
        {"type": "PERSON", "value": "Beta", "start": 6, "end": 10},
    )
    service = service_with_detectors(
        regex,
        presidio,
        FailDetector("gliner"),
        FailDetector("medspacy"),
    )

    results = service.detect(text)

    assert [item.entity_value for item in results] == ["Beta"]
    assert regex.seen_texts == [text]
    assert presidio.seen_texts == [text]


def test_pipeline_stops_on_absent_entity_candidates_not_leftover_labels(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "true")
    text = "Email\nPhone\nDiagnosis\n"

    regex = FakeDetector("regex", result=None)
    service = service_with_detectors(
        regex,
        FailDetector("presidio"),
        FailDetector("gliner"),
        FailDetector("medspacy"),
    )

    results = service.detect(text)

    assert results == []
    assert regex.seen_texts == [text]


class FakeQwenDetector(BaseDetector):
    client = object()

    def __init__(self):
        self.seen_texts = []
        self.contexts = []

    @property
    def name(self):
        return "qwen3b"

    def should_run(self, text, state):
        return True

    def detect(self, text, page_number=1):
        self.seen_texts.append(text)
        self.contexts.append(getattr(self, "orchestration_context", None))
        start = text.index("Alice")
        return [
            DetectionResult(
                entity_type="PERSON",
                entity_value="Alice",
                confidence_score=0.90,
                start_char=start,
                end_char=start + len("Alice"),
                page_number=page_number,
                detector=self.name,
                metadata={"test_detector": True},
            )
        ]


def test_qwen_runs_only_on_bounded_unresolved_candidate_context(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "false")
    monkeypatch.setenv("DETECTION_LLM_CONTEXT_WINDOW", "10")
    monkeypatch.setenv("DETECTION_MAX_UNRESOLVED_LLM_CONTEXTS", "1")
    text = "x" * 300 + "\nName: Alice\n" + "y" * 300
    alice_start = text.index("Alice")

    service = service_with_detectors(
        FakeDetector("regex", result=None),
        FakeDetector("presidio", result=None),
        FakeDetector("gliner", result=None),
        FakeDetector("medspacy", result=None),
    )
    fake_qwen = FakeQwenDetector()
    service._qwen3b = fake_qwen

    results = service.detect(text)

    assert [item.entity_value for item in results] == ["Alice"]
    assert results[0].start_char == alice_start
    assert fake_qwen.seen_texts
    assert fake_qwen.seen_texts[0] != text
    assert len(fake_qwen.seen_texts[0]) < len(text)
    assert fake_qwen.contexts[0]["text_offset"] > 0


def test_eob_detection_extracts_clean_healthcare_entities(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "true")
    text = """Explanation of Benefits (EOB)
Patient Name: Michael Robinson
DOB: 2006-01-13
SSN: 581-11-5467
Insurance ID: Fcg-35528379
Visit Date: 2024-01-13
Provider: Rojas-Gutierrez
Procedure Code: CPT99213
Diagnosis: Back Pain
Amount Billed: $662.00
Amount Covered: $354.00
"""

    results = DetectionService().detect(text)
    by_type = {entity.entity_type: entity for entity in results}

    assert by_type["PATIENT"].entity_value == "Michael Robinson"
    assert by_type["PATIENT"].detector == "Regex"
    assert by_type["PATIENT"].confidence_score == 1.0
    assert by_type["DATE_OF_BIRTH"].entity_value == "2006-01-13"
    assert "DOB:" not in by_type["DATE_OF_BIRTH"].entity_value
    assert by_type["SSN"].entity_value == "581-11-5467"
    assert by_type["INSURANCE_ID"].entity_value == "Fcg-35528379"
    assert by_type["VISIT_DATE"].entity_value == "2024-01-13"
    assert by_type["PROVIDER"].entity_value == "Rojas-Gutierrez"
    assert by_type["CPT_CODE"].entity_value == "CPT99213"
    assert by_type["CPT_CODE"].privacy_category == "PHI"
    assert by_type["DIAGNOSIS"].entity_value == "Back Pain"

def test_employment_verification_detects_person_and_labeled_military_address(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "true")
    text = """Employment Verification

This letter is to verify that Rebecca Norris DVM is currently employed with Odonnell Inc in the role of Journalist, broadcasting.

Details:
- Employee ID: EMP3896
- SSN: 400-04-2603
- DOB: 1992-03-19
- Start Date: 2020-10-24
- Salary: $133392
- Address: USCGC Miller, FPO AE 99567

Sincerely,
HR Department
"""

    results = DetectionService().detect(text)
    by_type = {entity.entity_type: entity for entity in results}

    assert by_type["PERSON"].entity_value == "Rebecca Norris"
    assert by_type["PERSON"].detector == "presidio"
    assert by_type["ADDRESS"].entity_value == "USCGC Miller, FPO AE 99567"
    assert by_type["ADDRESS"].detector == "Regex"
    assert "ZIP_CODE" not in by_type
    assert by_type["SSN"].entity_value == "400-04-2603"
    assert by_type["DATE_OF_BIRTH"].entity_value == "1992-03-19"


def test_mixed_enterprise_document_detects_all_structured_parties_without_extra_detectors(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "true")
    monkeypatch.setenv("GLINER_ENABLED", "false")
    text = """=========================================================
                ENTERPRISE SERVICE AGREEMENT
=========================================================

Agreement ID      : AGR-2026-004589
Date              : 28-Jul-2026

Customer Name     : Michael Robinson
Email             : michael.robinson@example.com
Phone             : +1-202-555-0148
Employee ID       : EMP-10452
PAN               : ABCDE1234F
Aadhaar           : 5678 1234 9876
Passport No       : M12345678
Driving License   : KA01 20240012345

---------------------------------------------------------
Company Information
---------------------------------------------------------

Organization       : ABC Technologies Pvt Ltd
GSTIN              : 29ABCDE1234F1Z5
Bank Account       : 1234567890123456
IFSC               : HDFC0001234
Invoice Number     : INV-2026-1045

---------------------------------------------------------
Medical Information
---------------------------------------------------------

Patient Name       : Michael Robinson
Hospital           : City Care Hospital
Doctor             : Dr. Sarah Williams
MRN                : MRN-458721
Diagnosis          : Type 2 Diabetes Mellitus
Medication         : Metformin 500mg
Procedure          : Blood Glucose Test
Visit Date         : 27-Jul-2026

---------------------------------------------------------
Insurance
---------------------------------------------------------

Policy Number      : POL-98345210
Claim Number       : CLM-2026-00982
Insurance Company  : HealthSecure Insurance

---------------------------------------------------------
Legal Section
---------------------------------------------------------

This agreement is signed between ABC Technologies Pvt Ltd
and Michael Robinson.

Witness:
Emily Carter

Authorized Signatory:
David Johnson

---------------------------------------------------------
Contact Information
---------------------------------------------------------

Address:
221B Baker Street
London
NW1 6XE

Emergency Contact:
Jennifer Robinson
Phone: +1-202-555-0199

Email:
jennifer.robinson@example.com
"""

    results = DetectionService().detect(text)
    detected = {(entity.entity_type, entity.entity_value) for entity in results}

    expected = {
        ("DOCUMENT_ID", "AGR-2026-004589"),
        ("DATE", "28-Jul-2026"),
        ("PERSON", "Michael Robinson"),
        ("EMAIL", "michael.robinson@example.com"),
        ("US_PHONE_NUMBER", "+1-202-555-0148"),
        ("EMPLOYEE_ID", "EMP-10452"),
        ("PAN_NUMBER", "ABCDE1234F"),
        ("AADHAAR_NUMBER", "5678 1234 9876"),
        ("PASSPORT_NUMBER", "M12345678"),
        ("DRIVING_LICENSE", "KA01 20240012345"),
        ("ORGANIZATION", "ABC Technologies Pvt Ltd"),
        ("GSTIN", "29ABCDE1234F1Z5"),
        ("BANK_ACCOUNT_NUMBER", "1234567890123456"),
        ("IFSC_CODE", "HDFC0001234"),
        ("INVOICE_NUMBER", "INV-2026-1045"),
        ("PATIENT", "Michael Robinson"),
        ("HOSPITAL", "City Care Hospital"),
        ("DOCTOR", "Dr. Sarah Williams"),
        ("MEDICAL_RECORD_NUMBER", "MRN-458721"),
        ("DIAGNOSIS", "Type 2 Diabetes Mellitus"),
        ("MEDICATION", "Metformin 500mg"),
        ("PROCEDURE", "Blood Glucose Test"),
        ("VISIT_DATE", "27-Jul-2026"),
        ("POLICY_NUMBER", "POL-98345210"),
        ("CLAIM_NUMBER", "CLM-2026-00982"),
        ("ORGANIZATION", "HealthSecure Insurance"),
        ("PERSON", "Emily Carter"),
        ("PERSON", "David Johnson"),
        ("ADDRESS", "221B Baker Street\nLondon\nNW1 6XE"),
        ("PERSON", "Jennifer Robinson"),
        ("US_PHONE_NUMBER", "+1-202-555-0199"),
        ("EMAIL", "jennifer.robinson@example.com"),
    }

    assert expected <= detected
    assert not any(entity.entity_value == "Insurance Company" for entity in results)
    assert not any(
        entity.entity_type == "CREDIT_CARD_NUMBER"
        and entity.entity_value == "1234567890123456"
        for entity in results
    )
    assert len([
        entity for entity in results
        if entity.entity_type == "PERSON" and entity.entity_value == "Michael Robinson"
    ]) == 2
    assert len([
        entity for entity in results
        if entity.entity_type == "ORGANIZATION" and entity.entity_value == "ABC Technologies Pvt Ltd"
    ]) == 2
    assert {entity.detector for entity in results} == {"Regex"}


def test_deduplicator_preserves_repeated_same_value_at_different_spans():
    from modules.detection.deduplicator import Deduplicator

    detections = [
        DetectionResult(
            entity_type="PERSON",
            entity_value="Michael Robinson",
            confidence_score=0.9,
            start_char=10,
            end_char=26,
            page_number=1,
            detector="Regex",
        ),
        DetectionResult(
            entity_type="PERSON",
            entity_value="Michael Robinson",
            confidence_score=0.8,
            start_char=100,
            end_char=116,
            page_number=1,
            detector="presidio",
        ),
    ]

    results = Deduplicator.deduplicate(detections)

    assert len(results) == 2
    assert {(entity.start_char, entity.end_char) for entity in results} == {
        (10, 26),
        (100, 116),
    }
