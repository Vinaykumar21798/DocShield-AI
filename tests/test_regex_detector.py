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