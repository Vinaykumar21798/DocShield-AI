from modules.detection.detectors.gliner_detector import GLiNERDetector

sample_text = """
Patient Name: John Doe

Hospital:
Apollo Hospital

Address:
Hyderabad, Telangana

Dr. Ramesh referred the patient to AIIMS Delhi.
"""

detector = GLiNERDetector()

results = detector.detect(sample_text)

print("\n========== GLiNER TEST ==========\n")

for entity in results:

    print(f"Type       : {entity.entity_type}")
    print(f"Value      : {entity.entity_value}")
    print(f"Confidence : {entity.confidence_score:.2f}")
    print(f"Detector   : {entity.detector}")
    print(f"Metadata   : {entity.metadata}")
    print("-" * 60)