# Isolated per-detector evaluation report

- Gold annotations: **66** (manual, from content.txt)
- Source text: `storage/runs/03b21b46-ea02-4d21-9429-331a9ca7456a/documents/3148c6b8-7198-45d1-951f-2a1dbde6e623/extracted/content.txt`

## Regex

- Mode: `pure_python` | predictions: 41
- Availability error: None
- Run error: None

| Metric | All conf | >= 0.80 |
| :--- | :--- | :--- |
| True positives | 35 | 32 |
| False positives | 6 | 6 |
| False negatives | 31 | 34 |
| Precision | 0.854 | 0.842 |
| Recall | 0.530 | 0.485 |
| F1 | 0.654 | 0.615 |

### False negatives (31)

| # | value | type | page |
| :--- | :--- | :--- | :--- |
| 1 | `Jane R. Smith` | PERSON | 1 |
| 2 | `XXX-XX-7890` | SSN | 1 |
| 3 | `Westfield` | LOCATION | 1 |
| 4 | `MI` | LOCATION | 1 |
| 5 | `Horizon Technologies Inc.` | ORGANIZATION | 1 |
| 6 | `Robert Smith` | PERSON | 1 |
| 7 | `09/22/1980` | DATE_OF_BIRTH | 1 |
| 8 | `XXX-XX-2468` | SSN | 1 |
| 9 | `Emma Smith` | PERSON | 1 |
| 10 | `06/12/2012` | DATE_OF_BIRTH | 1 |
| 11 | `XXX-XX-3579` | SSN | 1 |
| 12 | `Noah Smith` | PERSON | 1 |
| 13 | `11/04/2015` | DATE_OF_BIRTH | 1 |
| 14 | `XXX-XX-1357` | SSN | 1 |
| 15 | `Hypertension` | DISEASE | 3 |
| 16 | `Type 2 Diabetes` | DISEASE | 3 |
| 17 | `Seasonal allergies` | ALLERGY | 3 |
| 18 | `Lisinopril` | MEDICATION | 4 |
| 19 | `Metformin` | MEDICATION | 4 |
| 20 | `Cetirizine` | MEDICATION | 4 |
| 21 | `Colonoscopy` | PROCEDURE | 4 |
| 22 | `Right knee arthroscopy` | PROCEDURE | 4 |
| 23 | `Grand Rapids` | LOCATION | 5 |
| 24 | `MI` | LOCATION | 5 |
| 25 | `Grand Rapids` | LOCATION | 5 |
| 26 | `MI` | LOCATION | 5 |
| 27 | `789 Insurance Avenue` | ADDRESS | 5 |
| 28 | `Grand Rapids` | LOCATION | 5 |
| 29 | `MI` | LOCATION | 5 |
| 30 | `HealthGuard Insurance Company` | ORGANIZATION | 5 |
| 31 | `Michael J. Williams` | PERSON | 6 |

### False positives (6)

| # | value | raw type | canonical | page | conf |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `09/22/1980` | DATE_TIME | DATE | 1 | 1.0 |
| 2 | `06/12/2012` | DATE_TIME | DATE | 1 | 0.85 |
| 3 | `11/04/2015` | DATE_TIME | DATE | 1 | 0.85 |
| 4 | `XXX-XX-1357` | INSURANCE_ID | POLICY_NUMBER | 1 | 1.0 |
| 5 | `8:00 AM` | DATE_TIME | DATE | 5 | 0.85 |
| 6 | `8:00 PM` | DATE_TIME | DATE | 5 | 0.85 |

---

## Presidio

- Mode: `presidio+spacy` | predictions: 71
- Availability error: None
- Run error: None

| Metric | All conf | >= 0.80 |
| :--- | :--- | :--- |
| True positives | 22 | 18 |
| False positives | 49 | 46 |
| False negatives | 44 | 48 |
| Precision | 0.310 | 0.281 |
| Recall | 0.333 | 0.273 |
| F1 | 0.321 | 0.277 |

### False negatives (44)

