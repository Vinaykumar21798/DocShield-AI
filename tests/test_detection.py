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