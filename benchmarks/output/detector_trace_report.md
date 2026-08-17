# Trace: previous report entities -> raw detector output

| Attribution | All report entities | Suspicious only |
| :--- | :--- | :--- |
| detector_origin | 78 | 29 |
| reclass_origin | 1 | 1 |
| partial_span | 0 | 0 |
| downstream_artifact | 0 | 0 |

Raw predictions dropped downstream: **25**

## Suspicious entities detail

- **'Social Security'** (report ORGANIZATION, p1, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION 'Social Security' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'Spouse\t09/22/1980'** (report ORGANIZATION, p1, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION 'Spouse\t09/22/1980' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'Noah Smith\tChild'** (report PERSON, p1, detector_field=Presidio) -> **detector_origin**
  - raw: presidio PERSON 'Noah Smith\tChild' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'XXX-XX-1357'** (report INSURANCE_ID, p1, detector_field=Regex) -> **detector_origin**
  - raw: regex INSURANCE_ID 'XXX-XX-1357' conf=1.0 overlap=1.0 value_match=True type_match=True
- **'Cancer'** (report PERSON, p2, detector_field=Presidio) -> **detector_origin**
  - raw: presidio PERSON 'Cancer' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'• Primary'** (report ORGANIZATION, p2, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION '• Primary' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'• Urgent'** (report ORGANIZATION, p2, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION '• Urgent' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'• Outpatient'** (report ORGANIZATION, p2, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION '• Outpatient' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'• Diagnostic'** (report ORGANIZATION, p2, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION '• Diagnostic' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'CT'** (report ORGANIZATION, p2, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION 'CT' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'PET'** (report ORGANIZATION, p2, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION 'PET' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'• Outpatient'** (report ORGANIZATION, p2, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION '• Outpatient' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'02/28/2022'** (report ORGANIZATION, p4, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION '02/28/2022' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'• Outpatient'** (report ORGANIZATION, p4, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION '• Outpatient' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'• Advanced'** (report ORGANIZATION, p4, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION '• Advanced' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'CT scan'** (report PROCEDURE, p4, detector_field=MedSpaCy) -> **detector_origin**
  - raw: medspacy PROCEDURE 'CT scan' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'PET'** (report ORGANIZATION, p4, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION 'PET' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'• Durable'** (report ORGANIZATION, p4, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION '• Durable' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'• Home'** (report ORGANIZATION, p4, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION '• Home' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'EXCLUSIONS'** (report ORGANIZATION, p4, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION 'EXCLUSIONS' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'• Cosmetic'** (report ORGANIZATION, p4, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION '• Cosmetic' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'• Services'** (report ORGANIZATION, p4, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION '• Services' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'the United States'** (report LOCATION, p4, detector_field=Presidio) -> **detector_origin**
  - raw: presidio LOCATION 'the United States' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'Submit'** (report ORGANIZATION, p4, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION 'Submit' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'P.O. Box 45678'** (report PERSON, p5, detector_field=Presidio) -> **reclass_origin**
  - raw: regex PO_BOX 'P.O. Box 45678' conf=1.0 overlap=1.0 value_match=True type_match=False
- **'APPEALS'** (report ORGANIZATION, p5, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION 'APPEALS' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'GRIEVANCES'** (report ORGANIZATION, p5, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION 'GRIEVANCES' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'First Level Appeal'** (report ORGANIZATION, p5, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION 'First Level Appeal' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'8:00 AM'** (report DATE_TIME, p5, detector_field=Regex) -> **detector_origin**
  - raw: regex DATE_TIME '8:00 AM' conf=0.85 overlap=1.0 value_match=True type_match=True
- **'Privacy Practices'** (report ORGANIZATION, p5, detector_field=Presidio) -> **detector_origin**
  - raw: presidio ORGANIZATION 'Privacy Practices' conf=0.85 overlap=1.0 value_match=True type_match=True

## Dropped raw predictions (present raw, absent in report)

| # | detector | raw type | value | page | conf |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | presidio | DATE_TIME | `Last 4` | 1 | 0.85 |
| 2 | presidio | ORGANIZATION | `PPO` | 1 | 0.85 |
| 3 | presidio | ORGANIZATION | `• Substance` | 3 | 0.85 |
| 4 | presidio | ORGANIZATION | `• Preferred` | 3 | 0.85 |
| 5 | presidio | ORGANIZATION | `• Preferred` | 3 | 0.85 |
| 6 | presidio | ORGANIZATION | `• Eye` | 3 | 0.85 |
| 7 | presidio | ORGANIZATION | `• Contact` | 3 | 0.85 |
| 8 | presidio | ORGANIZATION | `• Preventive` | 3 | 0.85 |
| 9 | presidio | ORGANIZATION | `• Major` | 3 | 0.85 |
| 10 | presidio | ORGANIZATION | `• Seasonal` | 3 | 0.85 |
| 11 | presidio | ORGANIZATION | `CT` | 4 | 0.85 |
| 12 | presidio | ORGANIZATION | `HealthGuard Insurance Company
Claims Department` | 4 | 0.85 |
| 13 | presidio | ORGANIZATION | `HealthGuard Insurance Company
Appeals Department` | 5 | 0.85 |
| 14 | presidio | ORGANIZATION | `HealthGuard Insurance Company
Corporate Headquarters` | 5 | 0.85 |
| 15 | presidio | DATE_TIME | `8:00 AM - 8:00 PM EST` | 5 | 0.85 |
| 16 | presidio | ORGANIZATION | `HealthGuard Insurance Company` | 5 | 0.85 |
| 17 | presidio | ORGANIZATION | `HealthGuard Insurance Company` | 4 | 0.85 |
| 18 | presidio | ORGANIZATION | `HealthGuard Insurance Company` | 5 | 0.85 |
| 19 | presidio | ORGANIZATION | `PLAN ADMINISTRATOR
HealthGuard Insurance Company` | 5 | 0.85 |
| 20 | presidio | ORGANIZATION | `PM EST

IMPORTANT NOTICES
NOTICE OF PRIVACY PRACTICES
HealthGuard Insurance Company` | 5 | 0.85 |
| 21 | qwen | SSN | `XXX-XX-7890` | 1 | 0.95 |
| 22 | regex | INSURANCE_PROVIDER | `HealthGuard Insurance Company` | 4 | 1.0 |
| 23 | regex | INSURANCE_PROVIDER | `HealthGuard Insurance Company` | 5 | 1.0 |
| 24 | regex | INSURANCE_PROVIDER | `HealthGuard Insurance Company` | 5 | 1.0 |
| 25 | regex | DATE_TIME | `8:00 PM` | 5 | 0.85 |