| # | value | type | page |
| :--- | :--- | :--- | :--- |
| 1 | `HIP-2024-45871239` | POLICY_NUMBER | 1 |
| 2 | `04/18/1982` | DATE_OF_BIRTH | 1 |
| 3 | `XXX-XX-7890` | SSN | 1 |
| 4 | `Westfield` | LOCATION | 1 |
| 5 | `MI` | LOCATION | 1 |
| 6 | `48185` | ZIP_CODE | 1 |
| 7 | `(313) 555-7842` | US_PHONE_NUMBER | 1 |
| 8 | `jsmith@emailexample.com` | EMAIL | 1 |
| 9 | `HTI-24680` | GROUP_NUMBER | 1 |
| 10 | `09/22/1980` | DATE_OF_BIRTH | 1 |
| 11 | `XXX-XX-2468` | SSN | 1 |
| 12 | `06/12/2012` | DATE_OF_BIRTH | 1 |
| 13 | `XXX-XX-3579` | SSN | 1 |
| 14 | `11/04/2015` | DATE_OF_BIRTH | 1 |
| 15 | `XXX-XX-1357` | SSN | 1 |
| 16 | `Hypertension` | DISEASE | 3 |
| 17 | `Type 2 Diabetes` | DISEASE | 3 |
| 18 | `Seasonal allergies` | ALLERGY | 3 |
| 19 | `Lisinopril` | MEDICATION | 4 |
| 20 | `10mg` | DOSAGE | 4 |
| 21 | `Metformin` | MEDICATION | 4 |
| 22 | `500mg` | DOSAGE | 4 |
| 23 | `Cetirizine` | MEDICATION | 4 |
| 24 | `10mg` | DOSAGE | 4 |
| 25 | `Colonoscopy` | PROCEDURE | 4 |
| 26 | `Right knee arthroscopy` | PROCEDURE | 4 |
| 27 | `P.O. Box 45678` | ADDRESS | 5 |
| 28 | `MI` | LOCATION | 5 |
| 29 | `49501` | ZIP_CODE | 5 |
| 30 | `(800) 555-2468` | US_PHONE_NUMBER | 5 |
| 31 | `(800) 555-3579` | US_PHONE_NUMBER | 5 |
| 32 | `www.healthguardinsurance.com/claims` | URL | 5 |
| 33 | `P.O. Box 87654` | ADDRESS | 5 |
| 34 | `MI` | LOCATION | 5 |
| 35 | `49501` | ZIP_CODE | 5 |
| 36 | `(800) 555-9876` | US_PHONE_NUMBER | 5 |
| 37 | `(800) 555-8765` | US_PHONE_NUMBER | 5 |
| 38 | `www.healthguardinsurance.com/appeals` | URL | 5 |
| 39 | `MI` | LOCATION | 5 |
| 40 | `49503` | ZIP_CODE | 5 |
| 41 | `(800) 555-1234` | US_PHONE_NUMBER | 5 |
| 42 | `www.healthguardinsurance.com` | URL | 5 |
| 43 | `www.healthguardinsurance.com/privacy` | URL | 5 |
| 44 | `(800) 555-1234` | US_PHONE_NUMBER | 5 |

### False positives (49)

