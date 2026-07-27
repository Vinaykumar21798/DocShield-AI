from modules.detection.detectors.presidio_detector import PresidioDetector

sample_text = """
Patient Name: John Doe

Hospital:
Apollo Hospital

Address:
Hyderabad, Telangana

Visited on:
12 January 2024
"""

detector = PresidioDetector()

results = detector.detect(sample_text)

print("\n========== PRESIDIO TEST ==========\n")

for entity in results:
    print(f"Type       : {entity.entity_type}")
    print(f"Value      : {entity.entity_value}")
    print(f"Confidence : {entity.confidence_score:.2f}")
    print(f"Detector   : {entity.detector}")
    print("-" * 50)