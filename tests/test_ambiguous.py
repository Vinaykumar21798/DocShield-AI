from modules.detection.service import DetectionService

service = DetectionService()

TEST_CASES = [
    {
        "name": "1. Happy Path",
        "text": """
Patient Name: John Doe
Hospital: Apollo Hospital
Email: john@gmail.com
Phone: 9876543210
PAN: ABCDE1234F

Diagnosis:
Diabetes

Medication:
Metformin

Address:
Hyderabad, Telangana
""",
    },

    {
        "name": "2. Person Inside Hospital",
        "text": """
Patient:
John Doe

Hospital:
John Doe Hospital
""",
    },

    {
        "name": "3. Doctor vs Person",
        "text": """
Consultant:
Dr. Ramesh Kumar

Patient:
Ramesh Kumar
""",
    },

    {
        "name": "4. Organization vs Hospital",
        "text": """
Apollo Hospitals Ltd.
Apollo Hospital
Apollo Pharmacy
""",
    },

    {
        "name": "5. Address Header",
        "text": """
Address:
Hyderabad
""",
    },

    {
        "name": "6. Real Address",
        "text": """
221B Baker Street
London
NW1 6XE
""",
    },

    {
        "name": "7. PAN Embedded",
        "text": """
His PAN ABCDE1234F was verified successfully.
""",
    },

    {
        "name": "8. Aadhaar vs Credit Card",
        "text": """
Credit Card:
4111 1111 1111 1111

Aadhaar:
1234 5678 9123
""",
    },

    {
        "name": "9. Medical + PII",
        "text": """
John Doe

DOB:
12 Jan 1990

Hospital:
Apollo Hospital

Diagnosis:
Diabetes

Medication:
Metformin

Email:
john@gmail.com
""",
    },

    {
        "name": "10. Washington Ambiguity",
        "text": """
Patient lives in Washington.

Visited Washington Hospital.
""",
    },

    {
        "name": "11. Parkinson Ambiguity",
        "text": """
Diagnosis:
Parkinson disease

Dr. Parkinson examined the patient.
""",
    },

    {
        "name": "12. Medical Record Number",
        "text": """
MRN:
MR123456
""",
    },

    {
        "name": "13. Email Embedded",
        "text": """
Please contact john@gmail.com immediately.
""",
    },

    {
        "name": "14. Phone Embedded",
        "text": """
Emergency Contact:
+91 9876543210
""",
    },

    {
        "name": "15. Multiple Hospitals",
        "text": """
Apollo Hospital

KIMS Hospital

Yashoda Hospital
""",
    },

    {
        "name": "16. Hospital + Location",
        "text": """
Apollo Hospital Hyderabad
""",
    },

    {
        "name": "17. Section Headers Only",
        "text": """
Address

Hospital

Diagnosis

Medication

Email

Phone
""",
    },

    {
        "name": "18. OCR Noise",
        "text": """
P@tient N4me

J0hn D0e

Ap0llo Hospita1

98765S4321
""",
    },

    {
        "name": "19. Long Clinical Note",
        "text": """
Patient Name:
John Doe

Visited Apollo Hospital on
12 Jan 2024.

Diagnosis:
Hypertension

Medication:
Metformin

Email:
john@gmail.com

Phone:
9876543210
""",
    },

    {
        "name": "20. Empty Document",
        "text": "",
    },

    {
        "name": "21. KYC Document",
        "text": """
Customer Name:
Rahul Sharma

DOB:
12/08/1995

PAN:
ABCDE1234F

Aadhaar:
1234 5678 9123

Passport:
P1234567

Email:
rahul@gmail.com

Phone:
9876543210

Address:
12 MG Road,
Bengaluru,
Karnataka - 560001
""",
    },

    {
        "name": "22. Bank Statement",
        "text": """
Account Holder:
Ravi Kumar

Account Number:
1234567890123456

IFSC:
HDFC0001234

UPI:
ravi@okhdfcbank

Credit Card:
4111 1111 1111 1111

Phone:
9876543210
""",
    },

    {
        "name": "23. Hospital Discharge Summary",
        "text": """
Patient:
John Doe

MRN:
MR12345

Hospital:
Apollo Hospital

Consultant:
Dr. Meena Rao

Diagnosis:
Type 2 Diabetes

Hypertension

Medication:
Metformin

Aspirin
""",
    },

    {
        "name": "24. Resume",
        "text": """
Rahul Sharma

Email:
rahul@gmail.com

Phone:
9876543210

Address:
Hyderabad

Worked at Microsoft.

Worked at Google.
""",
    },

    {
        "name": "25. Email Conversation",
        "text": """
From:
john@gmail.com

To:
alice@gmail.com

Hi Alice,

Please call me at 9876543210.

Regards,

John
""",
    },

    {
        "name": "26. Clinical Prescription",
        "text": """
Apollo Hospital

Dr. Rajesh Kumar

Diagnosis:
Hypertension

Medicines

Metformin 500mg

Paracetamol 650mg
""",
    },

    {
        "name": "27. Adversarial Case",
        "text": """
Washington Hospital

Washington

Dr. Parkinson

Parkinson disease

John Doe Hospital

John Doe
""",
    },
]


for case in TEST_CASES:

    print("\n" + "=" * 80)
    print(case["name"])
    print("=" * 80)

    results = service.detect(case["text"])

    if not results:
        print("No entities found.")
        continue

    for r in results:
        print(
            f"{r.entity_type:<22}"
            f"{r.entity_value:<35}"
            f"{r.detector:<12}"
            f"{r.confidence_score:.2f}"
        )