| # | value | raw type | canonical | page | conf |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `04/18/1982` | DATE_TIME | DATE | 1 | 0.95 |
| 2 | `Social Security` | ORGANIZATION | ORGANIZATION | 1 | 0.85 |
| 3 | `Westfield` | PERSON | PERSON | 1 | 0.85 |
| 4 | `Horizon Technologies Inc` | ORGANIZATION | ORGANIZATION | 1 | 0.85 |
| 5 | `Last 4` | DATE_TIME | DATE | 1 | 0.85 |
| 6 | `Spouse	09/22/1980` | ORGANIZATION | ORGANIZATION | 1 | 0.85 |
| 7 | `09/22/1980` | DATE_TIME | DATE | 1 | 0.6 |
| 8 | `06/12/2012` | DATE_TIME | DATE | 1 | 0.6 |
| 9 | `11/04/2015` | DATE_TIME | DATE | 1 | 0.6 |
| 10 | `PPO` | ORGANIZATION | ORGANIZATION | 1 | 0.85 |
| 11 | `Cancer` | PERSON | PERSON | 2 | 0.85 |
| 12 | `• Primary` | ORGANIZATION | ORGANIZATION | 2 | 0.85 |
| 13 | `• Urgent` | ORGANIZATION | ORGANIZATION | 2 | 0.85 |
| 14 | `• Outpatient` | ORGANIZATION | ORGANIZATION | 2 | 0.85 |
| 15 | `• Diagnostic` | ORGANIZATION | ORGANIZATION | 2 | 0.85 |
| 16 | `CT` | ORGANIZATION | ORGANIZATION | 2 | 0.85 |
| 17 | `PET` | ORGANIZATION | ORGANIZATION | 2 | 0.85 |
| 18 | `• Outpatient` | ORGANIZATION | ORGANIZATION | 2 | 0.85 |
| 19 | `• Substance` | ORGANIZATION | ORGANIZATION | 3 | 0.85 |
| 20 | `• Preferred` | ORGANIZATION | ORGANIZATION | 3 | 0.85 |
| 21 | `• Preferred` | ORGANIZATION | ORGANIZATION | 3 | 0.85 |
| 22 | `• Eye` | ORGANIZATION | ORGANIZATION | 3 | 0.85 |
| 23 | `• Contact` | ORGANIZATION | ORGANIZATION | 3 | 0.85 |
| 24 | `• Preventive` | ORGANIZATION | ORGANIZATION | 3 | 0.85 |
| 25 | `• Major` | ORGANIZATION | ORGANIZATION | 3 | 0.85 |
| 26 | `• Seasonal` | ORGANIZATION | ORGANIZATION | 3 | 0.85 |
| 27 | `02/28/2022` | ORGANIZATION | ORGANIZATION | 4 | 0.85 |
| 28 | `• Outpatient` | ORGANIZATION | ORGANIZATION | 4 | 0.85 |
| 29 | `• Advanced` | ORGANIZATION | ORGANIZATION | 4 | 0.85 |
| 30 | `CT` | ORGANIZATION | ORGANIZATION | 4 | 0.85 |
| 31 | `PET` | ORGANIZATION | ORGANIZATION | 4 | 0.85 |
| 32 | `• Durable` | ORGANIZATION | ORGANIZATION | 4 | 0.85 |
| 33 | `• Home` | ORGANIZATION | ORGANIZATION | 4 | 0.85 |
| 34 | `EXCLUSIONS` | ORGANIZATION | ORGANIZATION | 4 | 0.85 |
| 35 | `• Cosmetic` | ORGANIZATION | ORGANIZATION | 4 | 0.85 |
| 36 | `• Services` | ORGANIZATION | ORGANIZATION | 4 | 0.85 |
| 37 | `the United States` | LOCATION | LOCATION | 4 | 0.85 |
| 38 | `Submit` | ORGANIZATION | ORGANIZATION | 4 | 0.85 |
| 39 | `HealthGuard Insurance Company` | ORGANIZATION | ORGANIZATION | 4 | 0.85 |
| 40 | `APPEALS` | ORGANIZATION | ORGANIZATION | 5 | 0.85 |
| 41 | `GRIEVANCES` | ORGANIZATION | ORGANIZATION | 5 | 0.85 |
| 42 | `First Level Appeal` | ORGANIZATION | ORGANIZATION | 5 | 0.85 |
| 43 | `HealthGuard Insurance Company` | ORGANIZATION | ORGANIZATION | 5 | 0.85 |
| 44 | `PLAN ADMINISTRATOR
HealthGuard Insurance Company` | ORGANIZATION | ORGANIZATION | 5 | 0.85 |
| 45 | `8:00 AM - 8:00 PM EST` | DATE_TIME | DATE | 5 | 0.85 |
| 46 | `PM EST

IMPORTANT NOTICES
NOTICE OF PRIVACY PRACTICES
HealthGuard Insurance Company` | ORGANIZATION | ORGANIZATION | 5 | 0.85 |
| 47 | `Privacy Practices` | ORGANIZATION | ORGANIZATION | 5 | 0.85 |
| 48 | `555-1234` | DATE_TIME | DATE | 5 | 0.85 |
| 49 | `HealthGuard` | ORGANIZATION | ORGANIZATION | 6 | 0.85 |

---

## MedSpaCy

- Mode: `medspacy_target_matcher` | predictions: 7
- Availability error: None
- Run error: None

| Metric | All conf | >= 0.80 |
| :--- | :--- | :--- |
| True positives | 4 | 4 |
| False positives | 3 | 3 |
| False negatives | 62 | 62 |
| Precision | 0.571 | 0.571 |
| Recall | 0.061 | 0.061 |
| F1 | 0.110 | 0.110 |

### False negatives (62)

