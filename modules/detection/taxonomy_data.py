"""
Auto-generated from PII_PHI_Entity_Policy_Taxonomy_Corrected.xlsx
Defines document-type specific entity policies (MUST_HAVE, NICE_TO_HAVE, DROP),
canonical entity mapping, risk levels, and drop rules.
"""

CANONICAL_ENTITY_MAPPING = {'A/C NO.': 'BANK ACCOUNT NUMBER',
 'AADHAAR': 'AADHAAR NUMBER (INDIA)',
 'AADHAAR NUMBER (INDIA)': 'AADHAAR NUMBER (INDIA)',
 'AADHAAR_NUMBER': 'AADHAAR NUMBER (INDIA)',
 'AADHAR NUMBER': 'AADHAAR NUMBER (INDIA)',
 'ABA NUMBER': 'BANK ROUTING / SORT CODE',
 'ACCESS TOKEN / OAUTH TOKEN': 'ACCESS TOKEN / OAUTH TOKEN',
 'ACCESSION NUMBER': 'IMAGING STUDY ID / ACCESSION NUMBER',
 'ACCOMMODATION REQUEST': 'DISABILITY STATUS',
 'ACCOUNT NUMBER': 'BANK ACCOUNT NUMBER',
 'ACCOUNT PASSWORD': 'PASSWORD',
 'ACCOUNT USERNAME': 'USERNAME / LOGIN ID',
 'ADDICTION TREATMENT NOTE': 'SUBSTANCE USE DISORDER TREATMENT INFO',
 'ADDRESS': 'STREET / MAILING ADDRESS',
 'ADMISSION / DISCHARGE / SERVICE DATE': 'ADMISSION / DISCHARGE / SERVICE DATE',
 'ADMISSION DATE': 'ADMISSION / DISCHARGE / SERVICE DATE',
 'AGE 90+': 'AGE OVER 89 (HIPAA SAFE HARBOR THRESHOLD)',
 'AGE >89': 'AGE OVER 89 (HIPAA SAFE HARBOR THRESHOLD)',
 'AGE OVER 89 (HIPAA SAFE HARBOR THRESHOLD)': 'AGE OVER 89 (HIPAA SAFE HARBOR THRESHOLD)',
 'ALLERGIES': 'ALLERGY INFORMATION',
 'ALLERGY': 'ALLERGY INFORMATION',
 'ALLERGY INFORMATION': 'ALLERGY INFORMATION',
 'AMBIGUOUS — RESOLVE BY CONTEXT': 'AMBIGUOUS — RESOLVE BY CONTEXT',
 'ANALYZER ID': 'MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER',
 'ANNUAL COMPENSATION': 'SALARY / COMPENSATION AMOUNT',
 'API KEY': 'API KEY / SECRET KEY',
 'API KEY / SECRET KEY': 'API KEY / SECRET KEY',
 'APPOINTMENT REFERENCE': 'BOOKING REFERENCE NUMBER',
 'APPRAISAL RATING': 'PERFORMANCE RATING / REVIEW CONTENT',
 'ASSESSMENT': 'DIAGNOSIS / MEDICAL CONDITION',
 'ATTENDING PHYSICIAN': 'TREATING PROVIDER NAME / NPI NUMBER',
 'ATTORNEY WORK PRODUCT': 'ATTORNEY-CLIENT PRIVILEGE NOTATION',
 'ATTORNEY-CLIENT PRIVILEGE NOTATION': 'ATTORNEY-CLIENT PRIVILEGE NOTATION',
 'AUTH COOKIE': 'SESSION ID / AUTH COOKIE',
 'BACKGROUND / CRIMINAL BACKGROUND CHECK RESULT': 'BACKGROUND / CRIMINAL BACKGROUND CHECK RESULT',
 'BACKGROUND CHECK REPORT': 'BACKGROUND / CRIMINAL BACKGROUND CHECK RESULT',
 'BACKGROUND SCREENING RESULT': 'BACKGROUND / CRIMINAL BACKGROUND CHECK RESULT',
 'BANK ACCOUNT NUMBER': 'BANK ACCOUNT NUMBER',
 'BANK ROUTING / SORT CODE': 'BANK ROUTING / SORT CODE',
 'BANK_ACCOUNT': 'BANK ACCOUNT NUMBER',
 'BARCODE / QR CODE INTERNAL DOCUMENT ID': 'BARCODE / QR CODE INTERNAL DOCUMENT ID',
 'BARCODE VALUE': 'BARCODE / QR CODE INTERNAL DOCUMENT ID',
 'BEARER TOKEN': 'ACCESS TOKEN / OAUTH TOKEN',
 'BEHAVIORAL HEALTH RECORD': 'MENTAL / BEHAVIORAL HEALTH NOTES',
 'BENEFICIARY NUMBER': 'HEALTH PLAN BENEFICIARY/MEMBER NUMBER',
 'BIC': 'IBAN / SWIFT-BIC CODE',
 'BILL NUMBER': 'INVOICE NUMBER',
 'BILLING ADDRESS': 'STREET / MAILING ADDRESS',
 'BIOMETRIC IDENTIFIER (FINGERPRINT / RETINA / VOICEPRINT)': 'BIOMETRIC IDENTIFIER (FINGERPRINT / RETINA / VOICEPRINT)',
 'BIRTH DATE': 'DATE OF BIRTH',
 'BOILERPLATE / DISCLAIMER TEXT': 'BOILERPLATE / DISCLAIMER TEXT',
 'BOOKING REFERENCE NUMBER': 'BOOKING REFERENCE NUMBER',
 'BREACH INCIDENT DESCRIPTION': 'BREACH INCIDENT DESCRIPTION',
 'BREACH RESPONSE LINE': 'ORGANIZATION CONTACT INFO',
 'BREACHED DATA ELEMENT DESCRIPTION': 'BREACHED DATA ELEMENT DESCRIPTION',
 'BROKERAGE ACCOUNT NUMBER': 'INVESTMENT / BROKERAGE ACCOUNT NUMBER',
 'CARD EXPIRATION DATE': 'CARD EXPIRATION DATE',
 'CARD NUMBER': 'PAYMENT CARD NUMBER (PAN)',
 'CARD PIN': 'PIN / PIN BLOCK',
 'CARD VERIFICATION CODE (CVV/CVC/CID/CAV2)': 'CARD VERIFICATION CODE (CVV/CVC/CID/CAV2)',
 'CARDHOLDER NAME': 'CARDHOLDER NAME',
 'CASE / DOCKET / REFERENCE NUMBER': 'CASE / DOCKET / REFERENCE NUMBER',
 'CASE NUMBER': 'CASE / DOCKET / REFERENCE NUMBER',
 'CAV2': 'CARD VERIFICATION CODE (CVV/CVC/CID/CAV2)',
 'CELL PHONE': 'PHONE NUMBER',
 'CHART NUMBER': 'MEDICAL RECORD NUMBER (MRN)',
 'CID': 'CARD VERIFICATION CODE (CVV/CVC/CID/CAV2)',
 'CITIZEN ID': 'NATIONAL / GOVERNMENT ID NUMBER (GENERIC, NON-US/NON-INDIA)',
 'CLAIM ID': 'MEDICAL CLAIM NUMBER',
 'CLAIM REFERENCE NUMBER': 'MEDICAL CLAIM NUMBER',
 'CLAIM_NUMBER': 'MEDICAL CLAIM NUMBER',
 'CLIENT SECRET': 'API KEY / SECRET KEY',
 'CLINIC': 'COMPANY / EMPLOYER NAME',
 'CLINIC ADDRESS': 'FACILITY ADDRESS',
 'CLINIC DEPARTMENT': 'DEPARTMENT / SPECIALTY NAME',
 'CLINICAL DIAGNOSIS': 'DIAGNOSIS / MEDICAL CONDITION',
 'CLINICAL NOTES / NARRATIVE': 'CLINICAL NOTES / NARRATIVE',
 'CLINICAL_MEASUREMENT': 'LAB TEST RESULT / VALUE',
 'COINSURANCE': 'COST-SHARING AMOUNT',
 'COMPANY / EMPLOYER NAME': 'COMPANY / EMPLOYER NAME',
 'COMPANY NAME': 'COMPANY / EMPLOYER NAME',
 'COMPROMISED INFORMATION DESCRIPTION': 'BREACHED DATA ELEMENT DESCRIPTION',
 'CONDITION': 'DIAGNOSIS / MEDICAL CONDITION',
 'CONFIRMATION NUMBER': 'BOOKING REFERENCE NUMBER',
 'CONTACT NUMBER': 'PHONE NUMBER',
 'CONVICTION RECORD': 'CRIMINAL RECORD / CONVICTION DATA',
 'COPAY': 'COST-SHARING AMOUNT',
 'CORRECTIVE ACTION NOTICE': 'DISCIPLINARY ACTION DETAIL',
 'COST-SHARING AMOUNT': 'COST-SHARING AMOUNT',
 'COUNTRY': 'COUNTRY NAME (GENERIC)',
 'COUNTRY NAME (GENERIC)': 'COUNTRY NAME (GENERIC)',
 'COURT / JURISDICTION NAME': 'COURT / JURISDICTION NAME',
 'COURT NAME': 'COURT / JURISDICTION NAME',
 'COVERAGE DATE': 'COVERAGE DATE',
 'COVERAGE EFFECTIVE DATE': 'COVERAGE DATE',
 'COVERAGE EXAMPLE SCENARIO': 'COVERAGE EXAMPLE SCENARIO',
 'COVERAGE TERMINATION DATE': 'COVERAGE DATE',
 'COVERAGE TIER': 'PLAN NAME',
 'CPT CODE': 'PROCEDURE CODE / DESCRIPTION',
 'CREDIT CARD NUMBER': 'PAYMENT CARD NUMBER (PAN)',
 'CREDIT MONITORING CODE': 'ENROLLMENT/ACTIVATION CODE',
 'CREDIT RATING': 'CREDIT SCORE',
 'CREDIT SCORE': 'CREDIT SCORE',
 'CREDIT_CARD': 'PAYMENT CARD NUMBER (PAN)',
 'CRIMINAL HISTORY': 'CRIMINAL RECORD / CONVICTION DATA',
 'CRIMINAL RECORD / CONVICTION DATA': 'CRIMINAL RECORD / CONVICTION DATA',
 'CT NUMBER / IMAGING TECHNICAL PARAMETER': 'CT NUMBER / IMAGING TECHNICAL PARAMETER',
 'CT VALUE': 'CT NUMBER / IMAGING TECHNICAL PARAMETER',
 'CUSTOMER NAME': 'FULL NAME / PERSON NAME',
 'CUSTOMER SERVICE NUMBER (ORGANIZATION)': 'ORGANIZATION CONTACT INFO',
 'CVC': 'CARD VERIFICATION CODE (CVV/CVC/CID/CAV2)',
 'CVE / VULNERABILITY REFERENCE': 'CVE / VULNERABILITY REFERENCE',
 'CVE ID': 'CVE / VULNERABILITY REFERENCE',
 'CVV': 'CARD VERIFICATION CODE (CVV/CVC/CID/CAV2)',
 'CVV FAMILY': 'CARD VERIFICATION CODE (CVV/CVC/CID/CAV2)',
 'CVV2': 'CARD VERIFICATION CODE (CVV/CVC/CID/CAV2)',
 'DATE': 'ADMISSION / DISCHARGE / SERVICE DATE',
 'DATE OF BIRTH': 'DATE OF BIRTH',
 'DATE OF SERVICE': 'ADMISSION / DISCHARGE / SERVICE DATE',
 'DATE_OF_BIRTH': 'DATE OF BIRTH',
 'DATE_TIME': 'ADMISSION / DISCHARGE / SERVICE DATE',
 'DEBIT CARD NUMBER': 'PAYMENT CARD NUMBER (PAN)',
 'DEDUCTIBLE': 'COST-SHARING AMOUNT',
 'DEPARTMENT / SPECIALTY NAME': 'DEPARTMENT / SPECIALTY NAME',
 'DESIGNATION': 'JOB TITLE',
 'DEVICE ID': 'DEVICE IDENTIFIER / MAC ADDRESS',
 'DEVICE IDENTIFIER / MAC ADDRESS': 'DEVICE IDENTIFIER / MAC ADDRESS',
 'DEVICE SERIAL NUMBER': 'MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER',
 'DIAGNOSIS': 'DIAGNOSIS / MEDICAL CONDITION',
 'DIAGNOSIS / MEDICAL CONDITION': 'DIAGNOSIS / MEDICAL CONDITION',
 'DIGITAL SIGNATURE': 'SIGNATURE',
 'DISABILITY': 'DISABILITY STATUS',
 'DISABILITY STATUS': 'DISABILITY STATUS',
 'DISCHARGE DATE': 'ADMISSION / DISCHARGE / SERVICE DATE',
 'DISCIPLINARY ACTION DETAIL': 'DISCIPLINARY ACTION DETAIL',
 'DISCIPLINARY RECORD': 'DISCIPLINARY ACTION DETAIL',
 'DISEASE': 'DIAGNOSIS / MEDICAL CONDITION',
 'DL NUMBER': "DRIVER'S LICENSE NUMBER",
 'DNA TEST RESULT': 'GENETIC / GENOMIC INFORMATION',
 'DOB': 'DATE OF BIRTH',
 'DOCKET NUMBER': 'CASE / DOCKET / REFERENCE NUMBER',
 'DOCTOR': 'TREATING PROVIDER NAME / NPI NUMBER',
 'DOCUMENT CREATION/PRINT DATE (NON-INDIVIDUAL)': 'DOCUMENT CREATION/PRINT DATE (NON-INDIVIDUAL)',
 'DOSAGE': 'MEDICATION / PRESCRIPTION DETAIL',
 "DRIVER'S LICENSE NUMBER": "DRIVER'S LICENSE NUMBER",
 'DRIVING LICENSE NUMBER': "DRIVER'S LICENSE NUMBER",
 'DRIVING_LICENSE': "DRIVER'S LICENSE NUMBER",
 'DRUG NAME': 'MEDICATION / PRESCRIPTION DETAIL',
 'E-MAIL': 'EMAIL ADDRESS',
 'E-SIGNATURE': 'SIGNATURE',
 'EIN': 'US TAX ID (EIN / ITIN)',
 'EMAIL': 'EMAIL ADDRESS',
 'EMAIL ADDRESS': 'EMAIL ADDRESS',
 'EMAIL ID': 'EMAIL ADDRESS',
 'EMPLOYEE ID NUMBER': 'EMPLOYEE ID NUMBER',
 'EMPLOYEE NAME': 'FULL NAME / PERSON NAME',
 'EMPLOYEE NUMBER': 'EMPLOYEE ID NUMBER',
 'EMPLOYER': 'COMPANY / EMPLOYER NAME',
 'ENROLLMENT DATE': 'COVERAGE DATE',
 'ENROLLMENT/ACTIVATION CODE': 'ENROLLMENT/ACTIVATION CODE',
 'ETHNICITY': 'RACIAL OR ETHNIC ORIGIN DATA',
 'EXP DATE': 'CARD EXPIRATION DATE',
 'EXPIRY DATE': 'CARD EXPIRATION DATE',
 'FACIAL IMAGE': 'PHOTOGRAPH / FACIAL IMAGE',
 'FACILITY ADDRESS': 'FACILITY ADDRESS',
 'FEDERAL TAX ID': 'US TAX ID (EIN / ITIN)',
 'FICO SCORE': 'CREDIT SCORE',
 'FIELD LABEL': 'FORM / TEMPLATE FIELD LABEL',
 'FINGERPRINT': 'BIOMETRIC IDENTIFIER (FINGERPRINT / RETINA / VOICEPRINT)',
 'FORM / TEMPLATE FIELD LABEL': 'FORM / TEMPLATE FIELD LABEL',
 'FORM HEADER LABEL': 'FORM / TEMPLATE FIELD LABEL',
 'FULL LEGAL NAME': 'FULL NAME / PERSON NAME',
 'FULL MAGNETIC STRIPE / TRACK DATA': 'FULL MAGNETIC STRIPE / TRACK DATA',
 'FULL NAME / PERSON NAME': 'FULL NAME / PERSON NAME',
 'GENDER IDENTITY': 'SEXUAL ORIENTATION / GENDER IDENTITY',
 'GENERATED ON': 'DOCUMENT CREATION/PRINT DATE (NON-INDIVIDUAL)',
 'GENETIC / GENOMIC INFORMATION': 'GENETIC / GENOMIC INFORMATION',
 'GENETIC TEST RESULT': 'GENETIC / GENOMIC INFORMATION',
 'GENOMIC DATA': 'GENETIC / GENOMIC INFORMATION',
 'GEOGRAPHIC SUBDIVISION': 'GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)',
 'GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)': 'GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)',
 'GOVERNMENT ID NUMBER': 'NATIONAL / GOVERNMENT ID NUMBER (GENERIC, NON-US/NON-INDIA)',
 'GROSS SALARY': 'SALARY / COMPENSATION AMOUNT',
 'GROUP / POLICY NUMBER': 'GROUP / POLICY NUMBER',
 'GROUP NUMBER': 'GROUP / POLICY NUMBER',
 'GROUP/PLAN NUMBER': 'GROUP / POLICY NUMBER',
 'GROUP_NUMBER': 'GROUP / POLICY NUMBER',
 'HEALTH INSURANCE POLICY NUMBER': 'HEALTH INSURANCE POLICY NUMBER',
 'HEALTH PLAN BENEFICIARY/MEMBER NUMBER': 'HEALTH PLAN BENEFICIARY/MEMBER NUMBER',
 'HEALTH PLAN ID': 'HEALTH INSURANCE POLICY NUMBER',
 'HEALTHCARE_STAFF': 'TREATING PROVIDER NAME / NPI NUMBER',
 'HIV / STI STATUS': 'HIV / STI STATUS',
 'HIV STATUS': 'HIV / STI STATUS',
 'HOLDINGS': 'SECURITIES / PORTFOLIO HOLDINGS DETAIL',
 'HOME ADDRESS': 'STREET / MAILING ADDRESS',
 'HOSPITAL': 'COMPANY / EMPLOYER NAME',
 'HOST NAME': 'INTERNAL SERVER / HOSTNAME',
 'HOUNSFIELD UNIT': 'CT NUMBER / IMAGING TECHNICAL PARAMETER',
 'IBAN': 'IBAN / SWIFT-BIC CODE',
 'IBAN / SWIFT-BIC CODE': 'IBAN / SWIFT-BIC CODE',
 'ICD CODE': 'DIAGNOSIS / MEDICAL CONDITION',
 'ID PHOTO': 'PHOTOGRAPH / FACIAL IMAGE',
 'IDENTITY PROTECTION ACTIVATION CODE': 'ENROLLMENT/ACTIVATION CODE',
 'IFSC CODE': 'BANK ROUTING / SORT CODE',
 'ILLUSTRATIVE EXAMPLE': 'COVERAGE EXAMPLE SCENARIO',
 'IMAGING STUDY ID / ACCESSION NUMBER': 'IMAGING STUDY ID / ACCESSION NUMBER',
 'IMEI': 'DEVICE IDENTIFIER / MAC ADDRESS',
 'IMMIGRATION CASE NUMBER': 'VISA / IMMIGRATION DOCUMENT NUMBER',
 'IMMUNIZATION HISTORY': 'IMMUNIZATION RECORD',
 'IMMUNIZATION RECORD': 'IMMUNIZATION RECORD',
 'INCIDENT SUMMARY': 'BREACH INCIDENT DESCRIPTION',
 'INCOME TAX PAN': 'PERMANENT ACCOUNT NUMBER — INCOME TAX (INDIA)',
 'INSURANCE MEMBER NUMBER': 'HEALTH PLAN BENEFICIARY/MEMBER NUMBER',
 'INSURED NAME': 'FULL NAME / PERSON NAME',
 'INTERNAL IP': 'INTERNAL SERVER / HOSTNAME',
 'INTERNAL SERVER / HOSTNAME': 'INTERNAL SERVER / HOSTNAME',
 'INVESTMENT / BROKERAGE ACCOUNT NUMBER': 'INVESTMENT / BROKERAGE ACCOUNT NUMBER',
 'INVESTMENT ACCOUNT NO.': 'INVESTMENT / BROKERAGE ACCOUNT NUMBER',
 'INVOICE ID': 'INVOICE NUMBER',
 'INVOICE NUMBER': 'INVOICE NUMBER',
 'IP': 'IP ADDRESS',
 'IP ADDRESS': 'IP ADDRESS',
 'IPV4 ADDRESS': 'IP ADDRESS',
 'IPV6 ADDRESS': 'IP ADDRESS',
 'IRIS SCAN': 'BIOMETRIC IDENTIFIER (FINGERPRINT / RETINA / VOICEPRINT)',
 'ITEM DESCRIPTION': 'LINE-ITEM PRODUCT/SERVICE DESCRIPTION',
 'ITIN': 'US TAX ID (EIN / ITIN)',
 'JOB TITLE': 'JOB TITLE',
 'KNOWN DRUG ALLERGIES': 'ALLERGY INFORMATION',
 'LAB': 'LAB TEST RESULT / VALUE',
 'LAB TEST RESULT / VALUE': 'LAB TEST RESULT / VALUE',
 'LAB VALUE': 'LAB TEST RESULT / VALUE',
 'LAB_RESULT': 'LAB TEST RESULT / VALUE',
 'LEGAL DISCLAIMER': 'BOILERPLATE / DISCLAIMER TEXT',
 'LICENSE PLATE': 'VEHICLE IDENTIFIER / LICENSE PLATE NUMBER',
 'LINE-ITEM PRODUCT/SERVICE DESCRIPTION': 'LINE-ITEM PRODUCT/SERVICE DESCRIPTION',
 'LOAN / MORTGAGE ACCOUNT NUMBER': 'LOAN / MORTGAGE ACCOUNT NUMBER',
 'LOAN NUMBER': 'LOAN / MORTGAGE ACCOUNT NUMBER',
 'LOCATION': 'STREET / MAILING ADDRESS',
 'LOGIN NAME': 'USERNAME / LOGIN ID',
 'LOGIN PASSWORD': 'PASSWORD',
 'MAC ADDRESS': 'DEVICE IDENTIFIER / MAC ADDRESS',
 'MAGNETIC STRIPE DATA': 'FULL MAGNETIC STRIPE / TRACK DATA',
 'MAILING ADDRESS': 'STREET / MAILING ADDRESS',
 'MATTER REFERENCE': 'CASE / DOCKET / REFERENCE NUMBER',
 'MEDICAL CLAIM NUMBER': 'MEDICAL CLAIM NUMBER',
 'MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER': 'MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER',
 'MEDICAL RECORD NUMBER (MRN)': 'MEDICAL RECORD NUMBER (MRN)',
 'MEDICAL SPECIALTY': 'DEPARTMENT / SPECIALTY NAME',
 'MEDICAL_RECORD_NUMBER': 'MEDICAL RECORD NUMBER (MRN)',
 'MEDICATION': 'MEDICATION / PRESCRIPTION DETAIL',
 'MEDICATION / PRESCRIPTION DETAIL': 'MEDICATION / PRESCRIPTION DETAIL',
 'MEMBER ID': 'HEALTH PLAN BENEFICIARY/MEMBER NUMBER',
 'MEMBER_ID': 'HEALTH PLAN BENEFICIARY/MEMBER NUMBER',
 'MENTAL / BEHAVIORAL HEALTH NOTES': 'MENTAL / BEHAVIORAL HEALTH NOTES',
 'MERCHANT': 'MERCHANT / VENDOR NAME',
 'MERCHANT / VENDOR NAME': 'MERCHANT / VENDOR NAME',
 'MFA CODE': 'OTP / MFA CODE',
 'MOBILE NUMBER': 'PHONE NUMBER',
 'MONTHLY PREMIUM': 'PREMIUM AMOUNT',
 'MORTGAGE ACCOUNT NUMBER': 'LOAN / MORTGAGE ACCOUNT NUMBER',
 'MRN': 'MEDICAL RECORD NUMBER (MRN)',
 'NAME': 'FULL NAME / PERSON NAME',
 'NAME ON CARD': 'CARDHOLDER NAME',
 'NATION': 'COUNTRY NAME (GENERIC)',
 'NATIONAL / GOVERNMENT ID NUMBER (GENERIC, NON-US/NON-INDIA)': 'NATIONAL / GOVERNMENT ID NUMBER (GENERIC, '
                                                                'NON-US/NON-INDIA)',
 'NATIONAL ID': 'NATIONAL / GOVERNMENT ID NUMBER (GENERIC, NON-US/NON-INDIA)',
 'NET PAY': 'SALARY / COMPENSATION AMOUNT',
 'NPI': 'TREATING PROVIDER NAME / NPI NUMBER',
 'NPI_NUMBER': 'TREATING PROVIDER NAME / NPI NUMBER',
 'NURSE': 'TREATING PROVIDER NAME / NPI NUMBER',
 'OAUTH TOKEN': 'ACCESS TOKEN / OAUTH TOKEN',
 'ONE-TIME PASSWORD': 'OTP / MFA CODE',
 'ORGANIZATION': 'COMPANY / EMPLOYER NAME',
 'ORGANIZATION CONTACT INFO': 'ORGANIZATION CONTACT INFO',
 'ORGANIZATION NAME': 'COMPANY / EMPLOYER NAME',
 'OTP / MFA CODE': 'OTP / MFA CODE',
 'OUT-OF-POCKET AMOUNT': 'COST-SHARING AMOUNT',
 'PAGE #': 'PAGE NUMBER',
 'PAGE NUMBER': 'PAGE NUMBER',
 'PAN': 'AMBIGUOUS — RESOLVE BY CONTEXT',
 'PAN (AMBIGUOUS ACRONYM)': 'AMBIGUOUS — RESOLVE BY CONTEXT',
 'PAN CARD NUMBER': 'PERMANENT ACCOUNT NUMBER — INCOME TAX (INDIA)',
 'PAN_NUMBER': 'PERMANENT ACCOUNT NUMBER — INCOME TAX (INDIA)',
 'PASSPORT ID': 'PASSPORT NUMBER',
 'PASSPORT NO.': 'PASSPORT NUMBER',
 'PASSPORT NUMBER': 'PASSPORT NUMBER',
 'PASSPORT_NUMBER': 'PASSPORT NUMBER',
 'PASSWORD': 'PASSWORD',
 'PATIENT': 'FULL NAME / PERSON NAME',
 'PATIENT ACCOUNT NUMBER': 'MEDICAL RECORD NUMBER (MRN)',
 'PATIENT ID': 'MEDICAL RECORD NUMBER (MRN)',
 'PATIENT NAME': 'FULL NAME / PERSON NAME',
 'PATIENT PHOTO': 'PHOTOGRAPH / FACIAL IMAGE',
 'PATIENT_NAME': 'FULL NAME / PERSON NAME',
 'PAYEE': 'MERCHANT / VENDOR NAME',
 'PAYMENT CARD NUMBER (PAN)': 'PAYMENT CARD NUMBER (PAN)',
 'PAYMENT HISTORY': 'TRANSACTION HISTORY / AMOUNTS',
 'PERFORMANCE RATING / REVIEW CONTENT': 'PERFORMANCE RATING / REVIEW CONTENT',
 'PERFORMANCE REVIEW': 'PERFORMANCE RATING / REVIEW CONTENT',
 'PERMANENT ACCOUNT NUMBER — INCOME TAX (INDIA)': 'PERMANENT ACCOUNT NUMBER — INCOME TAX (INDIA)',
 'PERSON': 'FULL NAME / PERSON NAME',
 'PG.': 'PAGE NUMBER',
 'PGP PRIVATE KEY': 'PRIVATE CRYPTOGRAPHIC KEY / CERTIFICATE',
 'PHONE NUMBER': 'PHONE NUMBER',
 'PHONE_NUMBER': 'PHONE NUMBER',
 'PHOTOGRAPH / FACIAL IMAGE': 'PHOTOGRAPH / FACIAL IMAGE',
 'PHYSICIAN': 'TREATING PROVIDER NAME / NPI NUMBER',
 'PHYSICIAN NAME': 'TREATING PROVIDER NAME / NPI NUMBER',
 'PHYSICIAN NARRATIVE': 'CLINICAL NOTES / NARRATIVE',
 'PIN / PIN BLOCK': 'PIN / PIN BLOCK',
 'PIN BLOCK': 'PIN / PIN BLOCK',
 'PIN NUMBER': 'PIN / PIN BLOCK',
 'PIN_CODE': 'GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)',
 'PLAN NAME': 'PLAN NAME',
 'PLAN TIER': 'PLAN NAME',
 'PO #': 'PURCHASE ORDER NUMBER',
 'PO NUMBER': 'PURCHASE ORDER NUMBER',
 'POLICY NUMBER': 'GROUP / POLICY NUMBER',
 'POLICY_NUMBER': 'HEALTH INSURANCE POLICY NUMBER',
 'PORTFOLIO STATEMENT DETAIL': 'SECURITIES / PORTFOLIO HOLDINGS DETAIL',
 'POSITION TITLE': 'JOB TITLE',
 'POSITIONS': 'SECURITIES / PORTFOLIO HOLDINGS DETAIL',
 'POSTAL CODE': 'GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)',
 'PRACTICE LOCATION ADDRESS': 'FACILITY ADDRESS',
 'PREMIUM AMOUNT': 'PREMIUM AMOUNT',
 'PREMIUM DUE': 'PREMIUM AMOUNT',
 'PRESCRIPTION': 'MEDICATION / PRESCRIPTION DETAIL',
 'PRINT DATE': 'DOCUMENT CREATION/PRINT DATE (NON-INDIVIDUAL)',
 'PRIVATE CRYPTOGRAPHIC KEY / CERTIFICATE': 'PRIVATE CRYPTOGRAPHIC KEY / CERTIFICATE',
 'PRIVATE KEY': 'PRIVATE CRYPTOGRAPHIC KEY / CERTIFICATE',
 'PRIVILEGED & CONFIDENTIAL': 'ATTORNEY-CLIENT PRIVILEGE NOTATION',
 'PROBLEM': 'DIAGNOSIS / MEDICAL CONDITION',
 'PROCEDURE': 'PROCEDURE CODE / DESCRIPTION',
 'PROCEDURE CODE / DESCRIPTION': 'PROCEDURE CODE / DESCRIPTION',
 'PRODUCT LINE ITEM': 'LINE-ITEM PRODUCT/SERVICE DESCRIPTION',
 'PRODUCT NAME': 'PLAN NAME',
 'PROGRESS NOTE': 'CLINICAL NOTES / NARRATIVE',
 'PROVIDER': 'TREATING PROVIDER NAME / NPI NUMBER',
 'PROVIDER ID': 'TREATING PROVIDER NAME / NPI NUMBER',
 'PSYCHIATRIC NOTE': 'MENTAL / BEHAVIORAL HEALTH NOTES',
 'PURCHASE ORDER NUMBER': 'PURCHASE ORDER NUMBER',
 'QR PAYLOAD': 'BARCODE / QR CODE INTERNAL DOCUMENT ID',
 'RACE': 'RACIAL OR ETHNIC ORIGIN DATA',
 'RACIAL OR ETHNIC ORIGIN DATA': 'RACIAL OR ETHNIC ORIGIN DATA',
 'REGISTRATION NUMBER': 'VEHICLE IDENTIFIER / LICENSE PLATE NUMBER',
 'RELIGION': 'RELIGIOUS BELIEF / AFFILIATION',
 'RELIGIOUS AFFILIATION': 'RELIGIOUS BELIEF / AFFILIATION',
 'RELIGIOUS BELIEF / AFFILIATION': 'RELIGIOUS BELIEF / AFFILIATION',
 'RESIDENTIAL ADDRESS': 'STREET / MAILING ADDRESS',
 'RETINA SCAN': 'BIOMETRIC IDENTIFIER (FINGERPRINT / RETINA / VOICEPRINT)',
 'ROUTING NUMBER': 'BANK ROUTING / SORT CODE',
 'RX': 'MEDICATION / PRESCRIPTION DETAIL',
 'SALARY / COMPENSATION AMOUNT': 'SALARY / COMPENSATION AMOUNT',
 'SAMPLE PATIENT SCENARIO': 'COVERAGE EXAMPLE SCENARIO',
 'SCANNER SERIAL NUMBER': 'MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER',
 'SCANNER TECHNICAL PARAMETER': 'CT NUMBER / IMAGING TECHNICAL PARAMETER',
 'SCHEDULING ID': 'BOOKING REFERENCE NUMBER',
 'SECRET ANSWER': 'SECURITY QUESTION & ANSWER',
 'SECRET KEY': 'API KEY / SECRET KEY',
 'SECURITIES / PORTFOLIO HOLDINGS DETAIL': 'SECURITIES / PORTFOLIO HOLDINGS DETAIL',
 'SECURITY CODE': 'CARD VERIFICATION CODE (CVV/CVC/CID/CAV2)',
 'SECURITY QUESTION': 'SECURITY QUESTION & ANSWER',
 'SECURITY QUESTION & ANSWER': 'SECURITY QUESTION & ANSWER',
 'SERVER HOSTNAME': 'INTERNAL SERVER / HOSTNAME',
 'SERVICE LINE': 'DEPARTMENT / SPECIALTY NAME',
 'SESSION COOKIE': 'SESSION ID / AUTH COOKIE',
 'SESSION ID / AUTH COOKIE': 'SESSION ID / AUTH COOKIE',
 'SESSION TOKEN': 'SESSION ID / AUTH COOKIE',
 'SEXUAL ORIENTATION': 'SEXUAL ORIENTATION / GENDER IDENTITY',
 'SEXUAL ORIENTATION / GENDER IDENTITY': 'SEXUAL ORIENTATION / GENDER IDENTITY',
 'SIGNATURE': 'SIGNATURE',
 'SIGNATURE BLOCK': 'SIGNATURE',
 'SOAP NOTE': 'CLINICAL NOTES / NARRATIVE',
 'SOCIAL SECURITY NO.': 'SOCIAL SECURITY NUMBER (SSN)',
 'SOCIAL SECURITY NUMBER': 'SOCIAL SECURITY NUMBER (SSN)',
 'SOCIAL SECURITY NUMBER (SSN)': 'SOCIAL SECURITY NUMBER (SSN)',
 'SORT CODE': 'BANK ROUTING / SORT CODE',
 'SPECIMEN RESULT': 'LAB TEST RESULT / VALUE',
 'SSN': 'SOCIAL SECURITY NUMBER (SSN)',
 'SSN FAMILY': 'SOCIAL SECURITY NUMBER (SSN)',
 'STAFF ID': 'EMPLOYEE ID NUMBER',
 'STANDARD TERMS BOILERPLATE': 'BOILERPLATE / DISCLAIMER TEXT',
 'START_DATE': 'ADMISSION / DISCHARGE / SERVICE DATE',
 'STATEMENT LINE ITEMS': 'TRANSACTION HISTORY / AMOUNTS',
 'STD DIAGNOSIS': 'HIV / STI STATUS',
 'STI RESULT': 'HIV / STI STATUS',
 'STREET / MAILING ADDRESS': 'STREET / MAILING ADDRESS',
 'STUDY ID': 'IMAGING STUDY ID / ACCESSION NUMBER',
 'SUBSCRIBER ID': 'HEALTH PLAN BENEFICIARY/MEMBER NUMBER',
 'SUBSTANCE USE DISORDER TREATMENT INFO': 'SUBSTANCE USE DISORDER TREATMENT INFO',
 'SUD TREATMENT RECORD': 'SUBSTANCE USE DISORDER TREATMENT INFO',
 'SWIFT CODE': 'IBAN / SWIFT-BIC CODE',
 'SYMPTOM': 'DIAGNOSIS / MEDICAL CONDITION',
 'TAX_ID': 'US TAX ID (EIN / ITIN)',
 'TELEPHONE NUMBER': 'PHONE NUMBER',
 'TEST RESULT': 'LAB TEST RESULT / VALUE',
 'THERAPY NOTE': 'MENTAL / BEHAVIORAL HEALTH NOTES',
 'TLS PRIVATE KEY': 'PRIVATE CRYPTOGRAPHIC KEY / CERTIFICATE',
 'TRACK 1 DATA': 'FULL MAGNETIC STRIPE / TRACK DATA',
 'TRACK 2 DATA': 'FULL MAGNETIC STRIPE / TRACK DATA',
 'TRADE UNION MEMBERSHIP': 'TRADE UNION MEMBERSHIP',
 'TRANSACTION DETAIL': 'TRANSACTION HISTORY / AMOUNTS',
 'TRANSACTION HISTORY / AMOUNTS': 'TRANSACTION HISTORY / AMOUNTS',
 'TREATING PROVIDER NAME / NPI NUMBER': 'TREATING PROVIDER NAME / NPI NUMBER',
 'TREATMENT PERFORMED': 'PROCEDURE CODE / DESCRIPTION',
 'TYPES OF PHI INVOLVED': 'BREACHED DATA ELEMENT DESCRIPTION',
 'UID': 'AADHAAR NUMBER (INDIA)',
 'UNION AFFILIATION': 'TRADE UNION MEMBERSHIP',
 'UNION MEMBER': 'TRADE UNION MEMBERSHIP',
 'US TAX ID (EIN / ITIN)': 'US TAX ID (EIN / ITIN)',
 'USER ID': 'USERNAME / LOGIN ID',
 'USERNAME / LOGIN ID': 'USERNAME / LOGIN ID',
 'US_PHONE_NUMBER': 'PHONE NUMBER',
 'VACCINATION RECORD': 'IMMUNIZATION RECORD',
 'VALID THRU': 'CARD EXPIRATION DATE',
 'VEHICLE IDENTIFIER / LICENSE PLATE NUMBER': 'VEHICLE IDENTIFIER / LICENSE PLATE NUMBER',
 'VENDOR NAME': 'MERCHANT / VENDOR NAME',
 'VENUE': 'COURT / JURISDICTION NAME',
 'VERIFICATION CODE': 'OTP / MFA CODE',
 'VIN': 'VEHICLE IDENTIFIER / LICENSE PLATE NUMBER',
 'VISA / IMMIGRATION DOCUMENT NUMBER': 'VISA / IMMIGRATION DOCUMENT NUMBER',
 'VISA NUMBER': 'VISA / IMMIGRATION DOCUMENT NUMBER',
 'VISIT_DATE': 'ADMISSION / DISCHARGE / SERVICE DATE',
 'VITAL_SIGN': 'LAB TEST RESULT / VALUE',
 'VOICEPRINT': 'BIOMETRIC IDENTIFIER (FINGERPRINT / RETINA / VOICEPRINT)',
 'VULNERABILITY REFERENCE': 'CVE / VULNERABILITY REFERENCE',
 'WET SIGNATURE': 'SIGNATURE',
 'WHAT HAPPENED SECTION': 'BREACH INCIDENT DESCRIPTION',
 'ZIP CODE': 'GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)',
 'ZIP_CODE': 'GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)'}

