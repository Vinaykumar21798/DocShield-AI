# PII/PHI entity research - accepted across GDPR/OECD/NIST/HIPAA-style privacy programs

PII = identifies or can identify a natural person.
PHI = health-related personal data, or identifiable health/payment/care data.

## Generic PII Entity Catalog

**Identity and demographics**:
full_name, first_name, middle_name, last_name, maiden_name, alias, initials, handwritten_signature, digital_signature, photograph, facial_image, date_of_birth, place_of_birth, age, age_over_89, gender, sex, nationality, citizenship, marital_status, family_member_name, mother_maiden_name, dependent_name, household_member_name

**Contact and location**:
home_address, street_address, apartment_unit, city, county, district, state_province, postal_code, country_of_residence, geolocation, GPS_coordinates, latitude_longitude, personal_email, personal_phone, mobile_number, fax_number, emergency_contact_name, emergency_contact_phone

**Government, civil, tax IDs**:
SSN, national_id, identity_card_number, tax_id, taxpayer_identification_number, passport_number, visa_number, immigration_number, resident_permit_number, work_permit_number, driver_license_number, voter_id, birth_certificate_number, marriage_certificate_number, death_certificate_number, military_id, social_insurance_number, aadhaar_number, pan_number, national_insurance_number, medicare_number, government_benefit_id, certificate_license_number, professional_license_number

**Financial and payment**:
bank_account_number, IBAN, routing_number, credit_card_number, debit_card_number, payment_card_expiry, card_security_code, payment_token, UPI_ID, PayPal_account, mobile_wallet_id, crypto_wallet_address, loan_account_number, mortgage_account_number, brokerage_account_number, insurance_policy_number, pension_account_number, tax_return_data, income, salary, credit_score, transaction_history

**Digital and device identifiers**:
username, login_id, customer_id, account_id, membership_number, loyalty_number, employee_id, student_id, patient_id, IP_address, MAC_address, device_id, IMEI, IMSI, SIM_serial_number, cookie_id, advertising_id, browser_fingerprint, online_identifier, social_media_handle, profile_url, URL, password, security_question_answer

**Biometric, genetic, sensitive personal data**:
fingerprint, voiceprint, iris_scan, retina_scan, facial_template, palmprint, hand_geometry, gait_pattern, keystroke_pattern, DNA_profile, genetic_marker, race_ethnicity, religious_belief, political_opinion, trade_union_membership, sexual_orientation, sex_life_information, disability_status, criminal_record, court_case_number

**Employment, education, travel, vehicle**:
work_email, work_phone, employer_name, job_title, payroll_id, personnel_file_number, performance_review, background_check_record, resume_cv, education_record, student_record, grades, transcript, vehicle_license_plate, VIN, boarding_pass_number, ticket_number, travel_itinerary

## Generic PHI / Health Data Entity Catalog

**Healthcare identifiers**:
patient_name, patient_id, medical_record_number, MRN, health_plan_beneficiary_number, medical_account_number, claim_number, encounter_id, visit_id, admission_date, discharge_date, appointment_date, healthcare_invoice, explanation_of_benefits

**Clinical conditions**:
diagnosis, ICD10_code, ICD9_code, SNOMED_code, chief_complaint, symptom, disease, medical_condition, injury, disability, pregnancy_status, mental_health_condition, substance_use_history, family_medical_history, allergy, allergic_reaction

**Medication and treatment**:
medication_name, prescription_number, dosage, administration_route, medication_schedule, treatment_plan, care_plan, procedure_name, CPT_code, HCPCS_code, surgery_history, anesthesia_record, therapy_notes, psychotherapy_notes

**Labs and diagnostics**:
lab_test_name, lab_result, lab_accession_number, specimen_id, pathology_report, radiology_report, xray_result, MRI_result, CT_result, ultrasound_result, biomarker, genetic_test_result, genomic_sequence

**Vitals and measurements**:
vital_sign, blood_pressure, heart_rate, respiratory_rate, body_temperature, oxygen_saturation, blood_glucose, hemoglobin, cholesterol_level, height, weight, BMI

**Public health and status**:
immunization_record, vaccination_status, infection_status, HIV_status, cancer_status, organ_donor_status, transplant_record, death_certificate_medical_cause, autopsy_report

**Healthcare operations**:
clinical_notes, SOAP_notes, discharge_summary, referral_record, consent_form, prior_authorization_number, insurance_member_id, insurance_group_number, billing_record, payment_record, pharmacy_record, prescription_fill_history

**Medical devices and digital health**:
medical_device_identifier, implant_serial_number, donor_id, wearable_health_data, fitness_tracker_health_metric, telehealth_record, patient_portal_username, emergency_contact_in_medical_record

## Important classification note:

A company name, company tax ID, business address, invoice number, or business transaction amount is not always PII.
It becomes PII when it identifies or links to a natural person, sole proprietor, patient, employee, customer, or account holder.

## Sources used:

NIST PII definition:
https://csrc.nist.gov/glossary/term/personally_identifiable_information

OECD personal data definition:
https://legalinstruments.oecd.org/public/doc/114/body-text.en.html

GDPR personal data definition:
https://eur-lex.europa.eu/legal-content/EN-ES/TXT/?uri=CELEX%3A32016R0679

EDPB personal data examples:
https://www.edpb.europa.eu/node/5284_cs

HHS HIPAA PHI/de-identification identifiers:
https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html

ICO health and special category data:
https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/special-category-data/what-is-special-category-data/