| # | value | type | page |
| :--- | :--- | :--- | :--- |
| 1 | `HIP-2024-45871239` | POLICY_NUMBER | 1 |
| 2 | `Jane R. Smith` | PERSON | 1 |
| 3 | `04/18/1982` | DATE_OF_BIRTH | 1 |
| 4 | `XXX-XX-7890` | SSN | 1 |
| 5 | `123 Maple Avenue, Apt 4B` | ADDRESS | 1 |
| 6 | `Westfield` | LOCATION | 1 |
| 7 | `MI` | LOCATION | 1 |
| 8 | `48185` | ZIP_CODE | 1 |
| 9 | `(313) 555-7842` | US_PHONE_NUMBER | 1 |
| 10 | `jsmith@emailexample.com` | EMAIL | 1 |
| 11 | `Horizon Technologies Inc.` | ORGANIZATION | 1 |
| 12 | `HTI-24680` | GROUP_NUMBER | 1 |
| 13 | `Robert Smith` | PERSON | 1 |
| 14 | `09/22/1980` | DATE_OF_BIRTH | 1 |
| 15 | `XXX-XX-2468` | SSN | 1 |
| 16 | `Emma Smith` | PERSON | 1 |
| 17 | `06/12/2012` | DATE_OF_BIRTH | 1 |
| 18 | `XXX-XX-3579` | SSN | 1 |
| 19 | `Noah Smith` | PERSON | 1 |
| 20 | `11/04/2015` | DATE_OF_BIRTH | 1 |
| 21 | `XXX-XX-1357` | SSN | 1 |
| 22 | `06/01/2024` | DATE | 1 |
| 23 | `05/31/2025` | DATE | 1 |
| 24 | `03/15/2019` | DATE | 3 |
| 25 | `07/10/2021` | DATE | 3 |
| 26 | `Seasonal allergies` | ALLERGY | 3 |
| 27 | `10mg` | DOSAGE | 4 |
| 28 | `500mg` | DOSAGE | 4 |
| 29 | `Cetirizine` | MEDICATION | 4 |
| 30 | `10mg` | DOSAGE | 4 |
| 31 | `Colonoscopy` | PROCEDURE | 4 |
| 32 | `10/12/2023` | DATE | 4 |
| 33 | `Right knee arthroscopy` | PROCEDURE | 4 |
| 34 | `02/28/2022` | DATE | 4 |
| 35 | `HealthGuard Insurance Company` | ORGANIZATION | 4 |
| 36 | `P.O. Box 45678` | ADDRESS | 5 |
| 37 | `Grand Rapids` | LOCATION | 5 |
| 38 | `MI` | LOCATION | 5 |
| 39 | `49501` | ZIP_CODE | 5 |
| 40 | `(800) 555-2468` | US_PHONE_NUMBER | 5 |
| 41 | `(800) 555-3579` | US_PHONE_NUMBER | 5 |
| 42 | `www.healthguardinsurance.com/claims` | URL | 5 |
| 43 | `HealthGuard Insurance Company` | ORGANIZATION | 5 |
| 44 | `P.O. Box 87654` | ADDRESS | 5 |
| 45 | `Grand Rapids` | LOCATION | 5 |
| 46 | `MI` | LOCATION | 5 |
| 47 | `49501` | ZIP_CODE | 5 |
| 48 | `(800) 555-9876` | US_PHONE_NUMBER | 5 |
| 49 | `(800) 555-8765` | US_PHONE_NUMBER | 5 |
| 50 | `www.healthguardinsurance.com/appeals` | URL | 5 |
| 51 | `HealthGuard Insurance Company` | ORGANIZATION | 5 |
| 52 | `789 Insurance Avenue` | ADDRESS | 5 |
| 53 | `Grand Rapids` | LOCATION | 5 |
| 54 | `MI` | LOCATION | 5 |
| 55 | `49503` | ZIP_CODE | 5 |
| 56 | `(800) 555-1234` | US_PHONE_NUMBER | 5 |
| 57 | `www.healthguardinsurance.com` | URL | 5 |
| 58 | `HealthGuard Insurance Company` | ORGANIZATION | 5 |
| 59 | `www.healthguardinsurance.com/privacy` | URL | 5 |
| 60 | `(800) 555-1234` | US_PHONE_NUMBER | 5 |
| 61 | `Michael J. Williams` | PERSON | 6 |
| 62 | `06/01/2024` | DATE | 6 |

### False positives (3)

| # | value | raw type | canonical | page | conf |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `MRI` | PROCEDURE | PROCEDURE | 2 | 0.85 |
| 2 | `MRI` | PROCEDURE | PROCEDURE | 4 | 0.85 |
| 3 | `CT scan` | PROCEDURE | PROCEDURE | 4 | 0.85 |

---

## GLiNER

- Mode: `model` | predictions: 2
- Availability error: None
- Run error: None