DOCUMENT_POLICIES = {'AML Document': {'BANK ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                          'data_type': 'Financial',
                                          'priority': 'MUST_HAVE',
                                          'regulation': 'FTC Safeguards Rule',
                                          'risk_level': 'CRITICAL',
                                          'threat': 'Financial fraud, unauthorized transfers, and account targeting.'},
                  'CASE / DOCKET / REFERENCE NUMBER': {'category': 'Administrative Identifier',
                                                       'data_type': 'Other',
                                                       'priority': 'NICE_TO_HAVE',
                                                       'regulation': 'No specific statutory citation in the supplied '
                                                                     'source set',
                                                       'risk_level': 'MEDIUM',
                                                       'threat': 'Links an individual to a specific legal or '
                                                                 'regulatory matter, which can itself be sensitive '
                                                                 '(e.g., litigation, AML case).'},
                  'DATE OF BIRTH': {'category': 'Direct Identifier',
                                    'data_type': 'PII',
                                    'priority': 'MUST_HAVE',
                                    'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                    'risk_level': 'HIGH',
                                    'threat': 'Common knowledge-based authentication factor; enables account takeover '
                                              'and identity theft.'},
                  'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                              'data_type': 'PII',
                                              'priority': 'MUST_HAVE',
                                              'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                              'risk_level': 'HIGH',
                                              'threat': 'Enables identity theft, account takeover, and social '
                                                        'engineering when paired with account data.'},
                  'NATIONAL / GOVERNMENT ID NUMBER (GENERIC, NON-US/NON-INDIA)': {'category': 'Government Identifier',
                                                                                  'data_type': 'PII',
                                                                                  'priority': 'MUST_HAVE',
                                                                                  'regulation': 'GDPR Art. 4 / NIST SP '
                                                                                                '800-122',
                                                                                  'risk_level': 'HIGH',
                                                                                  'threat': 'Enables identity theft '
                                                                                            'and impersonation; '
                                                                                            'jurisdiction-specific '
                                                                                            'format but universally a '
                                                                                            'strong identity anchor.'},
                  'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                               'data_type': 'PII',
                                               'priority': 'MUST_HAVE',
                                               'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                               'risk_level': 'MEDIUM',
                                               'threat': 'Enables mail fraud, identity theft, and physical targeting '
                                                         'when paired with financial data.'},
                  'TRANSACTION HISTORY / AMOUNTS': {'category': 'Financial Data',
                                                    'data_type': 'Financial',
                                                    'priority': 'NICE_TO_HAVE',
                                                    'regulation': 'GDPR Art. 4',
                                                    'risk_level': 'LOW',
                                                    'threat': 'Discloses spending behavior/financial profile; '
                                                              'privacy-relevant but not independently exploitable '
                                                              'without account credentials.'}},
 'Bank Statement': {'BANK ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                            'data_type': 'Financial',
                                            'priority': 'MUST_HAVE',
                                            'regulation': 'FTC Safeguards Rule',
                                            'risk_level': 'CRITICAL',
                                            'threat': 'Financial fraud, unauthorized transfers, and account '
                                                      'targeting.'},
                    'BANK ROUTING / SORT CODE': {'category': 'Financial Account Data',
                                                 'data_type': 'Financial',
                                                 'priority': 'NICE_TO_HAVE',
                                                 'regulation': 'FTC Safeguards Rule',
                                                 'risk_level': 'MEDIUM',
                                                 'threat': 'Enables fraudulent ACH/wire setup when combined with an '
                                                           'account number; low risk in isolation.'},
                    'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                'data_type': 'PII',
                                                'priority': 'MUST_HAVE',
                                                'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                                'risk_level': 'HIGH',
                                                'threat': 'Enables identity theft, account takeover, and social '
                                                          'engineering when paired with account data.'},
                    'IBAN / SWIFT-BIC CODE': {'category': 'Financial Account Data',
                                              'data_type': 'Financial',
                                              'priority': 'MUST_HAVE',
                                              'regulation': 'FTC Safeguards Rule / GDPR Art. 4',
                                              'risk_level': 'HIGH',
                                              'threat': 'Enables unauthorized international wire transfers and account '
                                                        'targeting.'},
                    'PHONE NUMBER': {'category': 'Direct Identifier',
                                     'data_type': 'PII',
                                     'priority': 'MUST_HAVE',
                                     'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                     'risk_level': 'MEDIUM',
                                     'threat': 'Enables account-recovery social engineering and SIM-swap style fraud.'},
                    'SOCIAL SECURITY NUMBER (SSN)': {'category': 'Government Identifier',
                                                     'data_type': 'PII',
                                                     'priority': 'MUST_HAVE',
                                                     'regulation': 'NIST SP 800-122 / HIPAA Privacy Rule (in health '
                                                                   'context)',
                                                     'risk_level': 'CRITICAL',
                                                     'threat': 'Identity theft, account fraud, impersonation, and '
                                                               'long-term privacy harm — a US SSN cannot practically '
                                                               'be reissued.'},
                    'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                 'data_type': 'PII',
                                                 'priority': 'MUST_HAVE',
                                                 'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                                 'risk_level': 'MEDIUM',
                                                 'threat': 'Enables mail fraud, identity theft, and physical targeting '
                                                           'when paired with financial data.'},
                    'TRANSACTION HISTORY / AMOUNTS': {'category': 'Financial Data',
                                                      'data_type': 'Financial',
                                                      'priority': 'NICE_TO_HAVE',
                                                      'regulation': 'GDPR Art. 4',
                                                      'risk_level': 'LOW',
                                                      'threat': 'Discloses spending behavior/financial profile; '
                                                                'privacy-relevant but not independently exploitable '
                                                                'without account credentials.'}},
 'Benefits / Performance / Disciplinary Document': {'DATE OF BIRTH': {'category': 'Direct Identifier',
                                                                      'data_type': 'PII',
                                                                      'priority': 'MUST_HAVE',
                                                                      'regulation': 'GDPR Art. 4 / India DPDP Act, '
                                                                                    '2023',
                                                                      'risk_level': 'MEDIUM',
                                                                      'threat': 'Supports identity theft and may '
                                                                                'reveal protected characteristics '
                                                                                '(e.g., age-related).'},
                                                    'DISABILITY STATUS': {'category': 'HR Sensitive Data',
                                                                          'data_type': 'PHI/Other',
                                                                          'priority': 'MUST_HAVE',
                                                                          'regulation': 'GDPR Art. 9',
                                                                          'risk_level': 'HIGH',
                                                                          'threat': 'Discrimination and employment '
                                                                                    'risk; also constitutes health '
                                                                                    'data in most frameworks.'},
                                                    'DISCIPLINARY ACTION DETAIL': {'category': 'HR Sensitive Data',
                                                                                   'data_type': 'Other',
                                                                                   'priority': 'NICE_TO_HAVE',
                                                                                   'regulation': 'No specific '
                                                                                                 'statutory citation '
                                                                                                 'in the supplied '
                                                                                                 'source set',
                                                                                   'risk_level': 'MEDIUM',
                                                                                   'threat': 'Reputational and '
                                                                                             'employment harm; could '
                                                                                             'affect future employment '
                                                                                             'prospects if leaked.'},
                                                    'EMPLOYEE ID NUMBER': {'category': 'Direct Identifier',
                                                                           'data_type': 'PII',
                                                                           'priority': 'NICE_TO_HAVE',
                                                                           'regulation': 'GDPR Art. 4 / India DPDP '
                                                                                         'Act, 2023',
                                                                           'risk_level': 'LOW',
                                                                           'threat': 'Links records to a specific '
                                                                                     'employee; lower standalone fraud '
                                                                                     'risk than a government ID or '
                                                                                     'SSN.'},
                                                    'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                                'data_type': 'PII',
                                                                                'priority': 'MUST_HAVE',
                                                                                'regulation': 'GDPR Art. 4 / India '
                                                                                              'DPDP Act, 2023',
                                                                                'risk_level': 'HIGH',
                                                                                'threat': 'Enables identity theft and '
                                                                                          'unauthorized disclosure of '
                                                                                          'employment data.'},
                                                    'HEALTH PLAN BENEFICIARY/MEMBER NUMBER': {'category': 'Direct '
                                                                                                          'Identifier',
                                                                                              'data_type': 'PHI',
                                                                                              'priority': 'MUST_HAVE',
                                                                                              'regulation': 'HIPAA '
                                                                                                            'Privacy '
                                                                                                            'Rule',
                                                                                              'risk_level': 'HIGH',
                                                                                              'threat': 'Enables '
                                                                                                        'medical '
                                                                                                        'insurance '
                                                                                                        'fraud and '
                                                                                                        'unauthorized '
                                                                                                        'claims filed '
                                                                                                        'against the '
                                                                                                        'beneficiary.'},
                                                    'PERFORMANCE RATING / REVIEW CONTENT': {'category': 'HR Sensitive '
                                                                                                        'Data',
                                                                                            'data_type': 'Other',
                                                                                            'priority': 'NICE_TO_HAVE',
                                                                                            'regulation': 'No specific '
                                                                                                          'statutory '
                                                                                                          'citation in '
                                                                                                          'the '
                                                                                                          'supplied '
                                                                                                          'source set',
                                                                                            'risk_level': 'MEDIUM',
                                                                                            'threat': 'Reputational '
                                                                                                      'and employment '
                                                                                                      'harm if '
                                                                                                      'disclosed to '
                                                                                                      'unauthorized '
                                                                                                      'parties (e.g., '
                                                                                                      'future '
                                                                                                      'employers, '
                                                                                                      'colleagues).'}},
 'Contract / NDA / Legal Agreement': {'BANK ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                                              'data_type': 'Financial',
                                                              'priority': 'MUST_HAVE',
                                                              'regulation': 'FTC Safeguards Rule',
                                                              'risk_level': 'CRITICAL',
                                                              'threat': 'Financial fraud, unauthorized transfers, and '
                                                                        'account targeting.'},
                                      'COMPANY / EMPLOYER NAME': {'category': 'Administrative/Structural Metadata',
                                                                  'data_type': 'Other',
                                                                  'priority': 'DROP',
                                                                  'regulation': 'N/A',
                                                                  'risk_level': 'MEDIUM',
                                                                  'threat': 'None on its own — organizational data; '
                                                                            'only becomes privacy-relevant combined '
                                                                            'with an individual identifier already '
                                                                            'captured separately.'},
                                      'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                  'data_type': 'PII',
                                                                  'priority': 'MUST_HAVE',
                                                                  'regulation': 'GDPR Art. 4 / NIST SP 800-122',
                                                                  'risk_level': 'HIGH',
                                                                  'threat': "Discloses a party's involvement in a "
                                                                            'legal matter; enables identity theft when '
                                                                            'combined with case data.'},
                                      'SIGNATURE': {'category': 'Direct Identifier',
                                                    'data_type': 'PII',
                                                    'priority': 'MUST_HAVE',
                                                    'regulation': 'GDPR Art. 4 / NIST SP 800-122',
                                                    'risk_level': 'HIGH',
                                                    'threat': 'Enables forgery of contractual execution, creating '
                                                              'legal and financial exposure.'},
                                      'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                                   'data_type': 'PII',
                                                                   'priority': 'NICE_TO_HAVE',
                                                                   'regulation': 'GDPR Art. 4 / NIST SP 800-122',
                                                                   'risk_level': 'MEDIUM',
                                                                   'threat': "Discloses a party's residence/place of "
                                                                             'business tied to a legal matter.'}},
 'Credential & Secrets Document (API keys, tokens, passwords)': {'ACCESS TOKEN / OAUTH TOKEN': {'category': 'Security '
                                                                                                            'Credential',
                                                                                                'data_type': 'Credential',
                                                                                                'priority': 'MUST_HAVE',
                                                                                                'regulation': 'GDPR '
                                                                                                              'Art. 32',
                                                                                                'risk_level': 'CRITICAL',
                                                                                                'threat': 'Enables '
                                                                                                          'unauthorized '
                                                                                                          'impersonation '
                                                                                                          'of a '
                                                                                                          'user/service '
                                                                                                          'session; '
                                                                                                          'often '
                                                                                                          'bypasses '
                                                                                                          'password '
                                                                                                          'protections '
                                                                                                          'entirely.'},
                                                                 'API KEY / SECRET KEY': {'category': 'Security '
                                                                                                      'Credential',
                                                                                          'data_type': 'Credential',
                                                                                          'priority': 'MUST_HAVE',
                                                                                          'regulation': 'GDPR Art. 32',
                                                                                          'risk_level': 'CRITICAL',
                                                                                          'threat': 'Unauthorized '
                                                                                                    'system access, '
                                                                                                    'data '
                                                                                                    'exfiltration, and '
                                                                                                    'service '
                                                                                                    'compromise.'},
                                                                 'CVE / VULNERABILITY REFERENCE': {'category': 'Administrative/Structural '
                                                                                                               'Metadata',
                                                                                                   'data_type': 'Other',
                                                                                                   'priority': 'DROP',
                                                                                                   'regulation': 'N/A',
                                                                                                   'risk_level': 'MEDIUM',
                                                                                                   'threat': 'None — a '
                                                                                                             'public '
                                                                                                             'vulnerability '
                                                                                                             'catalog '
                                                                                                             'identifier, '
                                                                                                             'not '
                                                                                                             'personal '
                                                                                                             'data.'},
                                                                 'INTERNAL SERVER / HOSTNAME': {'category': 'Administrative/Structural '
                                                                                                            'Metadata',
                                                                                                'data_type': 'Other',
                                                                                                'priority': 'DROP',
                                                                                                'regulation': 'N/A',
                                                                                                'risk_level': 'MEDIUM',
                                                                                                'threat': 'None '
                                                                                                          'directly — '
                                                                                                          'infrastructure '
                                                                                                          'metadata, '
                                                                                                          'not linked '
                                                                                                          'to a '
                                                                                                          'specific '
                                                                                                          'individual '
                                                                                                          '(distinct '
                                                                                                          'from a '
                                                                                                          "person's "
                                                                                                          'own device '
                                                                                                          'IP address, '
                                                                                                          'tracked '
                                                                                                          'separately).'},
                                                                 'OTP / MFA CODE': {'category': 'Security Credential',
                                                                                    'data_type': 'Credential',
                                                                                    'priority': 'MUST_HAVE',
                                                                                    'regulation': 'GDPR Art. 32',
                                                                                    'risk_level': 'HIGH',
                                                                                    'threat': 'Enables real-time '
                                                                                              'bypass of multi-factor '
                                                                                              'authentication if '
                                                                                              'intercepted while still '
                                                                                              'valid.'},
                                                                 'PASSWORD': {'category': 'Security Credential',
                                                                              'data_type': 'Credential',
                                                                              'priority': 'MUST_HAVE',
                                                                              'regulation': 'GDPR Art. 32',
                                                                              'risk_level': 'CRITICAL',
                                                                              'threat': 'Direct unauthorized '
                                                                                        'account/system access; '
                                                                                        'enables full account '
                                                                                        'takeover.'},
                                                                 'PRIVATE CRYPTOGRAPHIC KEY / CERTIFICATE': {'category': 'Security '
                                                                                                                         'Credential',
                                                                                                             'data_type': 'Credential',
                                                                                                             'priority': 'MUST_HAVE',
                                                                                                             'regulation': 'GDPR '
                                                                                                                           'Art. '
                                                                                                                           '32',
                                                                                                             'risk_level': 'CRITICAL',
                                                                                                             'threat': 'Complete '
                                                                                                                       'compromise '
                                                                                                                       'of '
                                                                                                                       'encrypted '
                                                                                                                       'communications '
                                                                                                                       'or '
                                                                                                                       'signing '
                                                                                                                       'authority.'},
                                                                 'SECURITY QUESTION & ANSWER': {'category': 'Security '
                                                                                                            'Credential',
                                                                                                'data_type': 'Credential',
                                                                                                'priority': 'MUST_HAVE',
                                                                                                'regulation': 'GDPR '
                                                                                                              'Art. 32',
                                                                                                'risk_level': 'HIGH',
                                                                                                'threat': 'Enables '
                                                                                                          'account-recovery '
                                                                                                          'bypass and '
                                                                                                          'impersonation.'},
                                                                 'SESSION ID / AUTH COOKIE': {'category': 'Security '
                                                                                                          'Credential '
                                                                                                          '— Online '
                                                                                                          'Identifier',
                                                                                              'data_type': 'Credential',
                                                                                              'priority': 'NICE_TO_HAVE',
                                                                                              'regulation': 'GDPR Art. '
                                                                                                            '4',
                                                                                              'risk_level': 'MEDIUM',
                                                                                              'threat': 'Enables '
                                                                                                        'session '
                                                                                                        'hijacking '
                                                                                                        'while the '
                                                                                                        'session '
                                                                                                        'remains '
                                                                                                        'valid.'},
                                                                 'USERNAME / LOGIN ID': {'category': 'Security '
                                                                                                     'Credential',
                                                                                         'data_type': 'Credential',
                                                                                         'priority': 'NICE_TO_HAVE',
                                                                                         'regulation': 'GDPR Art. 32 / '
                                                                                                       'GDPR Art. 4',
                                                                                         'risk_level': 'MEDIUM',
                                                                                         'threat': 'Enables targeted '
                                                                                                   'credential-stuffing '
                                                                                                   'and '
                                                                                                   'account-targeting '
                                                                                                   'attacks, '
                                                                                                   'especially paired '
                                                                                                   'with a password.'}},
 'Credit Card Statement': {'CARD EXPIRATION DATE': {'category': 'Payment Card — Cardholder Data',
                                                    'data_type': 'Payment',
                                                    'priority': 'NICE_TO_HAVE',
                                                    'regulation': 'PCI DSS',
                                                    'risk_level': 'MEDIUM',
                                                    'threat': 'Low value alone; increases fraud risk only when paired '
                                                              'with the PAN and cardholder name.'},
                           'CARD VERIFICATION CODE (CVV/CVC/CID/CAV2)': {'category': 'Payment Card — Sensitive '
                                                                                     'Authentication Data',
                                                                         'data_type': 'Payment',
                                                                         'priority': 'MUST_HAVE',
                                                                         'regulation': 'PCI DSS',
                                                                         'risk_level': 'CRITICAL',
                                                                         'threat': 'PCI DSS prohibits storage after '
                                                                                   'authorization; presence in a '
                                                                                   'document is itself a compliance '
                                                                                   'finding, and exposure enables '
                                                                                   'direct card-not-present fraud.'},
                           'CARDHOLDER NAME': {'category': 'Payment Card — Cardholder Data',
                                               'data_type': 'Payment',
                                               'priority': 'NICE_TO_HAVE',
                                               'regulation': 'PCI DSS',
                                               'risk_level': 'MEDIUM',
                                               'threat': 'Enables card-not-present fraud when combined with PAN/CVV.'},
                           'FULL MAGNETIC STRIPE / TRACK DATA': {'category': 'Payment Card — Sensitive Authentication '
                                                                             'Data',
                                                                 'data_type': 'Payment',
                                                                 'priority': 'MUST_HAVE',
                                                                 'regulation': 'PCI DSS',
                                                                 'risk_level': 'CRITICAL',
                                                                 'threat': 'Contains everything needed to clone a '
                                                                           'card; the single most damaging '
                                                                           'payment-data exposure.'},
                           'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                       'data_type': 'PII',
                                                       'priority': 'MUST_HAVE',
                                                       'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                                       'risk_level': 'HIGH',
                                                       'threat': 'Enables identity theft, account takeover, and social '
                                                                 'engineering when paired with account data.'},
                           'PAYMENT CARD NUMBER (PAN)': {'category': 'Payment Card — Cardholder Data',
                                                         'data_type': 'Payment',
                                                         'priority': 'MUST_HAVE',
                                                         'regulation': 'PCI DSS',
                                                         'risk_level': 'CRITICAL',
                                                         'threat': 'Direct payment fraud and unauthorized '
                                                                   'transactions.'},
                           'PIN / PIN BLOCK': {'category': 'Payment Card — Sensitive Authentication Data',
                                               'data_type': 'Payment',
                                               'priority': 'MUST_HAVE',
                                               'regulation': 'PCI DSS',
                                               'risk_level': 'CRITICAL',
                                               'threat': 'Enables direct fraudulent card-present transactions; among '
                                                         'the most sensitive payment data elements.'},
                           'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                        'data_type': 'PII',
                                                        'priority': 'MUST_HAVE',
                                                        'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                                        'risk_level': 'MEDIUM',
                                                        'threat': 'Enables mail fraud, identity theft, and physical '
                                                                  'targeting when paired with financial data.'},
                           'TRANSACTION HISTORY / AMOUNTS': {'category': 'Financial Data',
                                                             'data_type': 'Financial',
                                                             'priority': 'NICE_TO_HAVE',
                                                             'regulation': 'GDPR Art. 4',
                                                             'risk_level': 'LOW',
                                                             'threat': 'Discloses spending behavior/financial profile; '
                                                                       'privacy-relevant but not independently '
                                                                       'exploitable without account credentials.'}},
 'Discharge Summary': {'ADMISSION / DISCHARGE / SERVICE DATE': {'category': 'Direct Identifier',
                                                                'data_type': 'PHI',
                                                                'priority': 'MUST_HAVE',
                                                                'regulation': 'HIPAA Privacy Rule',
                                                                'risk_level': 'MEDIUM',
                                                                'threat': 'Enables re-identification when correlated '
                                                                          'with public event data (e.g., accident '
                                                                          'reports); listed HIPAA identifier.'},
                       'ALLERGY INFORMATION': {'category': 'Health/Clinical Data',
                                               'data_type': 'PHI',
                                               'priority': 'NICE_TO_HAVE',
                                               'regulation': 'HIPAA Privacy Rule',
                                               'risk_level': 'MEDIUM',
                                               'threat': 'Reveals health information; misuse risk lower than diagnosis '
                                                         'but still privacy-sensitive.'},
                       'CLINICAL NOTES / NARRATIVE': {'category': 'Health/Clinical Data',
                                                      'data_type': 'PHI',
                                                      'priority': 'MUST_HAVE',
                                                      'regulation': 'HIPAA Privacy Rule',
                                                      'risk_level': 'CRITICAL',
                                                      'threat': 'Free text frequently contains multiple PHI elements '
                                                                'at once (identity + diagnosis + history); high '
                                                                'aggregate breach impact.'},
                       'DATE OF BIRTH': {'category': 'Direct Identifier',
                                         'data_type': 'PII',
                                         'priority': 'MUST_HAVE',
                                         'regulation': 'HIPAA Privacy Rule',
                                         'risk_level': 'HIGH',
                                         'threat': 'HIPAA Safe Harbor identifier; strengthens patient '
                                                   're-identification when combined with other fields.'},
                       'DIAGNOSIS / MEDICAL CONDITION': {'category': 'Health/Clinical Data',
                                                         'data_type': 'PHI',
                                                         'priority': 'MUST_HAVE',
                                                         'regulation': 'HIPAA Privacy Rule',
                                                         'risk_level': 'CRITICAL',
                                                         'threat': 'Discrimination, stigmatization, '
                                                                   'employment/insurance harm, and medical-privacy '
                                                                   'harm if disclosed.'},
                       'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                   'data_type': 'PII',
                                                   'priority': 'MUST_HAVE',
                                                   'regulation': 'HIPAA Privacy Rule',
                                                   'risk_level': 'CRITICAL',
                                                   'threat': "Re-identifies an individual's health record; enables "
                                                             'medical-identity theft and targeted harassment.'},
                       'MEDICAL RECORD NUMBER (MRN)': {'category': 'Direct Identifier',
                                                       'data_type': 'PHI',
                                                       'priority': 'MUST_HAVE',
                                                       'regulation': 'HIPAA Privacy Rule',
                                                       'risk_level': 'CRITICAL',
                                                       'threat': 'Directly links an individual to their entire '
                                                                 'clinical history; enables medical-identity theft and '
                                                                 'insurance fraud.'},
                       'MEDICATION / PRESCRIPTION DETAIL': {'category': 'Health/Clinical Data',
                                                            'data_type': 'PHI',
                                                            'priority': 'MUST_HAVE',
                                                            'regulation': 'HIPAA Privacy Rule',
                                                            'risk_level': 'HIGH',
                                                            'threat': 'Can reveal a sensitive condition by inference '
                                                                      '(e.g., psychiatric, HIV, oncology drugs); '
                                                                      'enables prescription fraud.'},
                       'PROCEDURE CODE / DESCRIPTION': {'category': 'Health/Clinical Data',
                                                        'data_type': 'PHI',
                                                        'priority': 'NICE_TO_HAVE',
                                                        'regulation': 'HIPAA Privacy Rule',
                                                        'risk_level': 'MEDIUM',
                                                        'threat': 'Discloses treatment history; can imply a condition '
                                                                  '(re-identification risk) and support insurance '
                                                                  'fraud.'},
                       'TREATING PROVIDER NAME / NPI NUMBER': {'category': 'Direct Identifier',
                                                               'data_type': 'PHI',
                                                               'priority': 'NICE_TO_HAVE',
                                                               'regulation': 'HIPAA Privacy Rule',
                                                               'risk_level': 'MEDIUM',
                                                               'threat': 'Discloses the treating clinician; can '
                                                                         'support social engineering against the '
                                                                         'practice, lower risk to the patient '
                                                                         'directly.'}},
 'Email / Letter / General Form / Scanned Document': {'BARCODE / QR CODE INTERNAL DOCUMENT ID': {'category': 'Administrative/Structural '
                                                                                                             'Metadata',
                                                                                                 'data_type': 'Other',
                                                                                                 'priority': 'DROP',
                                                                                                 'regulation': 'N/A',
                                                                                                 'risk_level': 'MEDIUM',
                                                                                                 'threat': 'None — an '
                                                                                                           'internal '
                                                                                                           'document-management/tracking '
                                                                                                           'reference.'},
                                                      'BOILERPLATE / DISCLAIMER TEXT': {'category': 'Administrative/Structural '
                                                                                                    'Metadata',
                                                                                        'data_type': 'Other',
                                                                                        'priority': 'DROP',
                                                                                        'regulation': 'N/A',
                                                                                        'risk_level': 'MEDIUM',
                                                                                        'threat': 'None — standardized '
                                                                                                  'text repeated '
                                                                                                  'across many '
                                                                                                  'documents, not '
                                                                                                  'personal data.'},
                                                      'COUNTRY NAME (GENERIC)': {'category': 'Administrative/Structural '
                                                                                             'Metadata',
                                                                                 'data_type': 'Other',
                                                                                 'priority': 'DROP',
                                                                                 'regulation': 'N/A',
                                                                                 'risk_level': 'MEDIUM',
                                                                                 'threat': 'None on its own — '
                                                                                           'extremely low-specificity '
                                                                                           'geographic reference.'},
                                                      'DOCUMENT CREATION/PRINT DATE (NON-INDIVIDUAL)': {'category': 'Administrative/Structural '
                                                                                                                    'Metadata',
                                                                                                        'data_type': 'Other',
                                                                                                        'priority': 'DROP',
                                                                                                        'regulation': 'N/A',
                                                                                                        'risk_level': 'MEDIUM',
                                                                                                        'threat': 'None '
                                                                                                                  '— a '
                                                                                                                  'system/document '
                                                                                                                  'timestamp, '
                                                                                                                  'not '
                                                                                                                  'a '
                                                                                                                  'date '
                                                                                                                  'tied '
                                                                                                                  'to '
                                                                                                                  'an '
                                                                                                                  'individual '
                                                                                                                  '(contrast '
                                                                                                                  'with '
                                                                                                                  'Service '
                                                                                                                  'Date, '
                                                                                                                  'which '
                                                                                                                  'is '
                                                                                                                  'tracked '
                                                                                                                  'separately '
                                                                                                                  'for '
                                                                                                                  'health '
                                                                                                                  'records).'},
                                                      'EMAIL ADDRESS': {'category': 'Direct Identifier',
                                                                        'data_type': 'PII',
                                                                        'priority': 'NICE_TO_HAVE',
                                                                        'regulation': 'GDPR Art. 4 / India DPDP Act, '
                                                                                      '2023',
                                                                        'risk_level': 'LOW',
                                                                        'threat': 'Enables phishing, spam, and '
                                                                                  'account-targeting.'},
                                                      'FORM / TEMPLATE FIELD LABEL': {'category': 'Administrative/Structural '
                                                                                                  'Metadata',
                                                                                      'data_type': 'Other',
                                                                                      'priority': 'DROP',
                                                                                      'regulation': 'N/A',
                                                                                      'risk_level': 'MEDIUM',
                                                                                      'threat': 'None — static '
                                                                                                'template text, not '
                                                                                                'data about any '
                                                                                                'individual.'},
                                                      'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                                  'data_type': 'PII',
                                                                                  'priority': 'MUST_HAVE',
                                                                                  'regulation': 'GDPR Art. 4 / India '
                                                                                                'DPDP Act, 2023',
                                                                                  'risk_level': 'MEDIUM',
                                                                                  'threat': 'Basic identity exposure; '
                                                                                            'risk rises sharply when '
                                                                                            'combined with other '
                                                                                            'identifiers.'},
                                                      'PAGE NUMBER': {'category': 'Administrative/Structural Metadata',
                                                                      'data_type': 'Other',
                                                                      'priority': 'DROP',
                                                                      'regulation': 'N/A',
                                                                      'risk_level': 'MEDIUM',
                                                                      'threat': 'None — pagination metadata.'},
                                                      'PHONE NUMBER': {'category': 'Direct Identifier',
                                                                       'data_type': 'PII',
                                                                       'priority': 'NICE_TO_HAVE',
                                                                       'regulation': 'GDPR Art. 4 / India DPDP Act, '
                                                                                     '2023',
                                                                       'risk_level': 'LOW',
                                                                       'threat': 'Enables phishing, spam, and social '
                                                                                 'engineering.'},
                                                      'SIGNATURE': {'category': 'Direct Identifier',
                                                                    'data_type': 'PII',
                                                                    'priority': 'NICE_TO_HAVE',
                                                                    'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                                    'risk_level': 'LOW',
                                                                    'threat': 'Low standalone risk; relevant mainly as '
                                                                              'forgery material in combination with '
                                                                              'other data.'},
                                                      'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                                                   'data_type': 'PII',
                                                                                   'priority': 'NICE_TO_HAVE',
                                                                                   'regulation': 'GDPR Art. 4 / India '
                                                                                                 'DPDP Act, 2023',
                                                                                   'risk_level': 'MEDIUM',
                                                                                   'threat': 'Discloses residence; '
                                                                                             'moderate risk on its '
                                                                                             'own, higher when '
                                                                                             'combined with a name.'}},
 'Employee Record / HR Application': {'BACKGROUND / CRIMINAL BACKGROUND CHECK RESULT': {'category': 'HR Sensitive Data',
                                                                                        'data_type': 'Other',
                                                                                        'priority': 'MUST_HAVE',
                                                                                        'regulation': 'GDPR Art. 10 '
                                                                                                      '(proximate: '
                                                                                                      'Art. 9)',
                                                                                        'risk_level': 'HIGH',
                                                                                        'threat': 'Severe employment, '
                                                                                                  'reputational, and '
                                                                                                  'discrimination risk '
                                                                                                  'if disclosed.'},
                                      'BANK ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                                              'data_type': 'Financial',
                                                              'priority': 'MUST_HAVE',
                                                              'regulation': 'FTC Safeguards Rule',
                                                              'risk_level': 'CRITICAL',
                                                              'threat': 'Financial fraud, unauthorized transfers, and '
                                                                        'account targeting.'},
                                      'CRIMINAL RECORD / CONVICTION DATA': {'category': 'HR Sensitive Data',
                                                                            'data_type': 'Other',
                                                                            'priority': 'MUST_HAVE',
                                                                            'regulation': 'GDPR Art. 10 (proximate: '
                                                                                          'Art. 9)',
                                                                            'risk_level': 'CRITICAL',
                                                                            'threat': 'Severe discrimination and '
                                                                                      'reputational harm; among the '
                                                                                      'most protected personal-data '
                                                                                      'categories in most legal '
                                                                                      'frameworks.'},
                                      'DATE OF BIRTH': {'category': 'Direct Identifier',
                                                        'data_type': 'PII',
                                                        'priority': 'MUST_HAVE',
                                                        'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                        'risk_level': 'MEDIUM',
                                                        'threat': 'Supports identity theft and may reveal protected '
                                                                  'characteristics (e.g., age-related).'},
                                      'DISABILITY STATUS': {'category': 'HR Sensitive Data',
                                                            'data_type': 'PHI/Other',
                                                            'priority': 'MUST_HAVE',
                                                            'regulation': 'GDPR Art. 9',
                                                            'risk_level': 'HIGH',
                                                            'threat': 'Discrimination and employment risk; also '
                                                                      'constitutes health data in most frameworks.'},
                                      'DISCIPLINARY ACTION DETAIL': {'category': 'HR Sensitive Data',
                                                                     'data_type': 'Other',
                                                                     'priority': 'NICE_TO_HAVE',
                                                                     'regulation': 'No specific statutory citation in '
                                                                                   'the supplied source set',
                                                                     'risk_level': 'MEDIUM',
                                                                     'threat': 'Reputational and employment harm; '
                                                                               'could affect future employment '
                                                                               'prospects if leaked.'},
                                      'EMAIL ADDRESS': {'category': 'Direct Identifier',
                                                        'data_type': 'PII',
                                                        'priority': 'NICE_TO_HAVE',
                                                        'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                        'risk_level': 'LOW',
                                                        'threat': 'Enables phishing and account-targeting against the '
                                                                  'employee.'},
                                      'EMPLOYEE ID NUMBER': {'category': 'Direct Identifier',
                                                             'data_type': 'PII',
                                                             'priority': 'NICE_TO_HAVE',
                                                             'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                             'risk_level': 'LOW',
                                                             'threat': 'Links records to a specific employee; lower '
                                                                       'standalone fraud risk than a government ID or '
                                                                       'SSN.'},
                                      'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                  'data_type': 'PII',
                                                                  'priority': 'MUST_HAVE',
                                                                  'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                                  'risk_level': 'HIGH',
                                                                  'threat': 'Enables identity theft and unauthorized '
                                                                            'disclosure of employment data.'},
                                      'PERFORMANCE RATING / REVIEW CONTENT': {'category': 'HR Sensitive Data',
                                                                              'data_type': 'Other',
                                                                              'priority': 'NICE_TO_HAVE',
                                                                              'regulation': 'No specific statutory '
                                                                                            'citation in the supplied '
                                                                                            'source set',
                                                                              'risk_level': 'MEDIUM',
                                                                              'threat': 'Reputational and employment '
                                                                                        'harm if disclosed to '
                                                                                        'unauthorized parties (e.g., '
                                                                                        'future employers, '
                                                                                        'colleagues).'},
                                      'PHONE NUMBER': {'category': 'Direct Identifier',
                                                       'data_type': 'PII',
                                                       'priority': 'NICE_TO_HAVE',
                                                       'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                       'risk_level': 'LOW',
                                                       'threat': 'Enables phishing/social engineering targeting the '
                                                                 'employee.'},
                                      'RACIAL OR ETHNIC ORIGIN DATA': {'category': 'HR Sensitive Data — Special '
                                                                                   'Category',
                                                                       'data_type': 'Other',
                                                                       'priority': 'MUST_HAVE',
                                                                       'regulation': 'GDPR Art. 9',
                                                                       'risk_level': 'CRITICAL',
                                                                       'threat': 'Severe discrimination risk; '
                                                                                 'explicitly protected as sensitive '
                                                                                 'personal data.'},
                                      'SOCIAL SECURITY NUMBER (SSN)': {'category': 'Government Identifier',
                                                                       'data_type': 'PII',
                                                                       'priority': 'MUST_HAVE',
                                                                       'regulation': 'NIST SP 800-122 / HIPAA Privacy '
                                                                                     'Rule (in health context)',
                                                                       'risk_level': 'CRITICAL',
                                                                       'threat': 'Identity theft, account fraud, '
                                                                                 'impersonation, and long-term privacy '
                                                                                 'harm — a US SSN cannot practically '
                                                                                 'be reissued.'},
                                      'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                                   'data_type': 'PII',
                                                                   'priority': 'MUST_HAVE',
                                                                   'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                                   'risk_level': 'MEDIUM',
                                                                   'threat': "Discloses an employee's residence; "
                                                                             'supports identity theft and '
                                                                             'physical-safety risk.'}},
 'Explanation of Benefits (EOB) / Medical Claim': {'ADMISSION / DISCHARGE / SERVICE DATE': {'category': 'Direct '
                                                                                                        'Identifier',
                                                                                            'data_type': 'PHI',
                                                                                            'priority': 'MUST_HAVE',
                                                                                            'regulation': 'HIPAA '
                                                                                                          'Privacy '
                                                                                                          'Rule',
                                                                                            'risk_level': 'MEDIUM',
                                                                                            'threat': 'Enables '
                                                                                                      're-identification '
                                                                                                      'when correlated '
                                                                                                      'with public '
                                                                                                      'event data '
                                                                                                      '(e.g., accident '
                                                                                                      'reports); '
                                                                                                      'listed HIPAA '
                                                                                                      'identifier.'},
                                                   'DATE OF BIRTH': {'category': 'Direct Identifier',
                                                                     'data_type': 'PII',
                                                                     'priority': 'MUST_HAVE',
                                                                     'regulation': 'HIPAA Privacy Rule',
                                                                     'risk_level': 'HIGH',
                                                                     'threat': 'HIPAA Safe Harbor identifier; '
                                                                               'strengthens patient re-identification '
                                                                               'when combined with other fields.'},
                                                   'DIAGNOSIS / MEDICAL CONDITION': {'category': 'Health/Clinical Data',
                                                                                     'data_type': 'PHI',
                                                                                     'priority': 'MUST_HAVE',
                                                                                     'regulation': 'HIPAA Privacy Rule',
                                                                                     'risk_level': 'CRITICAL',
                                                                                     'threat': 'Discrimination, '
                                                                                               'stigmatization, '
                                                                                               'employment/insurance '
                                                                                               'harm, and '
                                                                                               'medical-privacy harm '
                                                                                               'if disclosed.'},
                                                   'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                               'data_type': 'PII',
                                                                               'priority': 'MUST_HAVE',
                                                                               'regulation': 'HIPAA Privacy Rule',
                                                                               'risk_level': 'CRITICAL',
                                                                               'threat': 'Re-identifies an '
                                                                                         "individual's health record; "
                                                                                         'enables medical-identity '
                                                                                         'theft and targeted '
                                                                                         'harassment.'},
                                                   'HEALTH INSURANCE POLICY NUMBER': {'category': 'Direct Identifier',
                                                                                      'data_type': 'PHI',
                                                                                      'priority': 'MUST_HAVE',
                                                                                      'regulation': 'HIPAA Privacy '
                                                                                                    'Rule',
                                                                                      'risk_level': 'HIGH',
                                                                                      'threat': 'Enables fraudulent '
                                                                                                'insurance claims and '
                                                                                                'unauthorized access '
                                                                                                'to coverage details.'},
                                                   'HEALTH PLAN BENEFICIARY/MEMBER NUMBER': {'category': 'Direct '
                                                                                                         'Identifier',
                                                                                             'data_type': 'PHI',
                                                                                             'priority': 'MUST_HAVE',
                                                                                             'regulation': 'HIPAA '
                                                                                                           'Privacy '
                                                                                                           'Rule',
                                                                                             'risk_level': 'HIGH',
                                                                                             'threat': 'Enables '
                                                                                                       'medical '
                                                                                                       'insurance '
                                                                                                       'fraud and '
                                                                                                       'unauthorized '
                                                                                                       'claims filed '
                                                                                                       'against the '
                                                                                                       'beneficiary.'},
                                                   'MEDICAL CLAIM NUMBER': {'category': 'Direct Identifier',
                                                                            'data_type': 'PHI',
                                                                            'priority': 'NICE_TO_HAVE',
                                                                            'regulation': 'HIPAA Privacy Rule',
                                                                            'risk_level': 'MEDIUM',
                                                                            'threat': 'Links to a specific episode of '
                                                                                      'care and billing detail; '
                                                                                      'moderate '
                                                                                      'fraud/re-identification risk.'},
                                                   'MEDICAL RECORD NUMBER (MRN)': {'category': 'Direct Identifier',
                                                                                   'data_type': 'PHI',
                                                                                   'priority': 'MUST_HAVE',
                                                                                   'regulation': 'HIPAA Privacy Rule',
                                                                                   'risk_level': 'CRITICAL',
                                                                                   'threat': 'Directly links an '
                                                                                             'individual to their '
                                                                                             'entire clinical history; '
                                                                                             'enables medical-identity '
                                                                                             'theft and insurance '
                                                                                             'fraud.'},
                                                   'PHONE NUMBER': {'category': 'Direct Identifier',
                                                                    'data_type': 'PII',
                                                                    'priority': 'MUST_HAVE',
                                                                    'regulation': 'HIPAA Privacy Rule',
                                                                    'risk_level': 'MEDIUM',
                                                                    'threat': 'HIPAA Safe Harbor identifier; enables '
                                                                              'phishing/social engineering against a '
                                                                              'patient.'},
                                                   'PROCEDURE CODE / DESCRIPTION': {'category': 'Health/Clinical Data',
                                                                                    'data_type': 'PHI',
                                                                                    'priority': 'NICE_TO_HAVE',
                                                                                    'regulation': 'HIPAA Privacy Rule',
                                                                                    'risk_level': 'MEDIUM',
                                                                                    'threat': 'Discloses treatment '
                                                                                              'history; can imply a '
                                                                                              'condition '
                                                                                              '(re-identification '
                                                                                              'risk) and support '
                                                                                              'insurance fraud.'},
                                                   'SOCIAL SECURITY NUMBER (SSN)': {'category': 'Government Identifier',
                                                                                    'data_type': 'PII',
                                                                                    'priority': 'MUST_HAVE',
                                                                                    'regulation': 'NIST SP 800-122 / '
                                                                                                  'HIPAA Privacy Rule '
                                                                                                  '(in health context)',
                                                                                    'risk_level': 'CRITICAL',
                                                                                    'threat': 'Identity theft, account '
                                                                                              'fraud, impersonation, '
                                                                                              'and long-term privacy '
                                                                                              'harm — a US SSN cannot '
                                                                                              'practically be '
                                                                                              'reissued.'},
                                                   'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                                                'data_type': 'PII',
                                                                                'priority': 'MUST_HAVE',
                                                                                'regulation': 'HIPAA Privacy Rule',
                                                                                'risk_level': 'HIGH',
                                                                                'threat': 'HIPAA Safe Harbor '
                                                                                          'identifier; discloses where '
                                                                                          'a patient lives, raising '
                                                                                          'both privacy and '
                                                                                          'physical-safety risk.'},
                                                   'TREATING PROVIDER NAME / NPI NUMBER': {'category': 'Direct '
                                                                                                       'Identifier',
                                                                                           'data_type': 'PHI',
                                                                                           'priority': 'NICE_TO_HAVE',
                                                                                           'regulation': 'HIPAA '
                                                                                                         'Privacy Rule',
                                                                                           'risk_level': 'MEDIUM',
                                                                                           'threat': 'Discloses the '
                                                                                                     'treating '
                                                                                                     'clinician; can '
                                                                                                     'support social '
                                                                                                     'engineering '
                                                                                                     'against the '
                                                                                                     'practice, lower '
                                                                                                     'risk to the '
                                                                                                     'patient '
                                                                                                     'directly.'}},
 'Health Insurance Policy / Benefits Document': {'BANK ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                                                         'data_type': 'Financial',
                                                                         'priority': 'MUST_HAVE',
                                                                         'regulation': 'FTC Safeguards Rule',
                                                                         'risk_level': 'HIGH',
                                                                         'threat': 'Direct financial-fraud and '
                                                                                   'account-takeover risk if premium '
                                                                                   'auto-pay banking details are '
                                                                                   'exposed.'},
                                                 'COMPANY / EMPLOYER NAME': {'category': 'Administrative/Structural '
                                                                                         'Metadata',
                                                                             'data_type': 'Other',
                                                                             'priority': 'DROP',
                                                                             'regulation': 'N/A',
                                                                             'risk_level': 'MEDIUM',
                                                                             'threat': ''},
                                                 'COVERAGE DATE': {'category': 'Administrative Identifier',
                                                                   'data_type': 'PHI',
                                                                   'priority': 'NICE_TO_HAVE',
                                                                   'regulation': 'HIPAA Privacy Rule',
                                                                   'risk_level': 'MEDIUM',
                                                                   'threat': 'Reveals enrollment timeline for a '
                                                                             'specific individual; lower standalone '
                                                                             're-identification value than a direct '
                                                                             'identifier.'},
                                                 'DATE OF BIRTH': {'category': 'Direct Identifier',
                                                                   'data_type': 'PHI',
                                                                   'priority': 'MUST_HAVE',
                                                                   'regulation': 'HIPAA Privacy Rule',
                                                                   'risk_level': 'HIGH',
                                                                   'threat': 'Combined with name, enables identity '
                                                                             'verification bypass and medical-identity '
                                                                             'theft.'},
                                                 'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                             'data_type': 'PHI',
                                                                             'priority': 'MUST_HAVE',
                                                                             'regulation': 'HIPAA Privacy Rule',
                                                                             'risk_level': 'HIGH',
                                                                             'threat': 'Identifies covered family '
                                                                                       'members, including minors, '
                                                                                       'tied to the same health-plan '
                                                                                       'record.'},
                                                 'HEALTH PLAN BENEFICIARY/MEMBER NUMBER': {'category': 'Direct '
                                                                                                       'Identifier',
                                                                                           'data_type': 'PHI',
                                                                                           'priority': 'MUST_HAVE',
                                                                                           'regulation': 'HIPAA '
                                                                                                         'Privacy Rule',
                                                                                           'risk_level': 'HIGH',
                                                                                           'threat': 'Uniquely '
                                                                                                     'identifies the '
                                                                                                     'enrollee within '
                                                                                                     'the plan; '
                                                                                                     'enables '
                                                                                                     'unauthorized '
                                                                                                     'benefits access '
                                                                                                     'and '
                                                                                                     'medical-identity '
                                                                                                     'theft.'},
                                                 'PHONE NUMBER': {'category': 'Direct Identifier',
                                                                  'data_type': 'PHI',
                                                                  'priority': 'MUST_HAVE',
                                                                  'regulation': 'HIPAA Privacy Rule',
                                                                  'risk_level': 'MEDIUM',
                                                                  'threat': 'Enables social engineering, phishing, and '
                                                                            'unwanted contact tied to a known '
                                                                            'health-plan enrollee.'},
                                                 'PLAN NAME': {'category': 'Administrative/Structural Metadata',
                                                               'data_type': 'Other',
                                                               'priority': 'DROP',
                                                               'regulation': 'N/A',
                                                               'risk_level': 'MEDIUM',
                                                               'threat': ''},
                                                 'PREMIUM AMOUNT': {'category': 'Financial Data',
                                                                    'data_type': 'PII/Financial',
                                                                    'priority': 'NICE_TO_HAVE',
                                                                    'regulation': 'FTC Safeguards Rule',
                                                                    'risk_level': 'MEDIUM',
                                                                    'threat': 'Reveals personal financial obligation '
                                                                              'tied to an identifiable enrollee; lower '
                                                                              'breach impact than an account number.'},
                                                 'SOCIAL SECURITY NUMBER (SSN)': {'category': 'Government Identifier',
                                                                                  'data_type': 'PII',
                                                                                  'priority': 'MUST_HAVE',
                                                                                  'regulation': 'NIST SP 800-122 / '
                                                                                                'HIPAA Privacy Rule '
                                                                                                '(in health context)',
                                                                                  'risk_level': 'CRITICAL',
                                                                                  'threat': 'Identity theft, fraud, '
                                                                                            'and impersonation; SSN is '
                                                                                            'a high-value, '
                                                                                            'standalone-exploitable '
                                                                                            'identifier.'},
                                                 'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                                              'data_type': 'PHI',
                                                                              'priority': 'MUST_HAVE',
                                                                              'regulation': 'HIPAA Privacy Rule',
                                                                              'risk_level': 'HIGH',
                                                                              'threat': 'Enables physical-world '
                                                                                        'location of the individual; '
                                                                                        'HIPAA Safe Harbor geographic '
                                                                                        'identifier.'}},
 'Healthcare Data Breach Notification Letter': {'BOILERPLATE / DISCLAIMER TEXT': {'category': 'Administrative/Structural '
                                                                                              'Metadata',
                                                                                  'data_type': 'Other',
                                                                                  'priority': 'DROP',
                                                                                  'regulation': 'N/A',
                                                                                  'risk_level': 'MEDIUM',
                                                                                  'threat': ''},
                                                'BREACH INCIDENT DESCRIPTION': {'category': 'Administrative/Structural '
                                                                                            'Metadata',
                                                                                'data_type': 'Other',
                                                                                'priority': 'NICE_TO_HAVE',
                                                                                'regulation': 'HIPAA Privacy Rule',
                                                                                'risk_level': 'LOW',
                                                                                'threat': 'Organizational/event-level '
                                                                                          'information; useful context '
                                                                                          'but does not by itself '
                                                                                          'identify the individual or '
                                                                                          'disclose their personal '
                                                                                          'health information.'},
                                                'BREACHED DATA ELEMENT DESCRIPTION': {'category': 'Health/Clinical '
                                                                                                  'Data',
                                                                                      'data_type': 'PHI',
                                                                                      'priority': 'MUST_HAVE',
                                                                                      'regulation': 'HIPAA Privacy '
                                                                                                    'Rule',
                                                                                      'risk_level': 'CRITICAL',
                                                                                      'threat': 'Functions as an '
                                                                                                'inline inventory of '
                                                                                                'exactly which '
                                                                                                'sensitive elements '
                                                                                                'about this individual '
                                                                                                'were exposed; '
                                                                                                're-exposing this text '
                                                                                                'is itself a secondary '
                                                                                                'disclosure of the '
                                                                                                'same sensitive '
                                                                                                'facts.'},
                                                'COMPANY / EMPLOYER NAME': {'category': 'Administrative/Structural '
                                                                                        'Metadata',
                                                                            'data_type': 'Other',
                                                                            'priority': 'DROP',
                                                                            'regulation': 'N/A',
                                                                            'risk_level': 'MEDIUM',
                                                                            'threat': ''},
                                                'ENROLLMENT/ACTIVATION CODE': {'category': 'Security Credential',
                                                                               'data_type': 'Credential',
                                                                               'priority': 'MUST_HAVE',
                                                                               'regulation': 'No specific statutory '
                                                                                             'citation in the supplied '
                                                                                             'source set',
                                                                               'risk_level': 'HIGH',
                                                                               'threat': 'A unique code tied to one '
                                                                                         'specific recipient that '
                                                                                         'grants enrollment in a '
                                                                                         'remediation service; '
                                                                                         'exposure enables an attacker '
                                                                                         "to claim the victim's free "
                                                                                         'credit-monitoring benefit or '
                                                                                         'pivot into further identity '
                                                                                         'fraud.'},
                                                'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                            'data_type': 'PHI',
                                                                            'priority': 'MUST_HAVE',
                                                                            'regulation': 'HIPAA Privacy Rule',
                                                                            'risk_level': 'CRITICAL',
                                                                            'threat': 'Directly identifies the breach '
                                                                                      'victim; combined with the '
                                                                                      'described breached data, '
                                                                                      'enables medical-identity theft '
                                                                                      'and targeted fraud against a '
                                                                                      'known-vulnerable individual.'},
                                                'HEALTH PLAN BENEFICIARY/MEMBER NUMBER': {'category': 'Direct '
                                                                                                      'Identifier',
                                                                                          'data_type': 'PHI',
                                                                                          'priority': 'MUST_HAVE',
                                                                                          'regulation': 'HIPAA Privacy '
                                                                                                        'Rule',
                                                                                          'risk_level': 'HIGH',
                                                                                          'threat': 'Enables '
                                                                                                    'unauthorized '
                                                                                                    'benefits access; '
                                                                                                    'part of the '
                                                                                                    'inline '
                                                                                                    'breach-content '
                                                                                                    'description.'},
                                                'MEDICAL RECORD NUMBER (MRN)': {'category': 'Direct Identifier',
                                                                                'data_type': 'PHI',
                                                                                'priority': 'MUST_HAVE',
                                                                                'regulation': 'HIPAA Privacy Rule',
                                                                                'risk_level': 'CRITICAL',
                                                                                'threat': 'Uniquely links the '
                                                                                          'individual to their full '
                                                                                          'clinical record; frequently '
                                                                                          'cited in the letter as one '
                                                                                          'of the breached elements or '
                                                                                          "as the letter's own "
                                                                                          'identity-verification '
                                                                                          'reference.'},
                                                'ORGANIZATION CONTACT INFO': {'category': 'Administrative/Structural '
                                                                                          'Metadata',
                                                                              'data_type': 'Other',
                                                                              'priority': 'DROP',
                                                                              'regulation': 'N/A',
                                                                              'risk_level': 'MEDIUM',
                                                                              'threat': ''},
                                                'SOCIAL SECURITY NUMBER (SSN)': {'category': 'Government Identifier',
                                                                                 'data_type': 'PII',
                                                                                 'priority': 'MUST_HAVE',
                                                                                 'regulation': 'NIST SP 800-122 / '
                                                                                               'HIPAA Privacy Rule (in '
                                                                                               'health context)',
                                                                                 'risk_level': 'CRITICAL',
                                                                                 'threat': 'Identity theft; '
                                                                                           'impersonation; fraud.'},
                                                'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                                             'data_type': 'PHI',
                                                                             'priority': 'MUST_HAVE',
                                                                             'regulation': 'HIPAA Privacy Rule',
                                                                             'risk_level': 'HIGH',
                                                                             'threat': 'Enables physical-world '
                                                                                       'location of a known breach '
                                                                                       'victim.'}},
 'Identity Document (Passport / Driver License / National ID / Visa)': {'DATE OF BIRTH': {'category': 'Direct '
                                                                                                      'Identifier',
                                                                                          'data_type': 'PII',
                                                                                          'priority': 'MUST_HAVE',
                                                                                          'regulation': 'NIST SP '
                                                                                                        '800-122 (PII) '
                                                                                                        '/ GDPR Art. 4',
                                                                                          'risk_level': 'HIGH',
                                                                                          'threat': 'Strengthens '
                                                                                                    'identity-theft '
                                                                                                    'and impersonation '
                                                                                                    'risk when paired '
                                                                                                    'with a government '
                                                                                                    'ID number.'},
                                                                        "DRIVER'S LICENSE NUMBER": {'category': 'Government '
                                                                                                                'Identifier',
                                                                                                    'data_type': 'PII',
                                                                                                    'priority': 'MUST_HAVE',
                                                                                                    'regulation': 'NIST '
                                                                                                                  'SP '
                                                                                                                  '800-122 '
                                                                                                                  '/ '
                                                                                                                  'GDPR '
                                                                                                                  'Art. '
                                                                                                                  '4',
                                                                                                    'risk_level': 'HIGH',
                                                                                                    'threat': 'Enables '
                                                                                                              'identity '
                                                                                                              'theft '
                                                                                                              'and '
                                                                                                              'fraudulent '
                                                                                                              'use as '
                                                                                                              'a '
                                                                                                              'secondary '
                                                                                                              'government '
                                                                                                              'ID.'},
                                                                        'FULL NAME / PERSON NAME': {'category': 'Direct '
                                                                                                                'Identifier',
                                                                                                    'data_type': 'PII',
                                                                                                    'priority': 'MUST_HAVE',
                                                                                                    'regulation': 'NIST '
                                                                                                                  'SP '
                                                                                                                  '800-122 '
                                                                                                                  '(PII) '
                                                                                                                  '/ '
                                                                                                                  'GDPR '
                                                                                                                  'Art. '
                                                                                                                  '4',
                                                                                                    'risk_level': 'CRITICAL',
                                                                                                    'threat': 'Enables '
                                                                                                              'impersonation '
                                                                                                              'and '
                                                                                                              'fraudulent '
                                                                                                              'use of '
                                                                                                              'a '
                                                                                                              'government-issued '
                                                                                                              'credential.'},
                                                                        'NATIONAL / GOVERNMENT ID NUMBER (GENERIC, NON-US/NON-INDIA)': {'category': 'Government '
                                                                                                                                                    'Identifier',
                                                                                                                                        'data_type': 'PII',
                                                                                                                                        'priority': 'MUST_HAVE',
                                                                                                                                        'regulation': 'GDPR '
                                                                                                                                                      'Art. '
                                                                                                                                                      '4 '
                                                                                                                                                      '/ '
                                                                                                                                                      'NIST '
                                                                                                                                                      'SP '
                                                                                                                                                      '800-122',
                                                                                                                                        'risk_level': 'HIGH',
                                                                                                                                        'threat': 'Enables '
                                                                                                                                                  'identity '
                                                                                                                                                  'theft '
                                                                                                                                                  'and '
                                                                                                                                                  'impersonation; '
                                                                                                                                                  'jurisdiction-specific '
                                                                                                                                                  'format '
                                                                                                                                                  'but '
                                                                                                                                                  'universally '
                                                                                                                                                  'a '
                                                                                                                                                  'strong '
                                                                                                                                                  'identity '
                                                                                                                                                  'anchor.'},
                                                                        'PASSPORT NUMBER': {'category': 'Government '
                                                                                                        'Identifier',
                                                                                            'data_type': 'PII',
                                                                                            'priority': 'MUST_HAVE',
                                                                                            'regulation': 'NIST SP '
                                                                                                          '800-122 / '
                                                                                                          'GDPR Art. 4',
                                                                                            'risk_level': 'CRITICAL',
                                                                                            'threat': 'Enables '
                                                                                                      'cross-border '
                                                                                                      'identity fraud, '
                                                                                                      'human-trafficking '
                                                                                                      'document '
                                                                                                      'forgery, and '
                                                                                                      'impersonation.'},
                                                                        'PHOTOGRAPH / FACIAL IMAGE': {'category': 'Direct '
                                                                                                                  'Identifier '
                                                                                                                  '/ '
                                                                                                                  'Biometric-Adjacent',
                                                                                                      'data_type': 'PII',
                                                                                                      'priority': 'MUST_HAVE',
                                                                                                      'regulation': 'HIPAA '
                                                                                                                    'Privacy '
                                                                                                                    'Rule '
                                                                                                                    '/ '
                                                                                                                    'GDPR '
                                                                                                                    'Art. '
                                                                                                                    '4',
                                                                                                      'risk_level': 'HIGH',
                                                                                                      'threat': 'A '
                                                                                                                'comparable '
                                                                                                                'identifier '
                                                                                                                'under '
                                                                                                                'HIPAA '
                                                                                                                'Safe '
                                                                                                                'Harbor '
                                                                                                                '("full '
                                                                                                                'face '
                                                                                                                'photographic '
                                                                                                                'images"); '
                                                                                                                'enables '
                                                                                                                'direct '
                                                                                                                'visual '
                                                                                                                'identification.'},
                                                                        'SIGNATURE': {'category': 'Direct Identifier',
                                                                                      'data_type': 'PII',
                                                                                      'priority': 'MUST_HAVE',
                                                                                      'regulation': 'NIST SP 800-122 '
                                                                                                    '(PII) / GDPR Art. '
                                                                                                    '4',
                                                                                      'risk_level': 'HIGH',
                                                                                      'threat': 'A reference signature '
                                                                                                'enables forgery of '
                                                                                                'the credential '
                                                                                                "holder's "
                                                                                                'authorization '
                                                                                                'elsewhere.'},
                                                                        'STREET / MAILING ADDRESS': {'category': 'Direct '
                                                                                                                 'Identifier',
                                                                                                     'data_type': 'PII',
                                                                                                     'priority': 'MUST_HAVE',
                                                                                                     'regulation': 'NIST '
                                                                                                                   'SP '
                                                                                                                   '800-122 '
                                                                                                                   '(PII) '
                                                                                                                   '/ '
                                                                                                                   'GDPR '
                                                                                                                   'Art. '
                                                                                                                   '4',
                                                                                                     'risk_level': 'HIGH',
                                                                                                     'threat': 'Printed '
                                                                                                               'on '
                                                                                                               'government '
                                                                                                               'credentials; '
                                                                                                               'discloses '
                                                                                                               'residence '
                                                                                                               'and '
                                                                                                               'supports '
                                                                                                               'impersonation.'},
                                                                        'VEHICLE IDENTIFIER / LICENSE PLATE NUMBER': {'category': 'Quasi-Identifier',
                                                                                                                      'data_type': 'PII',
                                                                                                                      'priority': 'NICE_TO_HAVE',
                                                                                                                      'regulation': 'GDPR '
                                                                                                                                    'Art. '
                                                                                                                                    '4 '
                                                                                                                                    '/ '
                                                                                                                                    'NIST '
                                                                                                                                    'SP '
                                                                                                                                    '800-122',
                                                                                                                      'risk_level': 'MEDIUM',
                                                                                                                      'threat': 'Traceable '
                                                                                                                                'to '
                                                                                                                                'a '
                                                                                                                                'registered '
                                                                                                                                'owner; '
                                                                                                                                'supports '
                                                                                                                                'physical '
                                                                                                                                'tracking/stalking '
                                                                                                                                'risk '
                                                                                                                                'but '
                                                                                                                                'generally '
                                                                                                                                'lower '
                                                                                                                                'direct '
                                                                                                                                'fraud '
                                                                                                                                'risk '
                                                                                                                                'than '
                                                                                                                                'a '
                                                                                                                                'government '
                                                                                                                                'ID.'},
                                                                        'VISA / IMMIGRATION DOCUMENT NUMBER': {'category': 'Government '
                                                                                                                           'Identifier',
                                                                                                               'data_type': 'PII',
                                                                                                               'priority': 'MUST_HAVE',
                                                                                                               'regulation': 'NIST '
                                                                                                                             'SP '
                                                                                                                             '800-122 '
                                                                                                                             '/ '
                                                                                                                             'GDPR '
                                                                                                                             'Art. '
                                                                                                                             '4',
                                                                                                               'risk_level': 'HIGH',
                                                                                                               'threat': 'Enables '
                                                                                                                         'immigration '
                                                                                                                         'fraud '
                                                                                                                         'and '
                                                                                                                         'status-related '
                                                                                                                         'harm; '
                                                                                                                         'can '
                                                                                                                         'affect '
                                                                                                                         'an '
                                                                                                                         "individual's "
                                                                                                                         'legal '
                                                                                                                         'residency '
                                                                                                                         'status '
                                                                                                                         'if '
                                                                                                                         'misused.'}},
 'Imaging / Radiology Report': {'ADMISSION / DISCHARGE / SERVICE DATE': {'category': 'Direct Identifier',
                                                                         'data_type': 'PHI',
                                                                         'priority': 'MUST_HAVE',
                                                                         'regulation': 'HIPAA Privacy Rule',
                                                                         'risk_level': 'MEDIUM',
                                                                         'threat': 'Enables re-identification when '
                                                                                   'correlated with public event data '
                                                                                   '(e.g., accident reports); listed '
                                                                                   'HIPAA identifier.'},
                                'CT NUMBER / IMAGING TECHNICAL PARAMETER': {'category': 'Administrative/Structural '
                                                                                        'Metadata',
                                                                            'data_type': 'Other',
                                                                            'priority': 'DROP',
                                                                            'regulation': 'N/A',
                                                                            'risk_level': 'MEDIUM',
                                                                            'threat': 'None — a physical '
                                                                                      'measurement/scanner calibration '
                                                                                      'value, not a personal '
                                                                                      'identifier or health-status '
                                                                                      'disclosure.'},
                                'DATE OF BIRTH': {'category': 'Direct Identifier',
                                                  'data_type': 'PII',
                                                  'priority': 'MUST_HAVE',
                                                  'regulation': 'HIPAA Privacy Rule',
                                                  'risk_level': 'HIGH',
                                                  'threat': 'HIPAA Safe Harbor identifier; strengthens patient '
                                                            're-identification when combined with other fields.'},
                                'DIAGNOSIS / MEDICAL CONDITION': {'category': 'Health/Clinical Data',
                                                                  'data_type': 'PHI',
                                                                  'priority': 'MUST_HAVE',
                                                                  'regulation': 'HIPAA Privacy Rule',
                                                                  'risk_level': 'CRITICAL',
                                                                  'threat': 'Discrimination, stigmatization, '
                                                                            'employment/insurance harm, and '
                                                                            'medical-privacy harm if disclosed.'},
                                'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                            'data_type': 'PII',
                                                            'priority': 'MUST_HAVE',
                                                            'regulation': 'HIPAA Privacy Rule',
                                                            'risk_level': 'CRITICAL',
                                                            'threat': "Re-identifies an individual's health record; "
                                                                      'enables medical-identity theft and targeted '
                                                                      'harassment.'},
                                'IMAGING STUDY ID / ACCESSION NUMBER': {'category': 'Direct Identifier',
                                                                        'data_type': 'PHI',
                                                                        'priority': 'NICE_TO_HAVE',
                                                                        'regulation': 'HIPAA Privacy Rule',
                                                                        'risk_level': 'MEDIUM',
                                                                        'threat': 'Links to a specific imaging study; '
                                                                                  'moderate risk, mainly useful for '
                                                                                  'tracing back to the patient '
                                                                                  'record.'},
                                'MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER': {'category': 'Administrative/Structural '
                                                                                           'Metadata',
                                                                               'data_type': 'Other',
                                                                               'priority': 'DROP',
                                                                               'regulation': 'N/A',
                                                                               'risk_level': 'MEDIUM',
                                                                               'threat': 'None — identifies a '
                                                                                         'machine/asset, not a person; '
                                                                                         'occasionally relevant to '
                                                                                         'biomedical-device recall '
                                                                                         'workflows but not a privacy '
                                                                                         'target.'},
                                'MEDICAL RECORD NUMBER (MRN)': {'category': 'Direct Identifier',
                                                                'data_type': 'PHI',
                                                                'priority': 'MUST_HAVE',
                                                                'regulation': 'HIPAA Privacy Rule',
                                                                'risk_level': 'CRITICAL',
                                                                'threat': 'Directly links an individual to their '
                                                                          'entire clinical history; enables '
                                                                          'medical-identity theft and insurance '
                                                                          'fraud.'},
                                'TREATING PROVIDER NAME / NPI NUMBER': {'category': 'Direct Identifier',
                                                                        'data_type': 'PHI',
                                                                        'priority': 'NICE_TO_HAVE',
                                                                        'regulation': 'HIPAA Privacy Rule',
                                                                        'risk_level': 'MEDIUM',
                                                                        'threat': 'Discloses the treating clinician; '
                                                                                  'can support social engineering '
                                                                                  'against the practice, lower risk to '
                                                                                  'the patient directly.'}},
 'Investment / Brokerage Document': {'BANK ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                                             'data_type': 'Financial',
                                                             'priority': 'MUST_HAVE',
                                                             'regulation': 'FTC Safeguards Rule',
                                                             'risk_level': 'CRITICAL',
                                                             'threat': 'Financial fraud, unauthorized transfers, and '
                                                                       'account targeting.'},
                                     'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                 'data_type': 'PII',
                                                                 'priority': 'MUST_HAVE',
                                                                 'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. '
                                                                               '4',
                                                                 'risk_level': 'HIGH',
                                                                 'threat': 'Enables identity theft, account takeover, '
                                                                           'and social engineering when paired with '
                                                                           'account data.'},
                                     'INVESTMENT / BROKERAGE ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                                                               'data_type': 'Financial',
                                                                               'priority': 'MUST_HAVE',
                                                                               'regulation': 'FTC Safeguards Rule',
                                                                               'risk_level': 'HIGH',
                                                                               'threat': 'Enables unauthorized '
                                                                                         'trading, transfers, or '
                                                                                         'account takeover.'},
                                     'SECURITIES / PORTFOLIO HOLDINGS DETAIL': {'category': 'Financial Data',
                                                                                'data_type': 'Financial',
                                                                                'priority': 'NICE_TO_HAVE',
                                                                                'regulation': 'FTC Safeguards Rule',
                                                                                'risk_level': 'LOW',
                                                                                'threat': 'Discloses wealth/financial '
                                                                                          'profile, which can support '
                                                                                          'targeted fraud, but does '
                                                                                          'not itself enable account '
                                                                                          'takeover.'},
                                     'SOCIAL SECURITY NUMBER (SSN)': {'category': 'Government Identifier',
                                                                      'data_type': 'PII',
                                                                      'priority': 'MUST_HAVE',
                                                                      'regulation': 'NIST SP 800-122 / HIPAA Privacy '
                                                                                    'Rule (in health context)',
                                                                      'risk_level': 'CRITICAL',
                                                                      'threat': 'Identity theft, account fraud, '
                                                                                'impersonation, and long-term privacy '
                                                                                'harm — a US SSN cannot practically be '
                                                                                'reissued.'},
                                     'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                                  'data_type': 'PII',
                                                                  'priority': 'MUST_HAVE',
                                                                  'regulation': 'FTC Safeguards Rule (GLBA) / GDPR '
                                                                                'Art. 4',
                                                                  'risk_level': 'MEDIUM',
                                                                  'threat': 'Enables mail fraud, identity theft, and '
                                                                            'physical targeting when paired with '
                                                                            'financial data.'},
                                     'TRANSACTION HISTORY / AMOUNTS': {'category': 'Financial Data',
                                                                       'data_type': 'Financial',
                                                                       'priority': 'NICE_TO_HAVE',
                                                                       'regulation': 'GDPR Art. 4',
                                                                       'risk_level': 'LOW',
                                                                       'threat': 'Discloses spending '
                                                                                 'behavior/financial profile; '
                                                                                 'privacy-relevant but not '
                                                                                 'independently exploitable without '
                                                                                 'account credentials.'}},
 'Invoice / Purchase Order': {'BANK ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                                      'data_type': 'Financial',
                                                      'priority': 'MUST_HAVE',
                                                      'regulation': 'FTC Safeguards Rule',
                                                      'risk_level': 'CRITICAL',
                                                      'threat': 'Financial fraud, unauthorized transfers, and account '
                                                                'targeting.'},
                              'COMPANY / EMPLOYER NAME': {'category': 'Administrative/Structural Metadata',
                                                          'data_type': 'Other',
                                                          'priority': 'DROP',
                                                          'regulation': 'N/A',
                                                          'risk_level': 'MEDIUM',
                                                          'threat': 'None on its own — organizational data; only '
                                                                    'becomes privacy-relevant combined with an '
                                                                    'individual identifier already captured '
                                                                    'separately.'},
                              'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                          'data_type': 'PII',
                                                          'priority': 'MUST_HAVE',
                                                          'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                                          'risk_level': 'HIGH',
                                                          'threat': 'Enables identity theft, account takeover, and '
                                                                    'social engineering when paired with account '
                                                                    'data.'},
                              'INVOICE NUMBER': {'category': 'Administrative/Structural Metadata',
                                                 'data_type': 'Other',
                                                 'priority': 'DROP',
                                                 'regulation': 'N/A',
                                                 'risk_level': 'MEDIUM',
                                                 'threat': 'None — an internal business/accounting reference, not '
                                                           "linked to an individual's protected data."},
                              'LINE-ITEM PRODUCT/SERVICE DESCRIPTION': {'category': 'Administrative/Structural '
                                                                                    'Metadata',
                                                                        'data_type': 'Other',
                                                                        'priority': 'DROP',
                                                                        'regulation': 'N/A',
                                                                        'risk_level': 'MEDIUM',
                                                                        'threat': 'None — describes a purchased '
                                                                                  'product/service, not the '
                                                                                  'individual.'},
                              'PURCHASE ORDER NUMBER': {'category': 'Administrative/Structural Metadata',
                                                        'data_type': 'Other',
                                                        'priority': 'DROP',
                                                        'regulation': 'N/A',
                                                        'risk_level': 'MEDIUM',
                                                        'threat': 'None — internal procurement reference, not personal '
                                                                  'data.'},
                              'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                           'data_type': 'PII',
                                                           'priority': 'MUST_HAVE',
                                                           'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                                           'risk_level': 'MEDIUM',
                                                           'threat': 'Enables mail fraud, identity theft, and physical '
                                                                     'targeting when paired with financial data.'},
                              'TRANSACTION HISTORY / AMOUNTS': {'category': 'Financial Data',
                                                                'data_type': 'Financial',
                                                                'priority': 'NICE_TO_HAVE',
                                                                'regulation': 'GDPR Art. 4',
                                                                'risk_level': 'LOW',
                                                                'threat': 'Discloses spending behavior/financial '
                                                                          'profile; privacy-relevant but not '
                                                                          'independently exploitable without account '
                                                                          'credentials.'}},
 'KYC Document': {'AADHAAR NUMBER (INDIA)': {'category': 'Government Identifier',
                                             'data_type': 'PII',
                                             'priority': 'MUST_HAVE',
                                             'regulation': 'Digital Personal Data Protection Act, 2023',
                                             'risk_level': 'CRITICAL',
                                             'threat': 'Enables identity theft and fraudulent enrollment across '
                                                       "India's linked digital-identity ecosystem (banking, telecom, "
                                                       'welfare).'},
                  'DATE OF BIRTH': {'category': 'Direct Identifier',
                                    'data_type': 'PII',
                                    'priority': 'MUST_HAVE',
                                    'regulation': 'NIST SP 800-122 (PII) / GDPR Art. 4',
                                    'risk_level': 'HIGH',
                                    'threat': 'Strengthens identity-theft and impersonation risk when paired with a '
                                              'government ID number.'},
                  "DRIVER'S LICENSE NUMBER": {'category': 'Government Identifier',
                                              'data_type': 'PII',
                                              'priority': 'MUST_HAVE',
                                              'regulation': 'NIST SP 800-122 / GDPR Art. 4',
                                              'risk_level': 'HIGH',
                                              'threat': 'Enables identity theft and fraudulent use as a secondary '
                                                        'government ID.'},
                  'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                              'data_type': 'PII',
                                              'priority': 'MUST_HAVE',
                                              'regulation': 'NIST SP 800-122 (PII) / GDPR Art. 4',
                                              'risk_level': 'CRITICAL',
                                              'threat': 'Enables impersonation and fraudulent use of a '
                                                        'government-issued credential.'},
                  'NATIONAL / GOVERNMENT ID NUMBER (GENERIC, NON-US/NON-INDIA)': {'category': 'Government Identifier',
                                                                                  'data_type': 'PII',
                                                                                  'priority': 'MUST_HAVE',
                                                                                  'regulation': 'GDPR Art. 4 / NIST SP '
                                                                                                '800-122',
                                                                                  'risk_level': 'HIGH',
                                                                                  'threat': 'Enables identity theft '
                                                                                            'and impersonation; '
                                                                                            'jurisdiction-specific '
                                                                                            'format but universally a '
                                                                                            'strong identity anchor.'},
                  'PASSPORT NUMBER': {'category': 'Government Identifier',
                                      'data_type': 'PII',
                                      'priority': 'MUST_HAVE',
                                      'regulation': 'NIST SP 800-122 / GDPR Art. 4',
                                      'risk_level': 'CRITICAL',
                                      'threat': 'Enables cross-border identity fraud, human-trafficking document '
                                                'forgery, and impersonation.'},
                  'PERMANENT ACCOUNT NUMBER — INCOME TAX (INDIA)': {'category': 'Government Identifier',
                                                                    'data_type': 'PII/Financial',
                                                                    'priority': 'MUST_HAVE',
                                                                    'regulation': 'Digital Personal Data Protection '
                                                                                  'Act, 2023',
                                                                    'risk_level': 'HIGH',
                                                                    'threat': 'Enables tax fraud and identity theft; '
                                                                              'widely used as a financial KYC '
                                                                              'identifier in India.'},
                  'PHOTOGRAPH / FACIAL IMAGE': {'category': 'Direct Identifier / Biometric-Adjacent',
                                                'data_type': 'PII',
                                                'priority': 'MUST_HAVE',
                                                'regulation': 'HIPAA Privacy Rule / GDPR Art. 4',
                                                'risk_level': 'HIGH',
                                                'threat': 'A comparable identifier under HIPAA Safe Harbor ("full face '
                                                          'photographic images"); enables direct visual '
                                                          'identification.'},
                  'SIGNATURE': {'category': 'Direct Identifier',
                                'data_type': 'PII',
                                'priority': 'MUST_HAVE',
                                'regulation': 'NIST SP 800-122 (PII) / GDPR Art. 4',
                                'risk_level': 'HIGH',
                                'threat': "A reference signature enables forgery of the credential holder's "
                                          'authorization elsewhere.'},
                  'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                               'data_type': 'PII',
                                               'priority': 'MUST_HAVE',
                                               'regulation': 'NIST SP 800-122 (PII) / GDPR Art. 4',
                                               'risk_level': 'HIGH',
                                               'threat': 'Printed on government credentials; discloses residence and '
                                                         'supports impersonation.'}},
 'Lab Report / Pathology Report': {'ADMISSION / DISCHARGE / SERVICE DATE': {'category': 'Direct Identifier',
                                                                            'data_type': 'PHI',
                                                                            'priority': 'MUST_HAVE',
                                                                            'regulation': 'HIPAA Privacy Rule',
                                                                            'risk_level': 'MEDIUM',
                                                                            'threat': 'Enables re-identification when '
                                                                                      'correlated with public event '
                                                                                      'data (e.g., accident reports); '
                                                                                      'listed HIPAA identifier.'},
                                   'DATE OF BIRTH': {'category': 'Direct Identifier',
                                                     'data_type': 'PII',
                                                     'priority': 'MUST_HAVE',
                                                     'regulation': 'HIPAA Privacy Rule',
                                                     'risk_level': 'HIGH',
                                                     'threat': 'HIPAA Safe Harbor identifier; strengthens patient '
                                                               're-identification when combined with other fields.'},
                                   'DIAGNOSIS / MEDICAL CONDITION': {'category': 'Health/Clinical Data',
                                                                     'data_type': 'PHI',
                                                                     'priority': 'MUST_HAVE',
                                                                     'regulation': 'HIPAA Privacy Rule',
                                                                     'risk_level': 'CRITICAL',
                                                                     'threat': 'Discrimination, stigmatization, '
                                                                               'employment/insurance harm, and '
                                                                               'medical-privacy harm if disclosed.'},
                                   'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                               'data_type': 'PII',
                                                               'priority': 'MUST_HAVE',
                                                               'regulation': 'HIPAA Privacy Rule',
                                                               'risk_level': 'CRITICAL',
                                                               'threat': "Re-identifies an individual's health record; "
                                                                         'enables medical-identity theft and targeted '
                                                                         'harassment.'},
                                   'LAB TEST RESULT / VALUE': {'category': 'Health/Clinical Data',
                                                               'data_type': 'PHI',
                                                               'priority': 'NICE_TO_HAVE',
                                                               'regulation': 'HIPAA Privacy Rule',
                                                               'risk_level': 'MEDIUM',
                                                               'threat': 'Discloses physiological/health status; '
                                                                         'moderate standalone risk, higher when linked '
                                                                         'to identity.'},
                                   'MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER': {'category': 'Administrative/Structural '
                                                                                              'Metadata',
                                                                                  'data_type': 'Other',
                                                                                  'priority': 'DROP',
                                                                                  'regulation': 'N/A',
                                                                                  'risk_level': 'MEDIUM',
                                                                                  'threat': 'None — identifies a '
                                                                                            'machine/asset, not a '
                                                                                            'person; occasionally '
                                                                                            'relevant to '
                                                                                            'biomedical-device recall '
                                                                                            'workflows but not a '
                                                                                            'privacy target.'},
                                   'MEDICAL RECORD NUMBER (MRN)': {'category': 'Direct Identifier',
                                                                   'data_type': 'PHI',
                                                                   'priority': 'MUST_HAVE',
                                                                   'regulation': 'HIPAA Privacy Rule',
                                                                   'risk_level': 'CRITICAL',
                                                                   'threat': 'Directly links an individual to their '
                                                                             'entire clinical history; enables '
                                                                             'medical-identity theft and insurance '
                                                                             'fraud.'},
                                   'TREATING PROVIDER NAME / NPI NUMBER': {'category': 'Direct Identifier',
                                                                           'data_type': 'PHI',
                                                                           'priority': 'NICE_TO_HAVE',
                                                                           'regulation': 'HIPAA Privacy Rule',
                                                                           'risk_level': 'MEDIUM',
                                                                           'threat': 'Discloses the treating '
                                                                                     'clinician; can support social '
                                                                                     'engineering against the '
                                                                                     'practice, lower risk to the '
                                                                                     'patient directly.'}},
 'Litigation Document / Regulatory Filing / Compliance Document': {'ATTORNEY-CLIENT PRIVILEGE NOTATION': {'category': 'Administrative/Structural '
                                                                                                                      'Metadata',
                                                                                                          'data_type': 'Other',
                                                                                                          'priority': 'DROP',
                                                                                                          'regulation': 'N/A',
                                                                                                          'risk_level': 'MEDIUM',
                                                                                                          'threat': 'None '
                                                                                                                    '— '
                                                                                                                    'a '
                                                                                                                    'legal-handling '
                                                                                                                    'label, '
                                                                                                                    'not '
                                                                                                                    'personal '
                                                                                                                    'data '
                                                                                                                    'itself, '
                                                                                                                    'though '
                                                                                                                    'it '
                                                                                                                    'should '
                                                                                                                    'still '
                                                                                                                    'trigger '
                                                                                                                    'a '
                                                                                                                    'separate '
                                                                                                                    'legal-hold/privilege '
                                                                                                                    'workflow.'},
                                                                   'CASE / DOCKET / REFERENCE NUMBER': {'category': 'Administrative '
                                                                                                                    'Identifier',
                                                                                                        'data_type': 'Other',
                                                                                                        'priority': 'NICE_TO_HAVE',
                                                                                                        'regulation': 'No '
                                                                                                                      'specific '
                                                                                                                      'statutory '
                                                                                                                      'citation '
                                                                                                                      'in '
                                                                                                                      'the '
                                                                                                                      'supplied '
                                                                                                                      'source '
                                                                                                                      'set',
                                                                                                        'risk_level': 'MEDIUM',
                                                                                                        'threat': 'Links '
                                                                                                                  'an '
                                                                                                                  'individual '
                                                                                                                  'to '
                                                                                                                  'a '
                                                                                                                  'specific '
                                                                                                                  'legal '
                                                                                                                  'or '
                                                                                                                  'regulatory '
                                                                                                                  'matter, '
                                                                                                                  'which '
                                                                                                                  'can '
                                                                                                                  'itself '
                                                                                                                  'be '
                                                                                                                  'sensitive '
                                                                                                                  '(e.g., '
                                                                                                                  'litigation, '
                                                                                                                  'AML '
                                                                                                                  'case).'},
                                                                   'COURT / JURISDICTION NAME': {'category': 'Administrative/Structural '
                                                                                                             'Metadata',
                                                                                                 'data_type': 'Other',
                                                                                                 'priority': 'DROP',
                                                                                                 'regulation': 'N/A',
                                                                                                 'risk_level': 'MEDIUM',
                                                                                                 'threat': 'None — '
                                                                                                           'identifies '
                                                                                                           'a public '
                                                                                                           'institution, '
                                                                                                           'not the '
                                                                                                           'individual.'},
                                                                   'CRIMINAL RECORD / CONVICTION DATA': {'category': 'HR '
                                                                                                                     'Sensitive '
                                                                                                                     'Data',
                                                                                                         'data_type': 'Other',
                                                                                                         'priority': 'MUST_HAVE',
                                                                                                         'regulation': 'GDPR '
                                                                                                                       'Art. '
                                                                                                                       '10 '
                                                                                                                       '(proximate: '
                                                                                                                       'Art. '
                                                                                                                       '9)',
                                                                                                         'risk_level': 'CRITICAL',
                                                                                                         'threat': 'Severe '
                                                                                                                   'discrimination '
                                                                                                                   'and '
                                                                                                                   'reputational '
                                                                                                                   'harm; '
                                                                                                                   'among '
                                                                                                                   'the '
                                                                                                                   'most '
                                                                                                                   'protected '
                                                                                                                   'personal-data '
                                                                                                                   'categories '
                                                                                                                   'in '
                                                                                                                   'most '
                                                                                                                   'legal '
                                                                                                                   'frameworks.'},
                                                                   'FULL NAME / PERSON NAME': {'category': 'Direct '
                                                                                                           'Identifier',
                                                                                               'data_type': 'PII',
                                                                                               'priority': 'MUST_HAVE',
                                                                                               'regulation': 'GDPR '
                                                                                                             'Art. 4 / '
                                                                                                             'NIST SP '
                                                                                                             '800-122',
                                                                                               'risk_level': 'HIGH',
                                                                                               'threat': 'Discloses a '
                                                                                                         "party's "
                                                                                                         'involvement '
                                                                                                         'in a legal '
                                                                                                         'matter; '
                                                                                                         'enables '
                                                                                                         'identity '
                                                                                                         'theft when '
                                                                                                         'combined '
                                                                                                         'with case '
                                                                                                         'data.'},
                                                                   'SOCIAL SECURITY NUMBER (SSN)': {'category': 'Government '
                                                                                                                'Identifier',
                                                                                                    'data_type': 'PII',
                                                                                                    'priority': 'MUST_HAVE',
                                                                                                    'regulation': 'NIST '
                                                                                                                  'SP '
                                                                                                                  '800-122 '
                                                                                                                  '/ '
                                                                                                                  'HIPAA '
                                                                                                                  'Privacy '
                                                                                                                  'Rule '
                                                                                                                  '(in '
                                                                                                                  'health '
                                                                                                                  'context)',
                                                                                                    'risk_level': 'CRITICAL',
                                                                                                    'threat': 'Identity '
                                                                                                              'theft, '
                                                                                                              'account '
                                                                                                              'fraud, '
                                                                                                              'impersonation, '
                                                                                                              'and '
                                                                                                              'long-term '
                                                                                                              'privacy '
                                                                                                              'harm — '
                                                                                                              'a US '
                                                                                                              'SSN '
                                                                                                              'cannot '
                                                                                                              'practically '
                                                                                                              'be '
                                                                                                              'reissued.'},
                                                                   'STREET / MAILING ADDRESS': {'category': 'Direct '
                                                                                                            'Identifier',
                                                                                                'data_type': 'PII',
                                                                                                'priority': 'NICE_TO_HAVE',
                                                                                                'regulation': 'GDPR '
                                                                                                              'Art. 4 '
                                                                                                              '/ NIST '
                                                                                                              'SP '
                                                                                                              '800-122',
                                                                                                'risk_level': 'MEDIUM',
                                                                                                'threat': 'Discloses a '
                                                                                                          "party's "
                                                                                                          'residence/place '
                                                                                                          'of business '
                                                                                                          'tied to a '
                                                                                                          'legal '
                                                                                                          'matter.'}},
 'Loan / Mortgage Document': {'BANK ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                                      'data_type': 'Financial',
                                                      'priority': 'MUST_HAVE',
                                                      'regulation': 'FTC Safeguards Rule',
                                                      'risk_level': 'CRITICAL',
                                                      'threat': 'Financial fraud, unauthorized transfers, and account '
                                                                'targeting.'},
                              'CREDIT SCORE': {'category': 'Financial Account Data',
                                               'data_type': 'Financial',
                                               'priority': 'NICE_TO_HAVE',
                                               'regulation': 'FTC Safeguards Rule',
                                               'risk_level': 'MEDIUM',
                                               'threat': 'Discloses financial standing; can support targeted financial '
                                                         'scams or discriminatory decisions if misused.'},
                              'DATE OF BIRTH': {'category': 'Direct Identifier',
                                                'data_type': 'PII',
                                                'priority': 'MUST_HAVE',
                                                'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                                'risk_level': 'HIGH',
                                                'threat': 'Common knowledge-based authentication factor; enables '
                                                          'account takeover and identity theft.'},
                              'EMAIL ADDRESS': {'category': 'Direct Identifier',
                                                'data_type': 'PII',
                                                'priority': 'MUST_HAVE',
                                                'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                                'risk_level': 'MEDIUM',
                                                'threat': 'Enables targeted phishing and account-recovery attacks '
                                                          'against a financial account.'},
                              'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                          'data_type': 'PII',
                                                          'priority': 'MUST_HAVE',
                                                          'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                                          'risk_level': 'HIGH',
                                                          'threat': 'Enables identity theft, account takeover, and '
                                                                    'social engineering when paired with account '
                                                                    'data.'},
                              'LOAN / MORTGAGE ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                                                 'data_type': 'Financial',
                                                                 'priority': 'MUST_HAVE',
                                                                 'regulation': 'FTC Safeguards Rule',
                                                                 'risk_level': 'HIGH',
                                                                 'threat': 'Enables account takeover, fraudulent '
                                                                           'servicing requests, and identity-linked '
                                                                           'financial fraud.'},
                              'PHONE NUMBER': {'category': 'Direct Identifier',
                                               'data_type': 'PII',
                                               'priority': 'MUST_HAVE',
                                               'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                               'risk_level': 'MEDIUM',
                                               'threat': 'Enables account-recovery social engineering and SIM-swap '
                                                         'style fraud.'},
                              'SALARY / COMPENSATION AMOUNT': {'category': 'Financial Data',
                                                               'data_type': 'Financial',
                                                               'priority': 'NICE_TO_HAVE',
                                                               'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                               'risk_level': 'MEDIUM',
                                                               'threat': 'Discloses financial standing; supports '
                                                                         'targeted scams and workplace-privacy harm.'},
                              'SIGNATURE': {'category': 'Direct Identifier',
                                            'data_type': 'PII',
                                            'priority': 'MUST_HAVE',
                                            'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                            'risk_level': 'HIGH',
                                            'threat': 'Enables forgery of financial authorization, check fraud, or '
                                                      'unauthorized transactions.'},
                              'SOCIAL SECURITY NUMBER (SSN)': {'category': 'Government Identifier',
                                                               'data_type': 'PII',
                                                               'priority': 'MUST_HAVE',
                                                               'regulation': 'NIST SP 800-122 / HIPAA Privacy Rule (in '
                                                                             'health context)',
                                                               'risk_level': 'CRITICAL',
                                                               'threat': 'Identity theft, account fraud, '
                                                                         'impersonation, and long-term privacy harm — '
                                                                         'a US SSN cannot practically be reissued.'},
                              'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                           'data_type': 'PII',
                                                           'priority': 'MUST_HAVE',
                                                           'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                                           'risk_level': 'MEDIUM',
                                                           'threat': 'Enables mail fraud, identity theft, and physical '
                                                                     'targeting when paired with financial data.'}},
 'Medical Appointment / Appointment Reminder': {'BOOKING REFERENCE NUMBER': {'category': 'Administrative/Structural '
                                                                                         'Metadata',
                                                                             'data_type': 'Other',
                                                                             'priority': 'DROP',
                                                                             'regulation': 'N/A',
                                                                             'risk_level': 'MEDIUM',
                                                                             'threat': ''},
                                                'DEPARTMENT / SPECIALTY NAME': {'category': 'Health/Clinical Data',
                                                                                'data_type': 'PHI',
                                                                                'priority': 'MUST_HAVE',
                                                                                'regulation': 'HIPAA Privacy Rule',
                                                                                'risk_level': 'HIGH',
                                                                                'threat': 'A specialty/department name '
                                                                                          'can itself disclose a '
                                                                                          'sensitive health category '
                                                                                          '(cancer, mental health, '
                                                                                          'reproductive health, '
                                                                                          'infectious disease) even '
                                                                                          'without an explicit '
                                                                                          'diagnosis being stated.'},
                                                'DIAGNOSIS / MEDICAL CONDITION': {'category': 'Health/Clinical Data',
                                                                                  'data_type': 'PHI',
                                                                                  'priority': 'MUST_HAVE',
                                                                                  'regulation': 'HIPAA Privacy Rule',
                                                                                  'risk_level': 'CRITICAL',
                                                                                  'threat': 'Directly discloses a '
                                                                                            'sensitive health '
                                                                                            'condition or reason for '
                                                                                            'care; discrimination and '
                                                                                            'privacy harm if exposed.'},
                                                'EMAIL ADDRESS': {'category': 'Direct Identifier',
                                                                  'data_type': 'PHI',
                                                                  'priority': 'NICE_TO_HAVE',
                                                                  'regulation': 'HIPAA Privacy Rule',
                                                                  'risk_level': 'MEDIUM',
                                                                  'threat': 'Enables phishing and account-targeting; '
                                                                            'moderate standalone breach impact.'},
                                                'FACILITY ADDRESS': {'category': 'Administrative/Structural Metadata',
                                                                     'data_type': 'Other',
                                                                     'priority': 'DROP',
                                                                     'regulation': 'N/A',
                                                                     'risk_level': 'MEDIUM',
                                                                     'threat': ''},
                                                'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                            'data_type': 'PHI',
                                                                            'priority': 'MUST_HAVE',
                                                                            'regulation': 'HIPAA Privacy Rule',
                                                                            'risk_level': 'CRITICAL',
                                                                            'threat': 'Re-identifies the individual as '
                                                                                      'a patient of a specific '
                                                                                      'provider; medical-identity '
                                                                                      'theft.'},
                                                'HEALTH PLAN BENEFICIARY/MEMBER NUMBER': {'category': 'Direct '
                                                                                                      'Identifier',
                                                                                          'data_type': 'PHI',
                                                                                          'priority': 'NICE_TO_HAVE',
                                                                                          'regulation': 'HIPAA Privacy '
                                                                                                        'Rule',
                                                                                          'risk_level': 'MEDIUM',
                                                                                          'threat': 'Enables '
                                                                                                    'unauthorized '
                                                                                                    'benefits '
                                                                                                    'inquiries if '
                                                                                                    'exposed; not '
                                                                                                    'always present on '
                                                                                                    'scheduling '
                                                                                                    'reminders.'},
                                                'MEDICAL RECORD NUMBER (MRN)': {'category': 'Direct Identifier',
                                                                                'data_type': 'PHI',
                                                                                'priority': 'MUST_HAVE',
                                                                                'regulation': 'HIPAA Privacy Rule',
                                                                                'risk_level': 'CRITICAL',
                                                                                'threat': 'Uniquely links the '
                                                                                          'individual to their '
                                                                                          'complete clinical record '
                                                                                          'across the health system.'},
                                                'PHONE NUMBER': {'category': 'Direct Identifier',
                                                                 'data_type': 'PHI',
                                                                 'priority': 'MUST_HAVE',
                                                                 'regulation': 'HIPAA Privacy Rule',
                                                                 'risk_level': 'MEDIUM',
                                                                 'threat': 'Enables social engineering/phishing and '
                                                                           'unwanted contact; also carries independent '
                                                                           'regulatory exposure for automated reminder '
                                                                           'calls/texts.'},
                                                'TREATING PROVIDER NAME / NPI NUMBER': {'category': 'Direct Identifier',
                                                                                        'data_type': 'PHI',
                                                                                        'priority': 'NICE_TO_HAVE',
                                                                                        'regulation': 'HIPAA Privacy '
                                                                                                      'Rule',
                                                                                        'risk_level': 'MEDIUM',
                                                                                        'threat': 'Corroborating '
                                                                                                  'identifier that, '
                                                                                                  'combined with a '
                                                                                                  'specialty, can '
                                                                                                  'reinforce inference '
                                                                                                  'of a sensitive '
                                                                                                  'condition; lower '
                                                                                                  'standalone risk '
                                                                                                  "than the patient's "
                                                                                                  'own identity.'}},
 'Medical Record / Clinical Note': {'ADMISSION / DISCHARGE / SERVICE DATE': {'category': 'Direct Identifier',
                                                                             'data_type': 'PHI',
                                                                             'priority': 'MUST_HAVE',
                                                                             'regulation': 'HIPAA Privacy Rule',
                                                                             'risk_level': 'MEDIUM',
                                                                             'threat': 'Enables re-identification when '
                                                                                       'correlated with public event '
                                                                                       'data (e.g., accident reports); '
                                                                                       'listed HIPAA identifier.'},
                                    'AGE OVER 89 (HIPAA SAFE HARBOR THRESHOLD)': {'category': 'Direct Identifier',
                                                                                  'data_type': 'PHI',
                                                                                  'priority': 'NICE_TO_HAVE',
                                                                                  'regulation': 'HIPAA Privacy Rule',
                                                                                  'risk_level': 'LOW',
                                                                                  'threat': 'Low standalone risk; '
                                                                                            'HIPAA requires ages over '
                                                                                            '89 to be aggregated into '
                                                                                            'a single category to '
                                                                                            'prevent re-identification '
                                                                                            'of a small cohort.'},
                                    'ALLERGY INFORMATION': {'category': 'Health/Clinical Data',
                                                            'data_type': 'PHI',
                                                            'priority': 'NICE_TO_HAVE',
                                                            'regulation': 'HIPAA Privacy Rule',
                                                            'risk_level': 'MEDIUM',
                                                            'threat': 'Reveals health information; misuse risk lower '
                                                                      'than diagnosis but still privacy-sensitive.'},
                                    'CLINICAL NOTES / NARRATIVE': {'category': 'Health/Clinical Data',
                                                                   'data_type': 'PHI',
                                                                   'priority': 'MUST_HAVE',
                                                                   'regulation': 'HIPAA Privacy Rule',
                                                                   'risk_level': 'CRITICAL',
                                                                   'threat': 'Free text frequently contains multiple '
                                                                             'PHI elements at once (identity + '
                                                                             'diagnosis + history); high aggregate '
                                                                             'breach impact.'},
                                    'DATE OF BIRTH': {'category': 'Direct Identifier',
                                                      'data_type': 'PII',
                                                      'priority': 'MUST_HAVE',
                                                      'regulation': 'HIPAA Privacy Rule',
                                                      'risk_level': 'HIGH',
                                                      'threat': 'HIPAA Safe Harbor identifier; strengthens patient '
                                                                're-identification when combined with other fields.'},
                                    'DIAGNOSIS / MEDICAL CONDITION': {'category': 'Health/Clinical Data',
                                                                      'data_type': 'PHI',
                                                                      'priority': 'MUST_HAVE',
                                                                      'regulation': 'HIPAA Privacy Rule',
                                                                      'risk_level': 'CRITICAL',
                                                                      'threat': 'Discrimination, stigmatization, '
                                                                                'employment/insurance harm, and '
                                                                                'medical-privacy harm if disclosed.'},
                                    'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                'data_type': 'PII',
                                                                'priority': 'MUST_HAVE',
                                                                'regulation': 'HIPAA Privacy Rule',
                                                                'risk_level': 'CRITICAL',
                                                                'threat': "Re-identifies an individual's health "
                                                                          'record; enables medical-identity theft and '
                                                                          'targeted harassment.'},
                                    'GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)': {'category': 'Direct Identifier',
                                                                                        'data_type': 'PHI',
                                                                                        'priority': 'NICE_TO_HAVE',
                                                                                        'regulation': 'HIPAA Privacy '
                                                                                                      'Rule',
                                                                                        'risk_level': 'LOW',
                                                                                        'threat': 'Low standalone '
                                                                                                  'risk; becomes '
                                                                                                  'meaningful '
                                                                                                  're-identification '
                                                                                                  'risk only in '
                                                                                                  'small-population '
                                                                                                  'geographies or '
                                                                                                  'combined with other '
                                                                                                  'quasi-identifiers.'},
                                    'MEDICAL RECORD NUMBER (MRN)': {'category': 'Direct Identifier',
                                                                    'data_type': 'PHI',
                                                                    'priority': 'MUST_HAVE',
                                                                    'regulation': 'HIPAA Privacy Rule',
                                                                    'risk_level': 'CRITICAL',
                                                                    'threat': 'Directly links an individual to their '
                                                                              'entire clinical history; enables '
                                                                              'medical-identity theft and insurance '
                                                                              'fraud.'},
                                    'MEDICATION / PRESCRIPTION DETAIL': {'category': 'Health/Clinical Data',
                                                                         'data_type': 'PHI',
                                                                         'priority': 'MUST_HAVE',
                                                                         'regulation': 'HIPAA Privacy Rule',
                                                                         'risk_level': 'HIGH',
                                                                         'threat': 'Can reveal a sensitive condition '
                                                                                   'by inference (e.g., psychiatric, '
                                                                                   'HIV, oncology drugs); enables '
                                                                                   'prescription fraud.'},
                                    'PHONE NUMBER': {'category': 'Direct Identifier',
                                                     'data_type': 'PII',
                                                     'priority': 'MUST_HAVE',
                                                     'regulation': 'HIPAA Privacy Rule',
                                                     'risk_level': 'MEDIUM',
                                                     'threat': 'HIPAA Safe Harbor identifier; enables phishing/social '
                                                               'engineering against a patient.'},
                                    'PROCEDURE CODE / DESCRIPTION': {'category': 'Health/Clinical Data',
                                                                     'data_type': 'PHI',
                                                                     'priority': 'NICE_TO_HAVE',
                                                                     'regulation': 'HIPAA Privacy Rule',
                                                                     'risk_level': 'MEDIUM',
                                                                     'threat': 'Discloses treatment history; can imply '
                                                                               'a condition (re-identification risk) '
                                                                               'and support insurance fraud.'},
                                    'SIGNATURE': {'category': 'Direct Identifier',
                                                  'data_type': 'PII',
                                                  'priority': 'NICE_TO_HAVE',
                                                  'regulation': 'HIPAA Privacy Rule',
                                                  'risk_level': 'MEDIUM',
                                                  'threat': 'Enables forgery of authorization for treatment or '
                                                            'disclosure.'},
                                    'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                                 'data_type': 'PII',
                                                                 'priority': 'MUST_HAVE',
                                                                 'regulation': 'HIPAA Privacy Rule',
                                                                 'risk_level': 'HIGH',
                                                                 'threat': 'HIPAA Safe Harbor identifier; discloses '
                                                                           'where a patient lives, raising both '
                                                                           'privacy and physical-safety risk.'},
                                    'TREATING PROVIDER NAME / NPI NUMBER': {'category': 'Direct Identifier',
                                                                            'data_type': 'PHI',
                                                                            'priority': 'NICE_TO_HAVE',
                                                                            'regulation': 'HIPAA Privacy Rule',
                                                                            'risk_level': 'MEDIUM',
                                                                            'threat': 'Discloses the treating '
                                                                                      'clinician; can support social '
                                                                                      'engineering against the '
                                                                                      'practice, lower risk to the '
                                                                                      'patient directly.'}},
 'Offer Letter / Employment Contract': {'COMPANY / EMPLOYER NAME': {'category': 'Administrative/Structural Metadata',
                                                                    'data_type': 'Other',
                                                                    'priority': 'DROP',
                                                                    'regulation': 'N/A',
                                                                    'risk_level': 'MEDIUM',
                                                                    'threat': 'None on its own — organizational data; '
                                                                              'only becomes privacy-relevant combined '
                                                                              'with an individual identifier already '
                                                                              'captured separately.'},
                                        'EMPLOYEE ID NUMBER': {'category': 'Direct Identifier',
                                                               'data_type': 'PII',
                                                               'priority': 'NICE_TO_HAVE',
                                                               'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                               'risk_level': 'LOW',
                                                               'threat': 'Links records to a specific employee; lower '
                                                                         'standalone fraud risk than a government ID '
                                                                         'or SSN.'},
                                        'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                    'data_type': 'PII',
                                                                    'priority': 'MUST_HAVE',
                                                                    'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                                    'risk_level': 'HIGH',
                                                                    'threat': 'Enables identity theft and unauthorized '
                                                                              'disclosure of employment data.'},
                                        'JOB TITLE': {'category': 'Administrative/Structural Metadata',
                                                      'data_type': 'Other',
                                                      'priority': 'DROP',
                                                      'regulation': 'N/A',
                                                      'risk_level': 'MEDIUM',
                                                      'threat': 'Low standalone risk — organizational/role '
                                                                'information; only meaningful when combined with a '
                                                                'captured personal identifier.'},
                                        'SALARY / COMPENSATION AMOUNT': {'category': 'Financial Data',
                                                                         'data_type': 'Financial',
                                                                         'priority': 'NICE_TO_HAVE',
                                                                         'regulation': 'GDPR Art. 4 / India DPDP Act, '
                                                                                       '2023',
                                                                         'risk_level': 'MEDIUM',
                                                                         'threat': 'Discloses financial standing; '
                                                                                   'supports targeted scams and '
                                                                                   'workplace-privacy harm.'},
                                        'SIGNATURE': {'category': 'Direct Identifier',
                                                      'data_type': 'PII',
                                                      'priority': 'NICE_TO_HAVE',
                                                      'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                      'risk_level': 'MEDIUM',
                                                      'threat': 'Enables forgery of employment-related authorization.'},
                                        'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                                     'data_type': 'PII',
                                                                     'priority': 'MUST_HAVE',
                                                                     'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                                     'risk_level': 'MEDIUM',
                                                                     'threat': "Discloses an employee's residence; "
                                                                               'supports identity theft and '
                                                                               'physical-safety risk.'}},
 'Patient Registration / Referral': {'DATE OF BIRTH': {'category': 'Direct Identifier',
                                                       'data_type': 'PII',
                                                       'priority': 'MUST_HAVE',
                                                       'regulation': 'HIPAA Privacy Rule',
                                                       'risk_level': 'HIGH',
                                                       'threat': 'HIPAA Safe Harbor identifier; strengthens patient '
                                                                 're-identification when combined with other fields.'},
                                     'EMAIL ADDRESS': {'category': 'Direct Identifier',
                                                       'data_type': 'PII',
                                                       'priority': 'MUST_HAVE',
                                                       'regulation': 'HIPAA Privacy Rule',
                                                       'risk_level': 'MEDIUM',
                                                       'threat': 'HIPAA Safe Harbor identifier; a credential-adjacent '
                                                                 'identifier usable for phishing tied to health '
                                                                 'context.'},
                                     'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                 'data_type': 'PII',
                                                                 'priority': 'MUST_HAVE',
                                                                 'regulation': 'HIPAA Privacy Rule',
                                                                 'risk_level': 'CRITICAL',
                                                                 'threat': "Re-identifies an individual's health "
                                                                           'record; enables medical-identity theft and '
                                                                           'targeted harassment.'},
                                     'HEALTH INSURANCE POLICY NUMBER': {'category': 'Direct Identifier',
                                                                        'data_type': 'PHI',
                                                                        'priority': 'MUST_HAVE',
                                                                        'regulation': 'HIPAA Privacy Rule',
                                                                        'risk_level': 'HIGH',
                                                                        'threat': 'Enables fraudulent insurance claims '
                                                                                  'and unauthorized access to coverage '
                                                                                  'details.'},
                                     'MEDICAL RECORD NUMBER (MRN)': {'category': 'Direct Identifier',
                                                                     'data_type': 'PHI',
                                                                     'priority': 'MUST_HAVE',
                                                                     'regulation': 'HIPAA Privacy Rule',
                                                                     'risk_level': 'CRITICAL',
                                                                     'threat': 'Directly links an individual to their '
                                                                               'entire clinical history; enables '
                                                                               'medical-identity theft and insurance '
                                                                               'fraud.'},
                                     'PHONE NUMBER': {'category': 'Direct Identifier',
                                                      'data_type': 'PII',
                                                      'priority': 'MUST_HAVE',
                                                      'regulation': 'HIPAA Privacy Rule',
                                                      'risk_level': 'MEDIUM',
                                                      'threat': 'HIPAA Safe Harbor identifier; enables phishing/social '
                                                                'engineering against a patient.'},
                                     'SIGNATURE': {'category': 'Direct Identifier',
                                                   'data_type': 'PII',
                                                   'priority': 'NICE_TO_HAVE',
                                                   'regulation': 'HIPAA Privacy Rule',
                                                   'risk_level': 'MEDIUM',
                                                   'threat': 'Enables forgery of authorization for treatment or '
                                                             'disclosure.'},
                                     'SOCIAL SECURITY NUMBER (SSN)': {'category': 'Government Identifier',
                                                                      'data_type': 'PII',
                                                                      'priority': 'MUST_HAVE',
                                                                      'regulation': 'NIST SP 800-122 / HIPAA Privacy '
                                                                                    'Rule (in health context)',
                                                                      'risk_level': 'CRITICAL',
                                                                      'threat': 'Identity theft, account fraud, '
                                                                                'impersonation, and long-term privacy '
                                                                                'harm — a US SSN cannot practically be '
                                                                                'reissued.'},
                                     'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                                  'data_type': 'PII',
                                                                  'priority': 'MUST_HAVE',
                                                                  'regulation': 'HIPAA Privacy Rule',
                                                                  'risk_level': 'HIGH',
                                                                  'threat': 'HIPAA Safe Harbor identifier; discloses '
                                                                            'where a patient lives, raising both '
                                                                            'privacy and physical-safety risk.'},
                                     'TREATING PROVIDER NAME / NPI NUMBER': {'category': 'Direct Identifier',
                                                                             'data_type': 'PHI',
                                                                             'priority': 'NICE_TO_HAVE',
                                                                             'regulation': 'HIPAA Privacy Rule',
                                                                             'risk_level': 'MEDIUM',
                                                                             'threat': 'Discloses the treating '
                                                                                       'clinician; can support social '
                                                                                       'engineering against the '
                                                                                       'practice, lower risk to the '
                                                                                       'patient directly.'}},
 'Payment Document / Receipt': {'CARD EXPIRATION DATE': {'category': 'Payment Card — Cardholder Data',
                                                         'data_type': 'Payment',
                                                         'priority': 'NICE_TO_HAVE',
                                                         'regulation': 'PCI DSS',
                                                         'risk_level': 'MEDIUM',
                                                         'threat': 'Low value alone; increases fraud risk only when '
                                                                   'paired with the PAN and cardholder name.'},
                                'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                            'data_type': 'PII',
                                                            'priority': 'MUST_HAVE',
                                                            'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                                            'risk_level': 'HIGH',
                                                            'threat': 'Enables identity theft, account takeover, and '
                                                                      'social engineering when paired with account '
                                                                      'data.'},
                                'INVOICE NUMBER': {'category': 'Administrative/Structural Metadata',
                                                   'data_type': 'Other',
                                                   'priority': 'DROP',
                                                   'regulation': 'N/A',
                                                   'risk_level': 'MEDIUM',
                                                   'threat': 'None — an internal business/accounting reference, not '
                                                             "linked to an individual's protected data."},
                                'LINE-ITEM PRODUCT/SERVICE DESCRIPTION': {'category': 'Administrative/Structural '
                                                                                      'Metadata',
                                                                          'data_type': 'Other',
                                                                          'priority': 'DROP',
                                                                          'regulation': 'N/A',
                                                                          'risk_level': 'MEDIUM',
                                                                          'threat': 'None — describes a purchased '
                                                                                    'product/service, not the '
                                                                                    'individual.'},
                                'MERCHANT / VENDOR NAME': {'category': 'Administrative/Structural Metadata',
                                                           'data_type': 'Other',
                                                           'priority': 'DROP',
                                                           'regulation': 'N/A',
                                                           'risk_level': 'MEDIUM',
                                                           'threat': 'None on its own — identifies a business, not the '
                                                                     'data subject; standard commercial information.'},
                                'PAYMENT CARD NUMBER (PAN)': {'category': 'Payment Card — Cardholder Data',
                                                              'data_type': 'Payment',
                                                              'priority': 'MUST_HAVE',
                                                              'regulation': 'PCI DSS',
                                                              'risk_level': 'CRITICAL',
                                                              'threat': 'Direct payment fraud and unauthorized '
                                                                        'transactions.'},
                                'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                             'data_type': 'PII',
                                                             'priority': 'MUST_HAVE',
                                                             'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                                             'risk_level': 'MEDIUM',
                                                             'threat': 'Enables mail fraud, identity theft, and '
                                                                       'physical targeting when paired with financial '
                                                                       'data.'},
                                'TRANSACTION HISTORY / AMOUNTS': {'category': 'Financial Data',
                                                                  'data_type': 'Financial',
                                                                  'priority': 'NICE_TO_HAVE',
                                                                  'regulation': 'GDPR Art. 4',
                                                                  'risk_level': 'LOW',
                                                                  'threat': 'Discloses spending behavior/financial '
                                                                            'profile; privacy-relevant but not '
                                                                            'independently exploitable without account '
                                                                            'credentials.'}},
 'Payroll / Salary Document': {'BANK ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                                       'data_type': 'Financial',
                                                       'priority': 'MUST_HAVE',
                                                       'regulation': 'FTC Safeguards Rule',
                                                       'risk_level': 'CRITICAL',
                                                       'threat': 'Financial fraud, unauthorized transfers, and account '
                                                                 'targeting.'},
                               'COMPANY / EMPLOYER NAME': {'category': 'Administrative/Structural Metadata',
                                                           'data_type': 'Other',
                                                           'priority': 'DROP',
                                                           'regulation': 'N/A',
                                                           'risk_level': 'MEDIUM',
                                                           'threat': 'None on its own — organizational data; only '
                                                                     'becomes privacy-relevant combined with an '
                                                                     'individual identifier already captured '
                                                                     'separately.'},
                               'EMPLOYEE ID NUMBER': {'category': 'Direct Identifier',
                                                      'data_type': 'PII',
                                                      'priority': 'NICE_TO_HAVE',
                                                      'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                      'risk_level': 'LOW',
                                                      'threat': 'Links records to a specific employee; lower '
                                                                'standalone fraud risk than a government ID or SSN.'},
                               'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                           'data_type': 'PII',
                                                           'priority': 'MUST_HAVE',
                                                           'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                           'risk_level': 'HIGH',
                                                           'threat': 'Enables identity theft and unauthorized '
                                                                     'disclosure of employment data.'},
                               'SALARY / COMPENSATION AMOUNT': {'category': 'Financial Data',
                                                                'data_type': 'Financial',
                                                                'priority': 'NICE_TO_HAVE',
                                                                'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                                'risk_level': 'MEDIUM',
                                                                'threat': 'Discloses financial standing; supports '
                                                                          'targeted scams and workplace-privacy harm.'},
                               'SOCIAL SECURITY NUMBER (SSN)': {'category': 'Government Identifier',
                                                                'data_type': 'PII',
                                                                'priority': 'MUST_HAVE',
                                                                'regulation': 'NIST SP 800-122 / HIPAA Privacy Rule '
                                                                              '(in health context)',
                                                                'risk_level': 'CRITICAL',
                                                                'threat': 'Identity theft, account fraud, '
                                                                          'impersonation, and long-term privacy harm — '
                                                                          'a US SSN cannot practically be reissued.'},
                               'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                                            'data_type': 'PII',
                                                            'priority': 'MUST_HAVE',
                                                            'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                            'risk_level': 'MEDIUM',
                                                            'threat': "Discloses an employee's residence; supports "
                                                                      'identity theft and physical-safety risk.'},
                               'US TAX ID (EIN / ITIN)': {'category': 'Government Identifier',
                                                          'data_type': 'PII/Financial',
                                                          'priority': 'MUST_HAVE',
                                                          'regulation': 'NIST SP 800-122 / FTC Safeguards Rule',
                                                          'risk_level': 'HIGH',
                                                          'threat': 'Enables tax fraud, fraudulent filings, and '
                                                                    'business/identity impersonation.'}},
 'Prescription': {'DATE OF BIRTH': {'category': 'Direct Identifier',
                                    'data_type': 'PII',
                                    'priority': 'MUST_HAVE',
                                    'regulation': 'HIPAA Privacy Rule',
                                    'risk_level': 'HIGH',
                                    'threat': 'HIPAA Safe Harbor identifier; strengthens patient re-identification '
                                              'when combined with other fields.'},
                  'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                              'data_type': 'PII',
                                              'priority': 'MUST_HAVE',
                                              'regulation': 'HIPAA Privacy Rule',
                                              'risk_level': 'CRITICAL',
                                              'threat': "Re-identifies an individual's health record; enables "
                                                        'medical-identity theft and targeted harassment.'},
                  'HEALTH INSURANCE POLICY NUMBER': {'category': 'Direct Identifier',
                                                     'data_type': 'PHI',
                                                     'priority': 'MUST_HAVE',
                                                     'regulation': 'HIPAA Privacy Rule',
                                                     'risk_level': 'HIGH',
                                                     'threat': 'Enables fraudulent insurance claims and unauthorized '
                                                               'access to coverage details.'},
                  'MEDICAL RECORD NUMBER (MRN)': {'category': 'Direct Identifier',
                                                  'data_type': 'PHI',
                                                  'priority': 'MUST_HAVE',
                                                  'regulation': 'HIPAA Privacy Rule',
                                                  'risk_level': 'CRITICAL',
                                                  'threat': 'Directly links an individual to their entire clinical '
                                                            'history; enables medical-identity theft and insurance '
                                                            'fraud.'},
                  'MEDICATION / PRESCRIPTION DETAIL': {'category': 'Health/Clinical Data',
                                                       'data_type': 'PHI',
                                                       'priority': 'MUST_HAVE',
                                                       'regulation': 'HIPAA Privacy Rule',
                                                       'risk_level': 'HIGH',
                                                       'threat': 'Can reveal a sensitive condition by inference (e.g., '
                                                                 'psychiatric, HIV, oncology drugs); enables '
                                                                 'prescription fraud.'},
                  'SIGNATURE': {'category': 'Direct Identifier',
                                'data_type': 'PII',
                                'priority': 'NICE_TO_HAVE',
                                'regulation': 'HIPAA Privacy Rule',
                                'risk_level': 'MEDIUM',
                                'threat': 'Enables forgery of authorization for treatment or disclosure.'},
                  'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                               'data_type': 'PII',
                                               'priority': 'MUST_HAVE',
                                               'regulation': 'HIPAA Privacy Rule',
                                               'risk_level': 'HIGH',
                                               'threat': 'HIPAA Safe Harbor identifier; discloses where a patient '
                                                         'lives, raising both privacy and physical-safety risk.'},
                  'TREATING PROVIDER NAME / NPI NUMBER': {'category': 'Direct Identifier',
                                                          'data_type': 'PHI',
                                                          'priority': 'NICE_TO_HAVE',
                                                          'regulation': 'HIPAA Privacy Rule',
                                                          'risk_level': 'MEDIUM',
                                                          'threat': 'Discloses the treating clinician; can support '
                                                                    'social engineering against the practice, lower '
                                                                    'risk to the patient directly.'}},
 'Resume / CV': {'COMPANY / EMPLOYER NAME': {'category': 'Administrative/Structural Metadata',
                                             'data_type': 'Other',
                                             'priority': 'DROP',
                                             'regulation': 'N/A',
                                             'risk_level': 'MEDIUM',
                                             'threat': 'None on its own — organizational data; only becomes '
                                                       'privacy-relevant combined with an individual identifier '
                                                       'already captured separately.'},
                 'DATE OF BIRTH': {'category': 'Direct Identifier',
                                   'data_type': 'PII',
                                   'priority': 'MUST_HAVE',
                                   'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                   'risk_level': 'MEDIUM',
                                   'threat': 'Supports identity theft and may reveal protected characteristics (e.g., '
                                             'age-related).'},
                 'EMAIL ADDRESS': {'category': 'Direct Identifier',
                                   'data_type': 'PII',
                                   'priority': 'NICE_TO_HAVE',
                                   'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                   'risk_level': 'LOW',
                                   'threat': 'Enables phishing and account-targeting against the employee.'},
                 'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                             'data_type': 'PII',
                                             'priority': 'MUST_HAVE',
                                             'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                             'risk_level': 'HIGH',
                                             'threat': 'Enables identity theft and unauthorized disclosure of '
                                                       'employment data.'},
                 'JOB TITLE': {'category': 'Administrative/Structural Metadata',
                               'data_type': 'Other',
                               'priority': 'DROP',
                               'regulation': 'N/A',
                               'risk_level': 'MEDIUM',
                               'threat': 'Low standalone risk — organizational/role information; only meaningful when '
                                         'combined with a captured personal identifier.'},
                 'PHONE NUMBER': {'category': 'Direct Identifier',
                                  'data_type': 'PII',
                                  'priority': 'NICE_TO_HAVE',
                                  'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                  'risk_level': 'LOW',
                                  'threat': 'Enables phishing/social engineering targeting the employee.'},
                 'PHOTOGRAPH / FACIAL IMAGE': {'category': 'Direct Identifier / Biometric-Adjacent',
                                               'data_type': 'PII',
                                               'priority': 'MUST_HAVE',
                                               'regulation': 'HIPAA Privacy Rule / GDPR Art. 4',
                                               'risk_level': 'HIGH',
                                               'threat': 'A comparable identifier under HIPAA Safe Harbor ("full face '
                                                         'photographic images"); enables direct visual '
                                                         'identification.'},
                 'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                              'data_type': 'PII',
                                              'priority': 'MUST_HAVE',
                                              'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                              'risk_level': 'MEDIUM',
                                              'threat': "Discloses an employee's residence; supports identity theft "
                                                        'and physical-safety risk.'}},
 'Summary of Benefits and Coverage (SBC)': {'COMPANY / EMPLOYER NAME': {'category': 'Administrative/Structural '
                                                                                    'Metadata',
                                                                        'data_type': 'Other',
                                                                        'priority': 'DROP',
                                                                        'regulation': 'N/A',
                                                                        'risk_level': 'MEDIUM',
                                                                        'threat': ''},
                                            'COST-SHARING AMOUNT': {'category': 'Administrative/Structural Metadata',
                                                                    'data_type': 'Other',
                                                                    'priority': 'DROP',
                                                                    'regulation': 'N/A',
                                                                    'risk_level': 'MEDIUM',
                                                                    'threat': ''},
                                            'COVERAGE EXAMPLE SCENARIO': {'category': 'Administrative/Structural '
                                                                                      'Metadata',
                                                                          'data_type': 'Other',
                                                                          'priority': 'DROP',
                                                                          'regulation': 'N/A',
                                                                          'risk_level': 'MEDIUM',
                                                                          'threat': ''},
                                            'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                        'data_type': 'PII/PHI',
                                                                        'priority': 'NICE_TO_HAVE',
                                                                        'regulation': 'HIPAA Privacy Rule',
                                                                        'risk_level': 'MEDIUM',
                                                                        'threat': 'Links the individual to a specific '
                                                                                  'health plan and, indirectly, to '
                                                                                  'their health-plan enrollment '
                                                                                  'status.'},
                                            'GROUP / POLICY NUMBER': {'category': 'Administrative Identifier',
                                                                      'data_type': 'PHI',
                                                                      'priority': 'NICE_TO_HAVE',
                                                                      'regulation': 'HIPAA Privacy Rule',
                                                                      'risk_level': 'MEDIUM',
                                                                      'threat': 'Identifies the employer/plan group '
                                                                                'rather than the individual directly; '
                                                                                'useful corroborating context but '
                                                                                'weaker re-identification value on its '
                                                                                'own.'},
                                            'HEALTH PLAN BENEFICIARY/MEMBER NUMBER': {'category': 'Direct Identifier',
                                                                                      'data_type': 'PHI',
                                                                                      'priority': 'MUST_HAVE',
                                                                                      'regulation': 'HIPAA Privacy '
                                                                                                    'Rule',
                                                                                      'risk_level': 'HIGH',
                                                                                      'threat': 'Uniquely identifies a '
                                                                                                'specific enrollee '
                                                                                                'within a health plan; '
                                                                                                'enables '
                                                                                                'medical-identity '
                                                                                                'theft and '
                                                                                                'unauthorized benefits '
                                                                                                'inquiries.'},
                                            'PLAN NAME': {'category': 'Administrative/Structural Metadata',
                                                          'data_type': 'Other',
                                                          'priority': 'DROP',
                                                          'regulation': 'N/A',
                                                          'risk_level': 'MEDIUM',
                                                          'threat': ''},
                                            'PREMIUM AMOUNT': {'category': 'Financial Data',
                                                               'data_type': 'PII/Financial',
                                                               'priority': 'NICE_TO_HAVE',
                                                               'regulation': 'FTC Safeguards Rule',
                                                               'risk_level': 'MEDIUM',
                                                               'threat': "Reveals an individual's personal healthcare "
                                                                         'spending obligation; sensitive but lower '
                                                                         'breach impact than an account or card '
                                                                         'number.'}},
 'System Log / Incident Report / Security Report': {'CVE / VULNERABILITY REFERENCE': {'category': 'Administrative/Structural '
                                                                                                  'Metadata',
                                                                                      'data_type': 'Other',
                                                                                      'priority': 'DROP',
                                                                                      'regulation': 'N/A',
                                                                                      'risk_level': 'MEDIUM',
                                                                                      'threat': 'None — a public '
                                                                                                'vulnerability catalog '
                                                                                                'identifier, not '
                                                                                                'personal data.'},
                                                    'DEVICE IDENTIFIER / MAC ADDRESS': {'category': 'Online Identifier',
                                                                                        'data_type': 'PII',
                                                                                        'priority': 'NICE_TO_HAVE',
                                                                                        'regulation': 'GDPR Art. 4',
                                                                                        'risk_level': 'LOW',
                                                                                        'threat': 'Supports '
                                                                                                  'device-level '
                                                                                                  'tracking; moderate '
                                                                                                  'risk mainly in '
                                                                                                  'combination with '
                                                                                                  'other identifiers.'},
                                                    'EMAIL ADDRESS': {'category': 'Direct Identifier',
                                                                      'data_type': 'PII',
                                                                      'priority': 'NICE_TO_HAVE',
                                                                      'regulation': 'GDPR Art. 32 / NIST SP 800-122',
                                                                      'risk_level': 'MEDIUM',
                                                                      'threat': 'Links a logged event to a specific '
                                                                                'mailbox/identity for follow-on '
                                                                                'phishing.'},
                                                    'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                                                                'data_type': 'PII',
                                                                                'priority': 'MUST_HAVE',
                                                                                'regulation': 'GDPR Art. 32 / NIST SP '
                                                                                              '800-122',
                                                                                'risk_level': 'MEDIUM',
                                                                                'threat': 'Links a system event or log '
                                                                                          'entry to a specific '
                                                                                          'individual, enabling '
                                                                                          'targeted follow-on '
                                                                                          'attacks.'},
                                                    'INTERNAL SERVER / HOSTNAME': {'category': 'Administrative/Structural '
                                                                                               'Metadata',
                                                                                   'data_type': 'Other',
                                                                                   'priority': 'DROP',
                                                                                   'regulation': 'N/A',
                                                                                   'risk_level': 'MEDIUM',
                                                                                   'threat': 'None directly — '
                                                                                             'infrastructure metadata, '
                                                                                             'not linked to a specific '
                                                                                             'individual (distinct '
                                                                                             "from a person's own "
                                                                                             'device IP address, '
                                                                                             'tracked separately).'},
                                                    'IP ADDRESS': {'category': 'Online Identifier',
                                                                   'data_type': 'PII',
                                                                   'priority': 'NICE_TO_HAVE',
                                                                   'regulation': 'GDPR Art. 4',
                                                                   'risk_level': 'MEDIUM',
                                                                   'threat': 'Supports device/location tracking and '
                                                                             'can enable targeted network attacks in a '
                                                                             'security-log context.'},
                                                    'SESSION ID / AUTH COOKIE': {'category': 'Security Credential — '
                                                                                             'Online Identifier',
                                                                                 'data_type': 'Credential',
                                                                                 'priority': 'NICE_TO_HAVE',
                                                                                 'regulation': 'GDPR Art. 4',
                                                                                 'risk_level': 'MEDIUM',
                                                                                 'threat': 'Enables session hijacking '
                                                                                           'while the session remains '
                                                                                           'valid.'},
                                                    'USERNAME / LOGIN ID': {'category': 'Security Credential',
                                                                            'data_type': 'Credential',
                                                                            'priority': 'NICE_TO_HAVE',
                                                                            'regulation': 'GDPR Art. 32 / GDPR Art. 4',
                                                                            'risk_level': 'MEDIUM',
                                                                            'threat': 'Enables targeted '
                                                                                      'credential-stuffing and '
                                                                                      'account-targeting attacks, '
                                                                                      'especially paired with a '
                                                                                      'password.'}},
 'Tax Document': {'AADHAAR NUMBER (INDIA)': {'category': 'Government Identifier',
                                             'data_type': 'PII',
                                             'priority': 'MUST_HAVE',
                                             'regulation': 'Digital Personal Data Protection Act, 2023',
                                             'risk_level': 'CRITICAL',
                                             'threat': 'Enables identity theft and fraudulent enrollment across '
                                                       "India's linked digital-identity ecosystem (banking, telecom, "
                                                       'welfare).'},
                  'BANK ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                          'data_type': 'Financial',
                                          'priority': 'MUST_HAVE',
                                          'regulation': 'FTC Safeguards Rule',
                                          'risk_level': 'CRITICAL',
                                          'threat': 'Financial fraud, unauthorized transfers, and account targeting.'},
                  'COMPANY / EMPLOYER NAME': {'category': 'Administrative/Structural Metadata',
                                              'data_type': 'Other',
                                              'priority': 'DROP',
                                              'regulation': 'N/A',
                                              'risk_level': 'MEDIUM',
                                              'threat': 'None on its own — organizational data; only becomes '
                                                        'privacy-relevant combined with an individual identifier '
                                                        'already captured separately.'},
                  'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                                              'data_type': 'PII',
                                              'priority': 'MUST_HAVE',
                                              'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                              'risk_level': 'HIGH',
                                              'threat': 'Enables identity theft, account takeover, and social '
                                                        'engineering when paired with account data.'},
                  'PERMANENT ACCOUNT NUMBER — INCOME TAX (INDIA)': {'category': 'Government Identifier',
                                                                    'data_type': 'PII/Financial',
                                                                    'priority': 'MUST_HAVE',
                                                                    'regulation': 'Digital Personal Data Protection '
                                                                                  'Act, 2023',
                                                                    'risk_level': 'HIGH',
                                                                    'threat': 'Enables tax fraud and identity theft; '
                                                                              'widely used as a financial KYC '
                                                                              'identifier in India.'},
                  'SALARY / COMPENSATION AMOUNT': {'category': 'Financial Data',
                                                   'data_type': 'Financial',
                                                   'priority': 'NICE_TO_HAVE',
                                                   'regulation': 'GDPR Art. 4 / India DPDP Act, 2023',
                                                   'risk_level': 'MEDIUM',
                                                   'threat': 'Discloses financial standing; supports targeted scams '
                                                             'and workplace-privacy harm.'},
                  'SOCIAL SECURITY NUMBER (SSN)': {'category': 'Government Identifier',
                                                   'data_type': 'PII',
                                                   'priority': 'MUST_HAVE',
                                                   'regulation': 'NIST SP 800-122 / HIPAA Privacy Rule (in health '
                                                                 'context)',
                                                   'risk_level': 'CRITICAL',
                                                   'threat': 'Identity theft, account fraud, impersonation, and '
                                                             'long-term privacy harm — a US SSN cannot practically be '
                                                             'reissued.'},
                  'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                                               'data_type': 'PII',
                                               'priority': 'MUST_HAVE',
                                               'regulation': 'FTC Safeguards Rule (GLBA) / GDPR Art. 4',
                                               'risk_level': 'MEDIUM',
                                               'threat': 'Enables mail fraud, identity theft, and physical targeting '
                                                         'when paired with financial data.'},
                  'US TAX ID (EIN / ITIN)': {'category': 'Government Identifier',
                                             'data_type': 'PII/Financial',
                                             'priority': 'MUST_HAVE',
                                             'regulation': 'NIST SP 800-122 / FTC Safeguards Rule',
                                             'risk_level': 'HIGH',
                                             'threat': 'Enables tax fraud, fraudulent filings, and business/identity '
                                                       'impersonation.'}}}

