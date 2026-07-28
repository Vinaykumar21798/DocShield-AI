from modules.detection.detectors.medspacy_detector import MedSpaCyDetector

sample_text = """
Patient Name: John Doe
Age: 45

Chief Complaint:
Fever and cough for 5 days.

Diagnosis:
Diabetes Mellitus
Hypertension

Medication:
Metformin 500 mg twice daily
Paracetamol 650 mg

Procedure:
MRI Brain

Laboratory Results:
Blood Glucose: 180 mg/dL
HbA1c: 8.2%

Allergy:
Penicillin

Hospital:
Apollo Hospital
"""

detector = MedSpaCyDetector()

results = detector.detect(sample_text)

print("\n========== MEDSPACY TEST ==========\n")

for entity in results:

    print(f"Type       : {entity.entity_type}")
    print(f"Value      : {entity.entity_value}")
    print(f"Confidence : {entity.confidence_score:.2f}")
    print(f"Detector   : {entity.detector}")
    print(f"Metadata   : {entity.metadata}")
    print("-" * 60)