| Metric | All conf | >= 0.80 |
| :--- | :--- | :--- |
| True positives | 2 | 0 |
| False positives | 0 | 0 |
| False negatives | 64 | 66 |
| Precision | 1.000 | 0.000 |
| Recall | 0.030 | 0.000 |
| F1 | 0.059 | 0.000 |

### False negatives (64)

| # | value | type | page |
| :--- | :--- | :--- | :--- |
| 1 | `HIP-2024-45871239` | POLICY_NUMBER | 1 |
| 2 | `Jane R. Smith` | PERSON | 1 |
| 3 | `04/18/1982` | DATE_OF_BIRTH | 1 |
| 4 | `XXX-XX-7890` | SSN | 1 |
| 5 | `123 Maple Avenue, Apt 4B` | ADDRESS | 1 |
| 6 | `Westfield` | LOCATION | 1 |
| 7 | `MI` | LOCATION | 1 |
| 8 | `48185` | ZIP_CODE | 1 |
| 9 | `(313) 555-7842` | US_PHONE_NUMBER | 1 |
| 10 | `jsmith@emailexample.com` | EMAIL | 1 |
| 11 | `Horizon Technologies Inc.` | ORGANIZATION | 1 |
| 12 | `HTI-24680` | GROUP_NUMBER | 1 |
| 13 | `Robert Smith` | PERSON | 1 |
| 14 | `09/22/1980` | DATE_OF_BIRTH | 1 |
| 15 | `XXX-XX-2468` | SSN | 1 |
| 16 | `06/12/2012` | DATE_OF_BIRTH | 1 |
| 17 | `XXX-XX-3579` | SSN | 1 |
| 18 | `11/04/2015` | DATE_OF_BIRTH | 1 |
| 19 | `XXX-XX-1357` | SSN | 1 |
| 20 | `06/01/2024` | DATE | 1 |
| 21 | `05/31/2025` | DATE | 1 |
| 22 | `Hypertension` | DISEASE | 3 |
| 23 | `03/15/2019` | DATE | 3 |
| 24 | `Type 2 Diabetes` | DISEASE | 3 |
| 25 | `07/10/2021` | DATE | 3 |
| 26 | `Seasonal allergies` | ALLERGY | 3 |
| 27 | `Lisinopril` | MEDICATION | 4 |
| 28 | `10mg` | DOSAGE | 4 |
| 29 | `Metformin` | MEDICATION | 4 |
| 30 | `500mg` | DOSAGE | 4 |
| 31 | `Cetirizine` | MEDICATION | 4 |
| 32 | `10mg` | DOSAGE | 4 |
| 33 | `Colonoscopy` | PROCEDURE | 4 |
| 34 | `10/12/2023` | DATE | 4 |
| 35 | `Right knee arthroscopy` | PROCEDURE | 4 |
| 36 | `02/28/2022` | DATE | 4 |
| 37 | `HealthGuard Insurance Company` | ORGANIZATION | 4 |
| 38 | `P.O. Box 45678` | ADDRESS | 5 |
| 39 | `Grand Rapids` | LOCATION | 5 |
| 40 | `MI` | LOCATION | 5 |
| 41 | `49501` | ZIP_CODE | 5 |
| 42 | `(800) 555-2468` | US_PHONE_NUMBER | 5 |
| 43 | `(800) 555-3579` | US_PHONE_NUMBER | 5 |
| 44 | `www.healthguardinsurance.com/claims` | URL | 5 |
| 45 | `HealthGuard Insurance Company` | ORGANIZATION | 5 |
| 46 | `P.O. Box 87654` | ADDRESS | 5 |
| 47 | `Grand Rapids` | LOCATION | 5 |
| 48 | `MI` | LOCATION | 5 |
| 49 | `49501` | ZIP_CODE | 5 |
| 50 | `(800) 555-9876` | US_PHONE_NUMBER | 5 |
| 51 | `(800) 555-8765` | US_PHONE_NUMBER | 5 |
| 52 | `www.healthguardinsurance.com/appeals` | URL | 5 |
| 53 | `HealthGuard Insurance Company` | ORGANIZATION | 5 |
| 54 | `789 Insurance Avenue` | ADDRESS | 5 |
| 55 | `Grand Rapids` | LOCATION | 5 |
| 56 | `MI` | LOCATION | 5 |
| 57 | `49503` | ZIP_CODE | 5 |
| 58 | `(800) 555-1234` | US_PHONE_NUMBER | 5 |
| 59 | `www.healthguardinsurance.com` | URL | 5 |
| 60 | `HealthGuard Insurance Company` | ORGANIZATION | 5 |
| 61 | `www.healthguardinsurance.com/privacy` | URL | 5 |
| 62 | `(800) 555-1234` | US_PHONE_NUMBER | 5 |
| 63 | `Michael J. Williams` | PERSON | 6 |
| 64 | `06/01/2024` | DATE | 6 |