GLOBAL_POLICY = {'AADHAAR NUMBER (INDIA)': {'category': 'Government Identifier',
                            'data_type': 'PII',
                            'priority': 'MUST_HAVE',
                            'risk_level': 'CRITICAL'},
 'ACCESS TOKEN / OAUTH TOKEN': {'category': 'Security Credential',
                                'data_type': 'Credential',
                                'priority': 'MUST_HAVE',
                                'risk_level': 'CRITICAL'},
 'ADMISSION / DISCHARGE / SERVICE DATE': {'category': 'Direct Identifier',
                                          'data_type': 'PHI',
                                          'priority': 'MUST_HAVE',
                                          'risk_level': 'MEDIUM'},
 'AGE OVER 89 (HIPAA SAFE HARBOR THRESHOLD)': {'category': 'Direct Identifier',
                                               'data_type': 'PHI',
                                               'priority': 'NICE_TO_HAVE',
                                               'risk_level': 'LOW'},
 'ALLERGY INFORMATION': {'category': 'Health/Clinical Data',
                         'data_type': 'PHI',
                         'priority': 'NICE_TO_HAVE',
                         'risk_level': 'MEDIUM'},
 'API KEY / SECRET KEY': {'category': 'Security Credential',
                          'data_type': 'Credential',
                          'priority': 'MUST_HAVE',
                          'risk_level': 'CRITICAL'},
 'ATTORNEY-CLIENT PRIVILEGE NOTATION': {'category': 'Administrative/Structural Metadata',
                                        'data_type': 'Other',
                                        'priority': 'DROP',
                                        'risk_level': 'MEDIUM'},
 'BACKGROUND / CRIMINAL BACKGROUND CHECK RESULT': {'category': 'HR Sensitive Data',
                                                   'data_type': 'Other',
                                                   'priority': 'MUST_HAVE',
                                                   'risk_level': 'HIGH'},
 'BANK ACCOUNT NUMBER': {'category': 'Financial Account Data',
                         'data_type': 'Financial',
                         'priority': 'MUST_HAVE',
                         'risk_level': 'CRITICAL'},
 'BANK ROUTING / SORT CODE': {'category': 'Financial Account Data',
                              'data_type': 'Financial',
                              'priority': 'NICE_TO_HAVE',
                              'risk_level': 'MEDIUM'},
 'BARCODE / QR CODE INTERNAL DOCUMENT ID': {'category': 'Administrative/Structural Metadata',
                                            'data_type': 'Other',
                                            'priority': 'DROP',
                                            'risk_level': 'MEDIUM'},
 'BOILERPLATE / DISCLAIMER TEXT': {'category': 'Administrative/Structural Metadata',
                                   'data_type': 'Other',
                                   'priority': 'DROP',
                                   'risk_level': 'MEDIUM'},
 'BOOKING REFERENCE NUMBER': {'category': 'Administrative/Structural Metadata',
                              'data_type': 'Other',
                              'priority': 'DROP',
                              'risk_level': 'MEDIUM'},
 'BREACH INCIDENT DESCRIPTION': {'category': 'Administrative/Structural Metadata',
                                 'data_type': 'Other',
                                 'priority': 'NICE_TO_HAVE',
                                 'risk_level': 'LOW'},
 'BREACHED DATA ELEMENT DESCRIPTION': {'category': 'Health/Clinical Data',
                                       'data_type': 'PHI',
                                       'priority': 'MUST_HAVE',
                                       'risk_level': 'CRITICAL'},
 'CARD EXPIRATION DATE': {'category': 'Payment Card — Cardholder Data',
                          'data_type': 'Payment',
                          'priority': 'NICE_TO_HAVE',
                          'risk_level': 'MEDIUM'},
 'CARD VERIFICATION CODE (CVV/CVC/CID/CAV2)': {'category': 'Payment Card — Sensitive Authentication Data',
                                               'data_type': 'Payment',
                                               'priority': 'MUST_HAVE',
                                               'risk_level': 'CRITICAL'},
 'CARDHOLDER NAME': {'category': 'Payment Card — Cardholder Data',
                     'data_type': 'Payment',
                     'priority': 'NICE_TO_HAVE',
                     'risk_level': 'MEDIUM'},
 'CASE / DOCKET / REFERENCE NUMBER': {'category': 'Administrative Identifier',
                                      'data_type': 'Other',
                                      'priority': 'NICE_TO_HAVE',
                                      'risk_level': 'MEDIUM'},
 'CLINICAL NOTES / NARRATIVE': {'category': 'Health/Clinical Data',
                                'data_type': 'PHI',
                                'priority': 'MUST_HAVE',
                                'risk_level': 'CRITICAL'},
 'COMPANY / EMPLOYER NAME': {'category': 'Administrative/Structural Metadata',
                             'data_type': 'Other',
                             'priority': 'DROP',
                             'risk_level': 'MEDIUM'},
 'COST-SHARING AMOUNT': {'category': 'Administrative/Structural Metadata',
                         'data_type': 'Other',
                         'priority': 'DROP',
                         'risk_level': 'MEDIUM'},
 'COUNTRY NAME (GENERIC)': {'category': 'Administrative/Structural Metadata',
                            'data_type': 'Other',
                            'priority': 'DROP',
                            'risk_level': 'MEDIUM'},
 'COURT / JURISDICTION NAME': {'category': 'Administrative/Structural Metadata',
                               'data_type': 'Other',
                               'priority': 'DROP',
                               'risk_level': 'MEDIUM'},
 'COVERAGE DATE': {'category': 'Administrative Identifier',
                   'data_type': 'PHI',
                   'priority': 'NICE_TO_HAVE',
                   'risk_level': 'MEDIUM'},
 'COVERAGE EXAMPLE SCENARIO': {'category': 'Administrative/Structural Metadata',
                               'data_type': 'Other',
                               'priority': 'DROP',
                               'risk_level': 'MEDIUM'},
 'CREDIT SCORE': {'category': 'Financial Account Data',
                  'data_type': 'Financial',
                  'priority': 'NICE_TO_HAVE',
                  'risk_level': 'MEDIUM'},
 'CRIMINAL RECORD / CONVICTION DATA': {'category': 'HR Sensitive Data',
                                       'data_type': 'Other',
                                       'priority': 'MUST_HAVE',
                                       'risk_level': 'CRITICAL'},
 'CT NUMBER / IMAGING TECHNICAL PARAMETER': {'category': 'Administrative/Structural Metadata',
                                             'data_type': 'Other',
                                             'priority': 'DROP',
                                             'risk_level': 'MEDIUM'},
 'CVE / VULNERABILITY REFERENCE': {'category': 'Administrative/Structural Metadata',
                                   'data_type': 'Other',
                                   'priority': 'DROP',
                                   'risk_level': 'MEDIUM'},
 'DATE OF BIRTH': {'category': 'Direct Identifier', 'data_type': 'PII', 'priority': 'MUST_HAVE', 'risk_level': 'HIGH'},
 'DEPARTMENT / SPECIALTY NAME': {'category': 'Health/Clinical Data',
                                 'data_type': 'PHI',
                                 'priority': 'MUST_HAVE',
                                 'risk_level': 'HIGH'},
 'DEVICE IDENTIFIER / MAC ADDRESS': {'category': 'Online Identifier',
                                     'data_type': 'PII',
                                     'priority': 'NICE_TO_HAVE',
                                     'risk_level': 'LOW'},
 'DIAGNOSIS / MEDICAL CONDITION': {'category': 'Health/Clinical Data',
                                   'data_type': 'PHI',
                                   'priority': 'MUST_HAVE',
                                   'risk_level': 'CRITICAL'},
 'DISABILITY STATUS': {'category': 'HR Sensitive Data',
                       'data_type': 'PHI/Other',
                       'priority': 'MUST_HAVE',
                       'risk_level': 'HIGH'},
 'DISCIPLINARY ACTION DETAIL': {'category': 'HR Sensitive Data',
                                'data_type': 'Other',
                                'priority': 'NICE_TO_HAVE',
                                'risk_level': 'MEDIUM'},
 'DOCUMENT CREATION/PRINT DATE (NON-INDIVIDUAL)': {'category': 'Administrative/Structural Metadata',
                                                   'data_type': 'Other',
                                                   'priority': 'DROP',
                                                   'risk_level': 'MEDIUM'},
 "DRIVER'S LICENSE NUMBER": {'category': 'Government Identifier',
                             'data_type': 'PII',
                             'priority': 'MUST_HAVE',
                             'risk_level': 'HIGH'},
 'EMAIL ADDRESS': {'category': 'Direct Identifier',
                   'data_type': 'PII',
                   'priority': 'MUST_HAVE',
                   'risk_level': 'MEDIUM'},
 'EMPLOYEE ID NUMBER': {'category': 'Direct Identifier',
                        'data_type': 'PII',
                        'priority': 'NICE_TO_HAVE',
                        'risk_level': 'LOW'},
 'ENROLLMENT/ACTIVATION CODE': {'category': 'Security Credential',
                                'data_type': 'Credential',
                                'priority': 'MUST_HAVE',
                                'risk_level': 'HIGH'},
 'FACILITY ADDRESS': {'category': 'Administrative/Structural Metadata',
                      'data_type': 'Other',
                      'priority': 'DROP',
                      'risk_level': 'MEDIUM'},
 'FORM / TEMPLATE FIELD LABEL': {'category': 'Administrative/Structural Metadata',
                                 'data_type': 'Other',
                                 'priority': 'DROP',
                                 'risk_level': 'MEDIUM'},
 'FULL MAGNETIC STRIPE / TRACK DATA': {'category': 'Payment Card — Sensitive Authentication Data',
                                       'data_type': 'Payment',
                                       'priority': 'MUST_HAVE',
                                       'risk_level': 'CRITICAL'},
 'FULL NAME / PERSON NAME': {'category': 'Direct Identifier',
                             'data_type': 'PII',
                             'priority': 'MUST_HAVE',
                             'risk_level': 'MEDIUM'},
 'GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)': {'category': 'Direct Identifier',
                                                     'data_type': 'PHI',
                                                     'priority': 'NICE_TO_HAVE',
                                                     'risk_level': 'LOW'},
 'GROUP / POLICY NUMBER': {'category': 'Administrative Identifier',
                           'data_type': 'PHI',
                           'priority': 'NICE_TO_HAVE',
                           'risk_level': 'MEDIUM'},
 'HEALTH INSURANCE POLICY NUMBER': {'category': 'Direct Identifier',
                                    'data_type': 'PHI',
                                    'priority': 'MUST_HAVE',
                                    'risk_level': 'HIGH'},
 'HEALTH PLAN BENEFICIARY/MEMBER NUMBER': {'category': 'Direct Identifier',
                                           'data_type': 'PHI',
                                           'priority': 'MUST_HAVE',
                                           'risk_level': 'HIGH'},
 'IBAN / SWIFT-BIC CODE': {'category': 'Financial Account Data',
                           'data_type': 'Financial',
                           'priority': 'MUST_HAVE',
                           'risk_level': 'HIGH'},
 'IMAGING STUDY ID / ACCESSION NUMBER': {'category': 'Direct Identifier',
                                         'data_type': 'PHI',
                                         'priority': 'NICE_TO_HAVE',
                                         'risk_level': 'MEDIUM'},
 'INTERNAL SERVER / HOSTNAME': {'category': 'Administrative/Structural Metadata',
                                'data_type': 'Other',
                                'priority': 'DROP',
                                'risk_level': 'MEDIUM'},
 'INVESTMENT / BROKERAGE ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                           'data_type': 'Financial',
                                           'priority': 'MUST_HAVE',
                                           'risk_level': 'HIGH'},
 'INVOICE NUMBER': {'category': 'Administrative/Structural Metadata',
                    'data_type': 'Other',
                    'priority': 'DROP',
                    'risk_level': 'MEDIUM'},
 'IP ADDRESS': {'category': 'Online Identifier',
                'data_type': 'PII',
                'priority': 'NICE_TO_HAVE',
                'risk_level': 'MEDIUM'},
 'JOB TITLE': {'category': 'Administrative/Structural Metadata',
               'data_type': 'Other',
               'priority': 'DROP',
               'risk_level': 'MEDIUM'},
 'LAB TEST RESULT / VALUE': {'category': 'Health/Clinical Data',
                             'data_type': 'PHI',
                             'priority': 'NICE_TO_HAVE',
                             'risk_level': 'MEDIUM'},
 'LINE-ITEM PRODUCT/SERVICE DESCRIPTION': {'category': 'Administrative/Structural Metadata',
                                           'data_type': 'Other',
                                           'priority': 'DROP',
                                           'risk_level': 'MEDIUM'},
 'LOAN / MORTGAGE ACCOUNT NUMBER': {'category': 'Financial Account Data',
                                    'data_type': 'Financial',
                                    'priority': 'MUST_HAVE',
                                    'risk_level': 'HIGH'},
 'MEDICAL CLAIM NUMBER': {'category': 'Direct Identifier',
                          'data_type': 'PHI',
                          'priority': 'NICE_TO_HAVE',
                          'risk_level': 'MEDIUM'},
 'MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER': {'category': 'Administrative/Structural Metadata',
                                                'data_type': 'Other',
                                                'priority': 'DROP',
                                                'risk_level': 'MEDIUM'},
 'MEDICAL RECORD NUMBER (MRN)': {'category': 'Direct Identifier',
                                 'data_type': 'PHI',
                                 'priority': 'MUST_HAVE',
                                 'risk_level': 'CRITICAL'},
 'MEDICATION / PRESCRIPTION DETAIL': {'category': 'Health/Clinical Data',
                                      'data_type': 'PHI',
                                      'priority': 'MUST_HAVE',
                                      'risk_level': 'HIGH'},
 'MERCHANT / VENDOR NAME': {'category': 'Administrative/Structural Metadata',
                            'data_type': 'Other',
                            'priority': 'DROP',
                            'risk_level': 'MEDIUM'},
 'NATIONAL / GOVERNMENT ID NUMBER (GENERIC, NON-US/NON-INDIA)': {'category': 'Government Identifier',
                                                                 'data_type': 'PII',
                                                                 'priority': 'MUST_HAVE',
                                                                 'risk_level': 'HIGH'},
 'ORGANIZATION CONTACT INFO': {'category': 'Administrative/Structural Metadata',
                               'data_type': 'Other',
                               'priority': 'DROP',
                               'risk_level': 'MEDIUM'},
 'OTP / MFA CODE': {'category': 'Security Credential',
                    'data_type': 'Credential',
                    'priority': 'MUST_HAVE',
                    'risk_level': 'HIGH'},
 'PAGE NUMBER': {'category': 'Administrative/Structural Metadata',
                 'data_type': 'Other',
                 'priority': 'DROP',
                 'risk_level': 'MEDIUM'},
 'PASSPORT NUMBER': {'category': 'Government Identifier',
                     'data_type': 'PII',
                     'priority': 'MUST_HAVE',
                     'risk_level': 'CRITICAL'},
 'PASSWORD': {'category': 'Security Credential',
              'data_type': 'Credential',
              'priority': 'MUST_HAVE',
              'risk_level': 'CRITICAL'},
 'PAYMENT CARD NUMBER (PAN)': {'category': 'Payment Card — Cardholder Data',
                               'data_type': 'Payment',
                               'priority': 'MUST_HAVE',
                               'risk_level': 'CRITICAL'},
 'PERFORMANCE RATING / REVIEW CONTENT': {'category': 'HR Sensitive Data',
                                         'data_type': 'Other',
                                         'priority': 'NICE_TO_HAVE',
                                         'risk_level': 'MEDIUM'},
 'PERMANENT ACCOUNT NUMBER — INCOME TAX (INDIA)': {'category': 'Government Identifier',
                                                   'data_type': 'PII/Financial',
                                                   'priority': 'MUST_HAVE',
                                                   'risk_level': 'HIGH'},
 'PHONE NUMBER': {'category': 'Direct Identifier', 'data_type': 'PII', 'priority': 'MUST_HAVE', 'risk_level': 'MEDIUM'},
 'PHOTOGRAPH / FACIAL IMAGE': {'category': 'Direct Identifier / Biometric-Adjacent',
                               'data_type': 'PII',
                               'priority': 'MUST_HAVE',
                               'risk_level': 'HIGH'},
 'PIN / PIN BLOCK': {'category': 'Payment Card — Sensitive Authentication Data',
                     'data_type': 'Payment',
                     'priority': 'MUST_HAVE',
                     'risk_level': 'CRITICAL'},
 'PLAN NAME': {'category': 'Administrative/Structural Metadata',
               'data_type': 'Other',
               'priority': 'DROP',
               'risk_level': 'MEDIUM'},
 'PREMIUM AMOUNT': {'category': 'Financial Data',
                    'data_type': 'PII/Financial',
                    'priority': 'NICE_TO_HAVE',
                    'risk_level': 'MEDIUM'},
 'PRIVATE CRYPTOGRAPHIC KEY / CERTIFICATE': {'category': 'Security Credential',
                                             'data_type': 'Credential',
                                             'priority': 'MUST_HAVE',
                                             'risk_level': 'CRITICAL'},
 'PROCEDURE CODE / DESCRIPTION': {'category': 'Health/Clinical Data',
                                  'data_type': 'PHI',
                                  'priority': 'NICE_TO_HAVE',
                                  'risk_level': 'MEDIUM'},
 'PURCHASE ORDER NUMBER': {'category': 'Administrative/Structural Metadata',
                           'data_type': 'Other',
                           'priority': 'DROP',
                           'risk_level': 'MEDIUM'},
 'RACIAL OR ETHNIC ORIGIN DATA': {'category': 'HR Sensitive Data — Special Category',
                                  'data_type': 'Other',
                                  'priority': 'MUST_HAVE',
                                  'risk_level': 'CRITICAL'},
 'SALARY / COMPENSATION AMOUNT': {'category': 'Financial Data',
                                  'data_type': 'Financial',
                                  'priority': 'NICE_TO_HAVE',
                                  'risk_level': 'MEDIUM'},
 'SECURITIES / PORTFOLIO HOLDINGS DETAIL': {'category': 'Financial Data',
                                            'data_type': 'Financial',
                                            'priority': 'NICE_TO_HAVE',
                                            'risk_level': 'LOW'},
 'SECURITY QUESTION & ANSWER': {'category': 'Security Credential',
                                'data_type': 'Credential',
                                'priority': 'MUST_HAVE',
                                'risk_level': 'HIGH'},
 'SESSION ID / AUTH COOKIE': {'category': 'Security Credential — Online Identifier',
                              'data_type': 'Credential',
                              'priority': 'NICE_TO_HAVE',
                              'risk_level': 'MEDIUM'},
 'SIGNATURE': {'category': 'Direct Identifier', 'data_type': 'PII', 'priority': 'MUST_HAVE', 'risk_level': 'HIGH'},
 'SOCIAL SECURITY NUMBER (SSN)': {'category': 'Government Identifier',
                                  'data_type': 'PII',
                                  'priority': 'MUST_HAVE',
                                  'risk_level': 'CRITICAL'},
 'STREET / MAILING ADDRESS': {'category': 'Direct Identifier',
                              'data_type': 'PII',
                              'priority': 'MUST_HAVE',
                              'risk_level': 'MEDIUM'},
 'TRANSACTION HISTORY / AMOUNTS': {'category': 'Financial Data',
                                   'data_type': 'Financial',
                                   'priority': 'NICE_TO_HAVE',
                                   'risk_level': 'LOW'},
 'TREATING PROVIDER NAME / NPI NUMBER': {'category': 'Direct Identifier',
                                         'data_type': 'PHI',
                                         'priority': 'NICE_TO_HAVE',
                                         'risk_level': 'MEDIUM'},
 'US TAX ID (EIN / ITIN)': {'category': 'Government Identifier',
                            'data_type': 'PII/Financial',
                            'priority': 'MUST_HAVE',
                            'risk_level': 'HIGH'},
 'USERNAME / LOGIN ID': {'category': 'Security Credential',
                         'data_type': 'Credential',
                         'priority': 'NICE_TO_HAVE',
                         'risk_level': 'MEDIUM'},
 'VEHICLE IDENTIFIER / LICENSE PLATE NUMBER': {'category': 'Quasi-Identifier',
                                               'data_type': 'PII',
                                               'priority': 'NICE_TO_HAVE',
                                               'risk_level': 'MEDIUM'},
 'VISA / IMMIGRATION DOCUMENT NUMBER': {'category': 'Government Identifier',
                                        'data_type': 'PII',
                                        'priority': 'MUST_HAVE',
                                        'risk_level': 'HIGH'}}