### False positives (0)

| # | value | raw type | canonical | page | conf |
| :--- | :--- | :--- | :--- | :--- | :--- |

---

## Qwen3:4b

- Mode: `ollama_qwen3_4b` | predictions: 21
- Availability error: None
- Run error: None

| Metric | All conf | >= 0.80 |
| :--- | :--- | :--- |
| True positives | 21 | 21 |
| False positives | 0 | 0 |
| False negatives | 45 | 45 |
| Precision | 1.000 | 1.000 |
| Recall | 0.318 | 0.318 |
| F1 | 0.483 | 0.483 |

### False negatives (45)

| # | value | type | page |
| :--- | :--- | :--- | :--- |
| 1 | `HIP-2024-45871239` | POLICY_NUMBER | 1 |
| 2 | `Westfield` | LOCATION | 1 |
| 3 | `MI` | LOCATION | 1 |
| 4 | `XXX-XX-2468` | SSN | 1 |
| 5 | `XXX-XX-3579` | SSN | 1 |
| 6 | `XXX-XX-1357` | SSN | 1 |
| 7 | `Hypertension` | DISEASE | 3 |
| 8 | `Type 2 Diabetes` | DISEASE | 3 |
| 9 | `Seasonal allergies` | ALLERGY | 3 |
| 10 | `Lisinopril` | MEDICATION | 4 |
| 11 | `10mg` | DOSAGE | 4 |
| 12 | `Metformin` | MEDICATION | 4 |
| 13 | `500mg` | DOSAGE | 4 |
| 14 | `Cetirizine` | MEDICATION | 4 |
| 15 | `10mg` | DOSAGE | 4 |
| 16 | `Colonoscopy` | PROCEDURE | 4 |
| 17 | `Right knee arthroscopy` | PROCEDURE | 4 |
| 18 | `HealthGuard Insurance Company` | ORGANIZATION | 4 |
| 19 | `P.O. Box 45678` | ADDRESS | 5 |
| 20 | `Grand Rapids` | LOCATION | 5 |
| 21 | `MI` | LOCATION | 5 |
| 22 | `49501` | ZIP_CODE | 5 |
| 23 | `(800) 555-2468` | US_PHONE_NUMBER | 5 |
| 24 | `(800) 555-3579` | US_PHONE_NUMBER | 5 |
| 25 | `www.healthguardinsurance.com/claims` | URL | 5 |
| 26 | `HealthGuard Insurance Company` | ORGANIZATION | 5 |
| 27 | `P.O. Box 87654` | ADDRESS | 5 |
| 28 | `Grand Rapids` | LOCATION | 5 |
| 29 | `MI` | LOCATION | 5 |
| 30 | `49501` | ZIP_CODE | 5 |
| 31 | `(800) 555-9876` | US_PHONE_NUMBER | 5 |
| 32 | `(800) 555-8765` | US_PHONE_NUMBER | 5 |
| 33 | `www.healthguardinsurance.com/appeals` | URL | 5 |
| 34 | `HealthGuard Insurance Company` | ORGANIZATION | 5 |
| 35 | `789 Insurance Avenue` | ADDRESS | 5 |
| 36 | `Grand Rapids` | LOCATION | 5 |
| 37 | `MI` | LOCATION | 5 |
| 38 | `49503` | ZIP_CODE | 5 |
| 39 | `(800) 555-1234` | US_PHONE_NUMBER | 5 |
| 40 | `www.healthguardinsurance.com` | URL | 5 |
| 41 | `HealthGuard Insurance Company` | ORGANIZATION | 5 |
| 42 | `www.healthguardinsurance.com/privacy` | URL | 5 |
| 43 | `(800) 555-1234` | US_PHONE_NUMBER | 5 |
| 44 | `Michael J. Williams` | PERSON | 6 |
| 45 | `06/01/2024` | DATE | 6 |

### False positives (0)

| # | value | raw type | canonical | page | conf |
| :--- | :--- | :--- | :--- | :--- | :--- |

---