DROP_ENTITIES = ['ATTORNEY-CLIENT PRIVILEGE NOTATION', 'BARCODE / QR CODE INTERNAL DOCUMENT ID', 'BOILERPLATE / DISCLAIMER TEXT',
 'BOOKING REFERENCE NUMBER', 'COMPANY / EMPLOYER NAME', 'COST-SHARING AMOUNT', 'COUNTRY NAME (GENERIC)',
 'COURT / JURISDICTION NAME', 'COVERAGE EXAMPLE SCENARIO', 'CT NUMBER / IMAGING TECHNICAL PARAMETER',
 'CVE / VULNERABILITY REFERENCE', 'DOCUMENT CREATION/PRINT DATE (NON-INDIVIDUAL)', 'FACILITY ADDRESS',
 'FORM / TEMPLATE FIELD LABEL', 'INTERNAL SERVER / HOSTNAME', 'INVOICE NUMBER', 'JOB TITLE',
 'LINE-ITEM PRODUCT/SERVICE DESCRIPTION', 'MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER', 'MERCHANT / VENDOR NAME',
 'ORGANIZATION CONTACT INFO', 'PAGE NUMBER', 'PLAN NAME', 'PURCHASE ORDER NUMBER']

DOCUMENT_TYPES = ['AML Document', 'Bank Statement', 'Benefits / Performance / Disciplinary Document', 'Contract / NDA / Legal Agreement',
 'Credential & Secrets Document (API keys, tokens, passwords)', 'Credit Card Statement', 'Discharge Summary',
 'Email / Letter / General Form / Scanned Document', 'Employee Record / HR Application',
 'Explanation of Benefits (EOB) / Medical Claim', 'Health Insurance Policy / Benefits Document',
 'Healthcare Data Breach Notification Letter', 'Identity Document (Passport / Driver License / National ID / Visa)',
 'Imaging / Radiology Report', 'Investment / Brokerage Document', 'Invoice / Purchase Order', 'KYC Document',
 'Lab Report / Pathology Report', 'Litigation Document / Regulatory Filing / Compliance Document',
 'Loan / Mortgage Document', 'Medical Appointment / Appointment Reminder', 'Medical Record / Clinical Note',
 'Offer Letter / Employment Contract', 'Patient Registration / Referral', 'Payment Document / Receipt',
 'Payroll / Salary Document', 'Prescription', 'Resume / CV', 'Summary of Benefits and Coverage (SBC)',
 'System Log / Incident Report / Security Report', 'Tax Document']
