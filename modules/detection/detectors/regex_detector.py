import re

from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.models.detection_result import DetectionResult


class RegexDetector(BaseDetector):

    NAME_TOKEN_PATTERN = r"(?:[A-Z]\.|[A-Z][A-Za-z]*(?:['-][A-Z][A-Za-z]+)*)"
    LABELED_NAME_PATTERN = (
        rf"{NAME_TOKEN_PATTERN}(?:[ \t]+{NAME_TOKEN_PATTERN}){{0,3}}"
    )
    DATE_VALUE_PATTERN = (
        r"(?:\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}-[A-Za-z]{3}-\d{4}"
        r"|\d{1,2}[- \t,]+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[- \t,]+\d{2,4}\b"
        r"|(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[, \t-]+)?"
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r"[- \t]+\d{1,2}\b(?:,)?[- \t]+\d{2,4}\b)"
    )
    DATE_RANGE_VALUE_PATTERN = (
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
        r"Dec(?:ember)?)\s+\d{1,2}\s*[-–]\s*\d{1,2},?\s+\d{4}"
    )
    US_PHONE_SEPARATOR = r"[-. \t]*(?:\r?\n[ \t]*)?"
    STRUCTURED_HIGH_CONFIDENCE = {
        "EMAIL",
        "PHONE_NUMBER",
        "US_PHONE_NUMBER",
        "URL",
        "IP_ADDRESS",
        "ACCESS_CODE",
        "TRACKING_NUMBER",
    }
    DATE_TIME_VALUE_PATTERN = (
        rf"(?:{DATE_VALUE_PATTERN}(?:[T\s]+(?:at\s+)?\d{{1,2}}:\d{{2}}(?::\d{{2}})?(?:\.\d+)?(?:Z|[+-]\d{{2}}:?\d{{2}})?(?:\s*[APap][Mm])?)?"
        r"|\b\d{{1,2}}:\d{{2}}(?::\d{{2}})?(?:\s*[APap][Mm])\b"
        r"|\b\d{{2}}:\d{{2}}:\d{{2}}\b"
        r")"
    )

    @property
    def name(self) -> str:
        return "Regex"

    PATTERNS = {

        "DOCUMENT_ID":
            r"(?im)^\s*(?:Agreement ID|Document ID|Reference Number)[ \t]*[:\-][ \t]*([A-Z0-9][A-Z0-9-]{5,})[ \t]*$",

        "REPORT_ID":
            r"(?im)^\s*Report ID[ \t]*[:#\-][ \t]*([A-Z0-9][A-Z0-9-]{5,40})[ \t]*$",

        "DATE":
            rf"(?im)^\s*Date[ \t]*[:\-][ \t]*({DATE_VALUE_PATTERN})[ \t]*$",

        "DATE_RANGE":
            rf"\b{DATE_RANGE_VALUE_PATTERN}\b",

        "DATE_TIME":
            rf"\b{DATE_VALUE_PATTERN}(?:[T\s]+(?:at\s+)?\d{{1,2}}:\d{{2}}(?::\d{{2}})?(?:\.\d+)?(?:Z|[+-]\d{{2}}:?\d{{2}})?(?:\s*[APap][Mm])?)?\b"
            r"|\b\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])\b"
            r"|\b\d{2}:\d{2}:\d{2}\b",

        "EMAIL":
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",

        "PHONE_NUMBER":
            r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b",

        "AADHAAR_NUMBER":
            r"\b\d{4}\s?\d{4}\s?\d{4}\b",

        "EMPLOYEE_ID":
            r"(?im)^\s*(?:[-*][ \t]*)?Employee ID[ \t]*[:\-][ \t]*([A-Z]{2,}-?[A-Z0-9-]+)[ \t]*$",

        "PAN_NUMBER":
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",

        "DRIVING_LICENSE":
            r"(?im)^\s*(?:[-*][ \t]*)?(?:Driving License|Driver License|Driver's License|Driving Licence|Driver Licence|DL)[ \t]*[:\-][ \t]*([A-Za-z0-9-]{5,20})[ \t]*$|\b[A-Z]{2}\d{2}[ \t-]?\d{7,12}\b",

        "NATIONAL_ID":
            r"(?im)^\s*(?:[-*][ \t]*)?(?:National ID|NID)[ \t]*[:\-][ \t]*([A-Za-z0-9-]{5,20})[ \t]*$",

        "MILITARY_ID":
            r"(?im)\b(?:Military[ \t]+ID|DoD[ \t]+ID|DoD[ \t]+Number|DoD[ \t]+#|CAC[ \t]+ID|Geneva[ \t]+Convention[ \t]+ID)[ \t]*[:\-]?[ \t]*([A-Za-z0-9-]{7,20})\b",

        "TAX_ID":
            r"(?im)\b(?:EIN|Employer[ \t]+ID|ITIN|Tax[ \t]+ID)[ \t]*(?:Number|No|#)?[:\-]?[ \t]*(\d{2}-\d{7}|9\d{2}-\d{2}-\d{4}|\d{9})\b"
            r"|\b(?:SIN|Social[ \t]+Insurance)[ \t]*(?:Number|No|#)?[:\-]?[ \t]*(\d{3}[ -]\d{3}[ -]\d{3})\b",

        "CRYPTO_WALLET":
            r"(?im)^\s*(?:[-*][ \t]*)?(?:Crypto Wallet|Wallet Address)[ \t]*[:\-][ \t]*([A-Za-z0-9]{32,64})[ \t]*$",

        "PASSPORT_NUMBER":
            r"\b[A-Z][0-9]{7,8}\b",

        "CREDIT_CARD":
            r"(?im)\b(?:Card|Credit[ \t]+Card|Debit[ \t]+Card|PAN)[ \t]*(?:Number|No|#)?[ \t]*[:\-]?[ \t]*((?:\d{4}[ -]?){3,4}\d{1,4}|\d{13,19})\b"
            r"|\b(?:\d{4}[ -]){3}\d{4}\b"
            r"|\b(?:\d{4}[ -]){2}\d{4}[ -]\d{3,4}\b"
            r"|\b(?:\d[ -]?){13,19}\b",

        "CVV":
            r"(?im)\b(?:CVV|CVC|CID|CVV2|CVC2|Security[ \t]+Code)[ \t]*[:\-]?[ \t]*(\d{3,4})\b",

        "EXPIRATION_DATE":
            r"(?im)\b(?:Exp(?:iry)?|Expiration|Valid[ \t]+Thru)[ \t]*(?:Date)?[:\-]?[ \t]*((?:0[1-9]|1[0-2])[/-](?:\d{2}|\d{4}))\b",

        "RX_NUMBER":
            r"(?im)\b(?:Rx|Prescription)[ \t]*(?:Number|No|#)?[:\-]?[ \t]*([A-Z0-9-]{5,20})\b",

        "DEVICE_ID":
            r"(?im)\b(?:Device|Implant|Pacemaker|Prosthetic)[ \t]*(?:Serial|ID|#)?[:\-]?[ \t]*([A-Z0-9-]{5,30})\b",

        "GSTIN":
            r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b",

        "IFSC_CODE":
            r"\b[A-Z]{4}0[A-Z0-9]{6}\b",

        "UPI_ID":
            r"\b[a-zA-Z0-9._-]{2,}@(ybl|ibl|okicici|oksbi|okaxis|paytm|apl|axl|upi)\b",

        "URL":
            r"\b(?:https?://|www\.)\S+\b",

        "IP_ADDRESS":
            r"\b(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}\b",

        "PIN_CODE":
            r"\b\d{6}\b",

        "SSN":
            r"(?im)\b(?:SSN|Social Security Number|Social Security #|Social Security)[ \t]*[:\-]?[ \t]*((?:\d{3}|[Xx*]{3})[-\s]?(?:\d{2}|[Xx*]{2})[-\s]?\d{4}|\d{9})\b"
            r"|\b(?:\d{3}|[Xx*]{3})[-\s](?:\d{2}|[Xx*]{2})[-\s]\d{4}\b",

        "PERSON":
            rf"(?im:^\s*(?:Customer Name|Witness|Authorized Signatory|Emergency Contact)[ \t]*[:\-]?[ \t]*(?:\r?\n[ \t]*)?({LABELED_NAME_PATTERN})[ \t]*$)"
            rf"|(?ims:\bagreement\s+is\s+signed\s+between\b[^\r\n]*(?:\r?\n)[ \t]*and[ \t]+({LABELED_NAME_PATTERN})\.?)",
        "PATIENT":
            rf"(?i:\bPatient(?:[ \t]+Name)?[ \t]*[:\-][ \t]*({LABELED_NAME_PATTERN})\b)"
            rf"|(?im:\bPatient Information[ \t]*:[ \t]*(?:\r?\n)[ \t]*[•*\-]?[ \t]*Name[ \t]*[:\-][ \t]*({LABELED_NAME_PATTERN})\b)",

        "US_PHONE_NUMBER":
            rf"(?<!\w)(?:\+?1[-. \t]?)?(?:\(\d{{3}}\){US_PHONE_SEPARATOR}\d{{3}}{US_PHONE_SEPARATOR}\d{{4}}|\b\d{{3}}[-. \t]\d{{3}}[-. \t]\d{{4}}\b)",

        "PHONE_NUMBER":
            r"(?im)\b(?:Phone|Mobile|Tel|Cell|Contact)[ \t]*(?:Number|No|#)?[ \t]*[:\-]?[ \t]*((?:\+?\d{1,3}[-. \t]*)?(?:\(\d{3}\)|\d{3})[-. \t]*\d{3}[-. \t]*\d{4})\b|\b(?:\+91[-\s]?)?[6-9]\d{9}\b",

        "DATE_OF_BIRTH":
            rf"(?i:\b(?:DOB|Date of Birth|Birth Date)[ \t]*[:\-]?[ \t]*(?:\([ \t]*)?({DATE_VALUE_PATTERN})\b)",

        "START_DATE":
            rf"(?im)\b(?:Start Date|Joining Date|Hire Date)[ \t]*[:\-][ \t]*({DATE_VALUE_PATTERN})[ \t]*$",

        "VISIT_DATE":
            rf"\b(?:Visit Date|Service Date|Date of Service|Collection Date|Admission Date|Discharge Date)[ \t]*[:\-]?[ \t]*({DATE_VALUE_PATTERN})\b",

        "DOCTOR":
            rf"(?im)\b(?:Doctor|Physician|Consultant|Attending Clinician|Clinician)[ \t]*[:\-][ \t]*((?:Dr\.?[ \t]+)?{LABELED_NAME_PATTERN})[ \t]*$"
            rf"|\bDr\.?[ \t]+{LABELED_NAME_PATTERN}\b",

        "PROVIDER":
            rf"(?im)^\s*(?:Billing[ \t]+)?Provider[ \t]*[:\-][ \t]*([A-Z0-9][A-Za-z0-9&.', -]{{2,60}})[ \t]*$"
            rf"|^\s*Provider[ \t]*[:\-][ \t]*((?:Dr\.?[ \t]+)?{LABELED_NAME_PATTERN})\b",

        "HOSPITAL":
            rf"(?im)^\s*Hospital[ \t]*[:\-][ \t]*([A-Z0-9][A-Za-z0-9&.', -]{{2,60}})[ \t]*$",

        "DIAGNOSIS":
            rf"(?im)^\s*Diagnosis[ \t]*[:\-][ \t]*([A-Z0-9][A-Za-z0-9&.', -]{{2,60}})[ \t]*$",

        "MEDICATION":
            rf"(?im)^\s*Medication[ \t]*[:\-][ \t]*([A-Z0-9][A-Za-z0-9&.', -]{{2,60}})[ \t]*$",

        "PROCEDURE":
            rf"(?im)^\s*Procedure[ \t]*[:\-][ \t]*([A-Z0-9][A-Za-z0-9&.', -]{{2,60}})[ \t]*$",

        "INSURANCE_PROVIDER":
            rf"(?im)^\s*([A-Z0-9][A-Za-z0-9&.', -]{{2,60}}?\b(?:Insurance Company|Assurance Company|Health Plan|Mutual)\b)[ \t]*$",

        "ORGANIZATION":
            rf"(?im)^\s*(?:Organization|Company|Insurance Company)[ \t]*[:\-][ \t]*([A-Z0-9][A-Za-z0-9&.', -]{{2,60}})[ \t]*$"
            rf"|(?ims:\bagreement\s+is\s+signed\s+between\s+([A-Z0-9][A-Za-z0-9&.', -]{{2,60}})(?=\s+and\b|\r?\n|\Z))",

        "ADDRESS":
            r"(?ims:^[^\r\n]*\S[ \t]+(?:Address|Home Address|Mailing Address|Office Address)[ \t]*[:\-][ \t]*([^\r\n]+)[ \t]*$"
            r"|^\s*(?:Address|Home Address|Mailing Address|Office Address)[ \t]*[:\-][ \t]*(.+?)(?=\r?\n\s*(?:[A-Z][A-Za-z0-9&.', -]{2,30}[ \t]*[:\-#]|\r?\n)|\Z))",

        "ZIP_CODE":
            r"\b\d{5}(?:-\d{4})?\b",

        "BANK_ACCOUNT":
            r"(?im)\b(?:Bank[ \t]+Account|Account|Acct|A/c)[ \t]*(?:Number|No|#)?[ \t]*[:\.]?[ \t]*([A-Z0-9]{2,4}(?:[ \t\-]?[A-Z0-9]{2,6}){2,8})\b"
            r"|\b[A-Z]{2}\d{2}(?:[ \t]?[A-Z0-9]{4}){2,7}\b"
            r"|\bBank Account(?: Number)?[ \t]*[:\-][ \t]*([A-Z0-9][A-Z0-9 \t-]{7,30})[ \t]*$",

        "BRANCH_CODE":
            r"(?im)\b(?:Branch[ \t]+(?:Code|ID|Number|No|#)|SWIFT(?:-BIC)?|BIC)[ \t]*[:\-][ \t]*([A-Z0-9-]{4,20})\b",

        "MRN":
            r"(?im)\b(?:Medical Record #|MRN|Medical Record Number)[ \t]*[:\-][ \t]*([A-Z]{2,}-?[A-Z0-9-]+)\b"
            r"|\bMRN[-: \t]?\d+\b",

        "INVOICE_NUMBER":
            r"(?im)\b(?:Invoice Number|Invoice No|Invoice ID)[ \t]*[:\-][ \t]*([A-Z]{2,}-[A-Z0-9-]+)[ \t]*$",

        "POLICY_NUMBER":
            r"(?im)\b(?:Policy Number|Policy No)[ \t]*[:\-][ \t]*(POL[-: \t]?[A-Z0-9-]+)[ \t]*$",

        "ACCESS_CODE":
            r"(?im)\b(?:using|access|activation|enrollment|security)[ \t]+code[ \t]*[:#\-][ \t]*([A-Z0-9][A-Z0-9-]{5,30})\b",

        "TRACKING_NUMBER":
            r"(?im)\b(?:Certified|Registered|Priority)[ \t]+Mail[ \t]*(?:Tracking[ \t]*(?:Number|No|#)?[ \t]*)?#[ \t]*((?=(?:\d[ \t-]*){12,22}\b)\d[\d \t-]*\d)[ \t]*$",

        "CLAIM_NUMBER":
            r"(?im)\bCLM[-: \t]?[A-Z0-9-]+\b|\bClaim[ \t]*(?:Number|No|#)[ \t]*[:\-]?[ \t]*((?=[A-Z0-9-]{6,24}\b)(?=[A-Z0-9-]*\d)[A-Z0-9-]{6,24})\b",

        "INSURANCE_ID":
            r"\b(?:INS|POL|POLICY|(?!(?:CPT|DOB|SSN|BOX|ZIP|TEL|FAX|NPI|POB))[a-zA-Z]{3})[-: \t]?(?=[a-zA-Z0-9-]*\d)(?!(?:box|p\.?\s*o\.?\s*box)\b)[a-zA-Z0-9-]{5,15}\b"
            r"|(?im:(?:Medicare|Insurance|Policy|Id)[ \t]*#?[ \t]*((?=[A-Z0-9]*\d)(?!(?:box|p\.?\s*o\.?\s*box)\b)[A-Z0-9]{8,15})\b)",

        "SALARY":
            r"(?im)\bSalary[ \t]*[:\-][ \t]*(\$?[ \t]*\d[\d,]*(?:\.\d{2})?)[ \t]*$",

        "CPT_CODE":
            r"\b(?:CPT[-: \t]?)?(?:\d{5}|\d{4}[A-Z]|[A-Z]\d{4})\b",

        "ICD10_CODE":
            r"\b[A-TV-Z][0-9]{2}(?:\.[A-Z0-9]{1,4})?\b",

        "NPI_NUMBER":
            r"(?im)\b(?:NPI|Provider NPI|National Provider Identifier|NPI Number)[ \t]*[:\-]?[ \t]*([12]\d{9})\b",

        "MEMBER_ID":
            r"(?im)\b(?:Member|Mbr|Policy|Subscriber)[ \t]*(?:ID|Id|No|#)[ \t]*[:\-]?[ \t]*((?=[A-Za-z0-9-]{4,24}\b)(?=[A-Za-z0-9-]*\d)[A-Za-z0-9-]{4,24})\b",

        "GROUP_NUMBER":
            r"(?im)\bGroup[ \t]*(?:Number|No|#|ID|Id)[ \t]*[:\-]?[ \t]*((?=[A-Za-z0-9-]{4,20}\b)(?=[A-Za-z0-9-]*\d)[A-Za-z0-9-]{4,20})\b",

        "TAX_ID":
            r"\b\d{2}-\d{7}\b|(?im:\b(?:Tax ID|TIN|EIN)[ \t]*[:\-]?[ \t]*(\d{2}-\d{7}|\d{9})\b)",

        "EOB_NUMBER":
            r"(?im)\b(?:EOB|Explanation of Benefits)[ \t]*(?:Number|No|#)[ \t]*[:\-]?[ \t]*((?=[A-Z0-9-]{6,24}\b)(?=[A-Z0-9-]*\d)[A-Z0-9-]{6,24})\b",

        "PO_BOX":
            r"\b[Pp]\.?[Oo]\.?\s+Box\s+\d+\b|\bBox\s+\d+\b",

        "CLINICAL_MEASUREMENT":
            r"\b\d+(?:\.\d+)?\s*(?:mg/dL|%)\b",

        "VITAL_SIGN":
            r"\b\d{2,3}/\d{2,3}\s*(?:mmHg)?\b",

        "CITY_STATE_ZIP":
            r"(?im)\b(?:City,?[ \t]*State[ \t]*(?:and[ \t]*)?Zip|City/State/Zip|CSZ)[ \t]*[:\-][ \t]*([A-Za-z\s.'-]+,[ \t]*[A-Z]{2})(?=[ \t]+\d{5})\b"
            r"|\b([A-Z][a-zA-Z\s.'-]+,[ \t]*[A-Z]{2})(?=[ \t]+\d{5})\b",

        "FINANCIAL_AMOUNT":
            r"(?im)\b(?:Total(?:[ \t]+(?:Amount|Due|Paid|Billed|Claimed))?|Amount(?:[ \t]+(?:Due|Paid|Billed|Claimed))?|Billed[ \t]+Amount|Copay|Coinsurance|Deductible|Premium(?:[ \t]+Due)?|Monthly[ \t]+Premium|Gross[ \t]+Salary|Net[ \t]+Pay|Account[ \t]+Balance|Payment[ \t]+Amount)[ \t]*[:\-][ \t]*(\$?[ \t]*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b"
            r"|(?:\$|USD\s*|EUR\s*|INR\s*|Rs\.?\s*)\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})\b",

        "DOSAGE":
            r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g)\b",
    }
    ENTITY_PRIORITY = {
        "BANK_ACCOUNT": 101,
        "CREDIT_CARD": 101,
        "BRANCH_CODE": 100,
        "CVV": 100,
        "MILITARY_ID": 98,
        "SSN": 96,
        "TAX_ID": 95,
        "DOCUMENT_ID": 94,
        "REPORT_ID": 94,
        "TRACKING_NUMBER": 93,
        "ACCESS_CODE": 92,
        "MRN": 92,
        "RX_NUMBER": 92,
        "DEVICE_ID": 92,
        "CLAIM_NUMBER": 91,
        "POLICY_NUMBER": 91,
        "INSURANCE_ID": 90,
        "PASSPORT_NUMBER": 90,
        "EMPLOYEE_ID": 89,
        "GSTIN": 88,
        "DRIVING_LICENSE": 87,
        "EXPIRATION_DATE": 86,
        "PATIENT": 86,
        "PERSON": 86,
        "DOCTOR": 86,
        "HOSPITAL": 86,
        "DATE_OF_BIRTH": 85,
        "DATE_RANGE": 84,
        "VISIT_DATE": 84,
        "START_DATE": 84,
        "INSURANCE_PROVIDER": 89,
        "PROVIDER": 88,
        "ADDRESS": 82,
        "CITY_STATE_ZIP": 80,
        "ZIP_CODE": 85,
        "PO_BOX": 82,
        "DIAGNOSIS": 82,
        "MEDICATION": 82,
        "PROCEDURE": 82,
        "PAN_NUMBER": 80,
        "FINANCIAL_AMOUNT": 78,
        "NPI_NUMBER": 90,
        "MEMBER_ID": 90,
        "GROUP_NUMBER": 90,
        "EOB_NUMBER": 90,
        "SALARY": 75,
        "ORGANIZATION": 74,
        "AADHAAR_NUMBER": 70,
        "IFSC_CODE": 60,
        "UPI_ID": 50,
        "DATE": 50,
        "DATE_TIME": 48,
        "US_PHONE_NUMBER": 45,
        "PHONE_NUMBER": 40,
        "EMAIL": 30,
        "INVOICE_NUMBER": 30,
        "CPT_CODE": 25,
        "ICD10_CODE": 24,
        "CLINICAL_MEASUREMENT": 25,
        "VITAL_SIGN": 25,
        "DOSAGE": 20,
        "URL": 20,
        "IP_ADDRESS": 10,
        "ZIP_CODE": 6,
        "PIN_CODE": 5,
    }
    CONTEXT = {
        "DOCUMENT_ID": ["agreement id", "document id", "reference number"],
        "REPORT_ID": ["report id"],
        "TRACKING_NUMBER": ["certified mail", "registered mail", "tracking"],
        "ACCESS_CODE": ["using code", "access code", "activation code", "enrollment code"],
        "DATE": ["date"],
        "DATE_RANGE": ["date", "between", "from", "incident", "account"],
        "DATE_TIME": ["date", "time", "at", "visited", "on", "dob", "birth", "service", "admission", "discharge", "collection"],
        "EMAIL": ["email", "mail"],
        "PHONE_NUMBER": ["phone", "mobile", "contact"],
        "US_PHONE_NUMBER": ["phone", "mobile", "contact"],
        "EMPLOYEE_ID": ["employee id"],
        "AADHAAR_NUMBER": ["aadhaar", "uid"],
        "PAN_NUMBER": ["pan"],
        "PASSPORT_NUMBER": ["passport"],
        "DRIVING_LICENSE": ["driving license", "driver license"],
        "CREDIT_CARD": ["card", "visa", "mastercard", "debit", "credit", "pan"],
        "CVV": ["cvv", "cvc", "cid", "security code"],
        "EXPIRATION_DATE": ["exp", "expiry", "expiration", "valid thru"],
        "BANK_ACCOUNT": ["iban", "bank", "account", "bank account", "a/c"],
        "BRANCH_CODE": ["branch", "branch code", "code", "swift", "bic", "bank"],
        "MILITARY_ID": ["military", "dod", "dod id", "cac", "defense", "geneva"],
        "TAX_ID": ["tax", "tin", "ein", "itin", "sin", "employer"],
        "RX_NUMBER": ["rx", "prescription", "rx#", "pharmacy"],
        "DEVICE_ID": ["device", "implant", "serial", "pacemaker", "prosthetic"],
        "GSTIN": ["gstin", "gst"],
        "IFSC_CODE": ["ifsc", "bank"],
        "UPI_ID": ["upi", "payment"],
        "IP_ADDRESS": ["ip"],
        "PIN_CODE": ["pin", "zipcode", "postal"],
        "SSN": ["ssn", "social security"],
        "PERSON": ["customer name", "witness", "authorized signatory", "emergency contact"],
        "PATIENT": ["patient", "patient name"],
        "DATE_OF_BIRTH": ["dob", "date of birth"],
        "START_DATE": ["start date", "joining date", "hire date"],
        "VISIT_DATE": ["visit date", "service date", "date of service", "collection date"],
        "DOCTOR": ["doctor", "physician", "consultant"],
        "HOSPITAL": ["hospital", "clinic", "medical facility"],
        "INSURANCE_PROVIDER": ["insurance", "insurance company", "health plan"],
        "ORGANIZATION": ["organization", "company", "insurance company", "agreement", "signed between"],
        "PROVIDER": ["provider"],
        "ADDRESS": ["address", "mailing address", "home address", "office address"],
        "ZIP_CODE": ["zip", "zipcode", "postal"],
        "MRN": ["mrn", "medical record"],
        "INVOICE_NUMBER": ["invoice"],
        "POLICY_NUMBER": ["policy"],
        "CLAIM_NUMBER": ["claim"],
        "INSURANCE_ID": ["insurance", "policy"],
        "SALARY": ["salary"],
        "DIAGNOSIS": ["diagnosis"],
        "MEDICATION": ["medication"],
        "PROCEDURE": ["procedure"],
        "CPT_CODE": ["cpt"],
        "ICD10_CODE": ["diagnosis", "icd"],
        "NPI_NUMBER": ["npi", "provider", "tax", "billing", "national provider"],
        "MEMBER_ID": ["member", "mbr", "id", "policy", "subscriber"],
        "GROUP_NUMBER": ["group", "grp", "number", "id"],
        "EOB_NUMBER": ["eob", "explanation", "benefits", "number"],
        "PO_BOX": ["box", "po box", "p.o. box", "address"],
        "CLINICAL_MEASUREMENT": ["a1c", "cholesterol", "hdl", "ldl", "triglycerides", "mg/dl", "%"],
        "VITAL_SIGN": ["blood pressure", "bp", "mmhg", "vital"],
        "DOSAGE": ["mg", "mcg", "dosage", "dose", "tablet", "capsule"],
    }
    GROUP_VALUE_ENTITIES = {
        "ADDRESS",
        "CITY_STATE_ZIP",
        "FINANCIAL_AMOUNT",
        "BANK_ACCOUNT",
        "BRANCH_CODE",
        "MILITARY_ID",
        "TAX_ID",
        "CREDIT_CARD",
        "CVV",
        "EXPIRATION_DATE",
        "RX_NUMBER",
        "DEVICE_ID",
        "DATE",
        "DATE_RANGE",
        "DATE_OF_BIRTH",
        "DIAGNOSIS",
        "DOCTOR",
        "DOCUMENT_ID",
        "REPORT_ID",
        "TRACKING_NUMBER",
        "ACCESS_CODE",
        "DRIVING_LICENSE",
        "EMPLOYEE_ID",
        "HOSPITAL",
        "INSURANCE_ID",
        "INSURANCE_PROVIDER",
        "INVOICE_NUMBER",
        "MEDICATION",
        "MRN",
        "ORGANIZATION",
        "PATIENT",
        "PERSON",
        "POLICY_NUMBER",
        "PROCEDURE",
        "PROVIDER",
        "SALARY",
        "START_DATE",
        "VISIT_DATE",
        "CLAIM_NUMBER",
        "EOB_NUMBER",
        "MEMBER_ID",
        "GROUP_NUMBER",
        "SSN",
    }
    LABELED_NAME_PLACEHOLDERS = {
        "anonymous",
        "na",
        "n a",
        "none",
        "not available",
        "not applicable",
        "null",
        "redacted",
        "tbd",
        "to be determined",
        "unavailable",
        "unknown",
        "withheld",
    }
    INVALID_IDENTIFIER_VALUES = {
        "claim",
        "group",
        "id",
        "member",
        "messages",
        "name",
        "number",
        "processed",
        "received",
        "status",
    }

    LABELED_NAME_ROLE_VALUES = {
        "account holder",
        "billing department",
        "card holder",
        "claims department",
        "customer service",
        "help desk",
        "insurance company",
        "main hospital",
        "medical center",
        "policy holder",
    }

    NON_PERSON_NAME_TERMS = {
        "account",
        "amount",
        "benefit",
        "benefits",
        "billing",
        "billed",
        "card",
        "center",
        "claim",
        "clinic",
        "company",
        "corp",
        "corporation",
        "covered",
        "customer",
        "department",
        "diagnosis",
        "group",
        "help",
        "holder",
        "hospital",
        "inc",
        "insurance",
        "lab",
        "laboratory",
        "llc",
        "ltd",
        "medical",
        "pharmacy",
        "policy",
        "procedure",
        "service",
        "unknown",
    }

    def detect(
        self,
        text: str,
        page_number: int = 1,
    ) -> list[DetectionResult]:

        detections: list[DetectionResult] = []

        for entity, pattern in self.PATTERNS.items():

            for match in re.finditer(pattern, text):

                value, start_char, end_char = self.extract_value_span(
                    entity,
                    match,
                )

                # Enforce contextual verification for CPT_CODE to prevent ZIP_CODE collisions
                if entity == "CPT_CODE":
                    if not self.has_context(entity, text, start_char):
                        continue

                # Avoid classifying bank account numbers as credit cards.
                is_checksum_failed_candidate = False
                if entity == "CREDIT_CARD":
                    if self.has_context("BANK_ACCOUNT", text, start_char):
                        continue
                    if not self.validate(entity, value):
                        if self.has_context("CREDIT_CARD", text, start_char):
                            is_checksum_failed_candidate = True
                        else:
                            continue

                # Enforce contextual verification for ADDRESS to avoid masking placeholders.
                if entity == "ADDRESS":
                    if not self.validate_address_value(value):
                        continue

                # Enforce contextual verification for ZIP_CODE to avoid matching street numbers
                if entity == "ZIP_CODE":
                    if not self.validate_zip_code(value, text, start_char):
                        continue

                # Enforce contextual verification for PIN_CODE to avoid matching salaries/numbers
                if entity == "PIN_CODE":
                    if not self.validate_pin_code(value, text, start_char):
                        continue

                # Avoid treating invoice/reference IDs as insurance IDs without insurance context.
                if entity == "INSURANCE_ID":
                    if not self.validate_insurance_id(value, text, start_char):
                        continue

                # Enforce contextual verification for AADHAAR_NUMBER to avoid random 12-digit numbers
                if entity == "AADHAAR_NUMBER":
                    if not self.has_context(entity, text, start_char):
                        continue

                if entity in {"PATIENT", "PERSON", "DOCTOR"}:
                    CLINICAL_SUFFIXES = [
                        " Office Visit", " Specialist Consult", " Consult", " Consultation",
                        " Follow Up", " Follow-Up", " Evaluation", " Exam", " Examination",
                        " Surgery", " Procedure", " Therapy", " Clinic", " Hospital",
                        " Center", " Service", " Department", " Standard",
                    ]
                    for suffix in CLINICAL_SUFFIXES:
                        if value.lower().endswith(suffix.lower()):
                            strip_len = len(suffix)
                            value = value[:-strip_len].strip()
                            end_char = start_char + len(value)
                            break

                    if not self.validate_labeled_person_value(value):
                        continue

                elif entity == "PROVIDER":
                    if not value.strip():
                        continue
                    if any(term in value.lower() for term in ["customer service", "main hospital"]):
                        continue

                if entity in {"CLAIM_NUMBER", "MEMBER_ID", "GROUP_NUMBER", "EOB_NUMBER"}:
                    if not self.validate(entity, value):
                        continue

                confidence = self.calculate_confidence(
                    entity,
                    value,
                    text,
                    start_char,
                )
                if is_checksum_failed_candidate:
                    confidence = 0.40

                detections.append(
                    DetectionResult(
                        entity_type=entity,
                        entity_value=value,
                        confidence_score=confidence,
                        start_char=start_char,
                        end_char=end_char,
                        page_number=page_number,
                        detector=self.name,
                        metadata={
                            "method": "hybrid_regex",
                            "resolved": True,
                        },
                    )
                )

        # -----------------------------------------
        # Resolve overlapping matches
        # -----------------------------------------

        detections.sort(
            key=lambda entity: (
                -self.ENTITY_PRIORITY.get(entity.entity_type, 0),
                entity.start_char,
            )
        )

        filtered = []

        for entity in detections:

            if not self.has_overlap(
                entity.start_char,
                entity.end_char,
                filtered,
            ):
                filtered.append(entity)

        filtered.sort(
            key=lambda entity: entity.start_char
        )

        return filtered

    @staticmethod
    def extract_value_span(
        entity: str,
        match: re.Match,
    ) -> tuple[str, int, int]:
        if entity in RegexDetector.GROUP_VALUE_ENTITIES and match.lastindex:
            for group_index in range(1, match.lastindex + 1):
                value = match.group(group_index)
                if value is None:
                    continue

                start = match.start(group_index)
                end = match.end(group_index)
                leading = len(value) - len(value.lstrip())
                trailing = len(value.rstrip())
                return value.strip(), start + leading, start + trailing

        return match.group(), match.start(), match.end()

    def has_overlap(
            self,
            start: int,
            end: int,
            accepted: list[DetectionResult],
        ) -> bool:
            """
            Check whether the current match overlaps with an
            already accepted higher-priority entity.
            """

            for entity in accepted:

                if start < entity.end_char and end > entity.start_char:
                    return True

            return False

    def calculate_confidence(
        self,
        entity: str,
        value: str,
        text: str,
        start: int,
    ) -> float:

        if (
            entity in self.STRUCTURED_HIGH_CONFIDENCE
            and self.validate(entity, value)
        ):
            return 1.0

        score = 0.40
        if entity == "DATE_TIME":
            score = 0.55

        if self.has_context(entity, text, start):
            score += 0.30

        if self.validate(entity, value):
            score += 0.30

        return round(min(score, 1.0), 2)

    def has_context(
        self,
        entity: str,
        text: str,
        start: int,
    ) -> bool:

        window = 160 if entity == "CPT_CODE" else 40

        if entity == "CPT_CODE":
            line_start = text.rfind("\n", 0, start) + 1
            line_end = text.find("\n", start)
            if line_end == -1:
                line_end = len(text)
            line = text[line_start:line_end]
            offset = start - line_start
            if (
                re.search(self.DATE_VALUE_PATTERN, line[:offset], re.IGNORECASE)
                and re.search(r"\b[A-TV-Z][0-9]{2}(?:\.[A-Z0-9]{1,4})?\b", line[offset:], re.IGNORECASE)
            ):
                return True

        left = max(0, start - window)
        right = min(len(text), start + window)

        context = text[left:right].lower()

        keywords = self.CONTEXT.get(entity, [])

        return any(keyword in context for keyword in keywords)

    def validate(
        self,
        entity: str,
        value: str,
    ) -> bool:

        if entity == "CREDIT_CARD":
            return self.luhn(value)

        if entity == "BANK_ACCOUNT":
            return self.validate_bank_account_value(value)

        if entity == "AADHAAR_NUMBER":
            return len(re.sub(r"\D", "", value)) == 12

        if entity == "PAN_NUMBER":
            return bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", value))

        if entity == "PASSPORT_NUMBER":
            return bool(re.fullmatch(r"[A-Z][0-9]{7,8}", value))

        if entity == "DRIVING_LICENSE":
            return bool(re.fullmatch(r"[A-Z]{2}\d{2}[ \t-]?\d{7,12}", value))

        if entity == "GSTIN":
            return bool(re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", value))

        if entity == "PHONE_NUMBER":
            return len(re.sub(r"\D", "", value)[-10:]) == 10

        if entity == "SSN":
            clean = re.sub(r"\D", "", value)
            return len(clean) == 9 and not clean.startswith("000") and clean != "123456789"

        if entity == "US_PHONE_NUMBER":
            digits = re.sub(r"\D", "", value)
            if digits.startswith("1"):
                digits = digits[1:]
            return len(digits) == 10

        if entity == "PROVIDER":
            return self.validate_provider_value(value)

        if entity in {"PATIENT", "PERSON", "DOCTOR"}:
            return self.validate_labeled_person_value(value)

        if entity == "HOSPITAL":
            return self.validate_facility_value(value)

        if entity == "ORGANIZATION":
            return self.validate_organization_value(value)

        if entity == "ADDRESS":
            return self.validate_address_value(value)

        if entity in {"DATE", "DATE_OF_BIRTH", "START_DATE", "VISIT_DATE"}:
            return self.validate_date_value(value)

        if entity == "DATE_RANGE":
            return bool(
                re.fullmatch(
                    self.DATE_RANGE_VALUE_PATTERN,
                    value.strip(),
                    re.IGNORECASE,
                )
            )

        if entity == "DATE_TIME":
            return self.validate_date_time_value(value)

        if entity in {
            "ACCESS_CODE",
            "DOCUMENT_ID",
            "EMPLOYEE_ID",
            "INVOICE_NUMBER",
            "POLICY_NUMBER",
            "REPORT_ID",
        }:
            return bool(re.fullmatch(r"[A-Z0-9][A-Z0-9-]{4,}", value.strip().upper()))

        if entity == "TRACKING_NUMBER":
            digits = re.sub(r"\D", "", value)
            return 12 <= len(digits) <= 22

        if entity == "SALARY":
            return bool(re.fullmatch(r"\$?[ \t]*\d[\d,]*(?:\.\d{2})?", value.strip()))

        if entity in {"DIAGNOSIS", "MEDICATION", "PROCEDURE"}:
            return self.validate_labeled_text_value(value)

        if entity == "ZIP_CODE":
            return bool(re.fullmatch(r"\d{5}(-\d{4})?", value))

        if entity == "MRN":
            return bool(re.search(r"\d+", value))

        if entity == "CLAIM_NUMBER":
            normalized = value.strip()
            return bool(
                len(normalized) > 6
                and normalized.lower() not in self.INVALID_IDENTIFIER_VALUES
                and re.fullmatch(r"[A-Za-z0-9-]+", normalized)
                and re.search(r"\d", normalized)
            )

        if entity == "INSURANCE_ID":
            # Disallow matches containing PO Box to avoid collisions
            if re.search(r"(?i)\b(?:box|p\.?\s*o\.?\s*box)\b", value):
                return False
            return len(value) > 4

        if entity == "CPT_CODE":
            normalized = re.sub(r"[^A-Za-z0-9]", "", value).upper()
            if normalized.startswith("CPT"):
                normalized = normalized[3:]
            return bool(re.fullmatch(r"\d{5}|\d{4}[A-Z]|[A-Z]\d{4}", normalized))

        if entity == "ICD10_CODE":
            return bool(re.fullmatch(r"[A-TV-Z][0-9]{2}(\.[A-Z0-9]{1,4})?", value))

        if entity == "NPI_NUMBER":
            return self.is_valid_npi(value)

        if entity == "TAX_ID":
            clean = value.replace("-", "").strip()
            return len(clean) == 9 and clean.isdigit()

        if entity in {"MEMBER_ID", "GROUP_NUMBER", "EOB_NUMBER"}:
            normalized = value.strip()
            return bool(
                len(normalized) >= 4
                and normalized.lower() not in self.INVALID_IDENTIFIER_VALUES
                and re.fullmatch(r"[A-Za-z0-9-]+", normalized)
                and re.search(r"\d", normalized)
            )

        if entity == "PO_BOX":
            return bool(re.search(r"(?i)\bbox\s+\d+\b", value))

        if entity in {"CLINICAL_MEASUREMENT", "VITAL_SIGN", "DOSAGE"}:
            return len(value.strip()) > 0

        return True

    def validate_bank_account_value(self, value: str) -> bool:
        normalized = re.sub(r"[\s-]+", "", value.strip()).upper()
        if normalized.startswith(("IBAN", "ACCOUNT")):
            return False
        if normalized.isdigit():
            return 8 <= len(normalized) <= 18
        return bool(re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", normalized))

    def validate_date_value(self, value: str) -> bool:
        return bool(re.fullmatch(self.DATE_VALUE_PATTERN, value.strip(), re.IGNORECASE))

    def validate_date_time_value(self, value: str) -> bool:
        return bool(re.fullmatch(self.DATE_TIME_VALUE_PATTERN, value.strip(), re.IGNORECASE))

    def validate_labeled_text_value(self, value: str) -> bool:
        normalized = " ".join(value.strip().split())
        normalized_key = normalized.lower()
        if len(normalized) < 3:
            return False
        if normalized_key in self.LABELED_NAME_PLACEHOLDERS:
            return False
        return not re.fullmatch(r"[-_/.,\s]+", normalized)

    def validate_facility_value(self, value: str) -> bool:
        normalized = " ".join(value.strip().split())
        normalized_key = normalized.lower()
        if not self.validate_labeled_text_value(normalized):
            return False
        return any(
            keyword in normalized_key
            for keyword in ("hospital", "clinic", "medical", "care", "health")
        )

    def validate_organization_value(self, value: str) -> bool:
        normalized = " ".join(value.strip().split())
        normalized_key = normalized.lower()
        if not self.validate_labeled_text_value(normalized):
            return False
        if normalized_key in {"company information", "organization", "insurance company"}:
            return False
        return bool(re.search(r"[A-Za-z]{3,}", normalized))

    def validate_provider_value(self, value: str) -> bool:
        normalized = " ".join(value.strip().split())
        normalized_key = normalized.lower()
        if not self.validate_labeled_text_value(normalized):
            return False
        if normalized_key in self.LABELED_NAME_ROLE_VALUES:
            return False
        if self.validate_labeled_person_value(normalized):
            return True
        if any(
            keyword in normalized_key
            for keyword in (
                "hospital",
                "clinic",
                "medical center",
                "healthcare",
                "health system",
                "family medicine",
            )
        ):
            return True
        return bool(re.search(r"\b(?:md|do|np|pa-c)\b", normalized_key))

    def validate_address_value(self, value: str) -> bool:
        normalized = " ".join(value.strip().split())
        normalized_key = normalized.lower()

        if not normalized or len(normalized) < 5:
            return False

        if normalized_key in self.LABELED_NAME_PLACEHOLDERS:
            return False

        if re.fullmatch(r"(?i)(n/?a|none|unknown|not available|not applicable|redacted)", normalized):
            return False

        lines = [line.strip() for line in value.splitlines() if line.strip()]
        if len(lines) > 1:
            first_line = lines[0].lower()
            rest = " ".join(lines[1:])
            if (
                re.search(r"\b(?:insurance|company|department|corp|corporation|llc|ltd)\b", first_line)
                and re.search(r"\b(?:p\.?o\.?\s+box|box\s+\d+|\d{5}(?:-\d{4})?)\b", rest, re.IGNORECASE)
            ):
                return False

        # UK postcode or military APO/FPO/DPO formats are common in OCR output.
        if re.search(r"\b[A-Z]{1,2}\d[A-Z\d]?[ \t]*\d[A-Z]{2}\b", normalized):
            return True

        if re.search(r"\b(?:APO|FPO|DPO)\s+(?:AA|AE|AP)\s+\d{5}(?:-\d{4})?\b", normalized):
            return True

        if re.search(r"\b\d{5}(?:-\d{4})?\b", normalized) and re.search(r"\b[A-Z]{2}\b", normalized):
            return True

        if re.search(r"\b(?:P\.?O\.? Box|Suite|Apt|Apartment|Unit)\b", normalized, re.IGNORECASE):
            return True

        street_suffixes = (
            "Avenue", "Ave", "Boulevard", "Blvd", "Court", "Ct", "Drive", "Dr",
            "Lane", "Ln", "Road", "Rd", "Street", "St", "Way",
        )
        suffix_pattern = "|".join(street_suffixes)
        if re.search(rf"\b\d+[A-Za-z]?\s+.+\s+(?:{suffix_pattern})\.?\b", normalized):
            return True

        return bool(re.search(r",\s*[A-Z][A-Za-z .'-]+(?:,\s*[A-Z]{2})?\b", normalized))

    def validate_labeled_person_value(self, value: str) -> bool:
        normalized = " ".join(value.strip().split())
        normalized_key = re.sub(r"[^a-z0-9]+", " ", normalized.lower()).strip()

        if not normalized or len(normalized) < 3:
            return False

        if normalized_key in self.LABELED_NAME_PLACEHOLDERS:
            return False

        if normalized_key in self.LABELED_NAME_ROLE_VALUES:
            return False

        if re.search(r"\d|@|://|www\.|[$]", normalized):
            return False

        terms = set(re.findall(r"[a-z]+", normalized_key))
        if terms & self.NON_PERSON_NAME_TERMS:
            return False

        tokens = re.findall(
            rf"(?:Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Prof\.?|{self.NAME_TOKEN_PATTERN})",
            normalized,
        )
        name_tokens = [
            token
            for token in tokens
            if token.lower().rstrip(".") not in {"dr", "mr", "mrs", "ms", "prof"}
        ]

        if not name_tokens:
            return False

        return all(
            re.fullmatch(self.NAME_TOKEN_PATTERN, token)
            for token in name_tokens
        )

    def validate_zip_code(self, value: str, text: str, start: int) -> bool:
        """
        Ensures a 5-digit number is only classified as a ZIP_CODE if it is either:
        1. Preceded by a US state abbreviation (e.g. UT 12036, AP 81970).
        2. Or matches context keywords within a 40-character window.
        This prevents false positives on 5-digit street numbers (e.g. 00480 Cook Cove).
        """
        US_STATES = {
            "AL", "AK", "AS", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FM", "FL", "GA",
            "GU", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MH", "MD", "MA",
            "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND",
            "MP", "OH", "OK", "OR", "PW", "PA", "PR", "RI", "SC", "SD", "TN", "TX", "UT",
            "VT", "VI", "VA", "WA", "WV", "WI", "WY", "AE", "AA", "AP"
        }
        # Check if preceded by a US state abbreviation
        preceding = text[max(0, start - 10):start].strip()
        state_match = re.search(r'\b([A-Z]{2})\s*$', preceding)
        if state_match and state_match.group(1) in US_STATES:
            return True
        # Check if keyword context exists
        return self.has_context("ZIP_CODE", text, start)

    def validate_insurance_id(self, value: str, text: str, start: int) -> bool:
        normalized = value.upper()
        has_explicit_prefix = normalized.startswith(("INS", "POL", "POLICY"))
        return has_explicit_prefix or self.has_context("INSURANCE_ID", text, start)

    def validate_pin_code(self, value: str, text: str, start: int) -> bool:
        """
        Ensures a 6-digit number is only classified as a PIN_CODE if it is not a currency/salary
        and is either preceded by an Indian state name/abbreviation or matches pin context.
        """
        # Check if preceded by currency or salary markers
        preceding = text[max(0, start - 15):start].strip()
        if any(curr in preceding.lower() for curr in ["$", "₹", "rs", "rs.", "usd", "eur", "gbp", "salary"]):
            return False

        INDIAN_STATES = {
            "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DN", "DD", "DL", "GA", "GJ", "HR",
            "HP", "JK", "JH", "KA", "KL", "LA", "LD", "MP", "MH", "MN", "ML", "MZ", "NL",
            "OD", "PY", "PB", "RJ", "SK", "TN", "TS", "TR", "UP", "UK", "WB",
            "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa",
            "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka", "kerala",
            "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland",
            "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
            "uttar pradesh", "uttarakhand", "west bengal"
        }
        state_match = re.search(r'\b([A-Za-z]{2,15})\s*[-:\s]*$', preceding.lower())
        if state_match and state_match.group(1).upper() in INDIAN_STATES:
            return True

        # Check if keyword context exists
        return self.has_context("PIN_CODE", text, start)

    def luhn(
        self,
        number: str,
    ) -> bool:

        digits = re.sub(r"\D", "", number)

        total = 0

        reverse = digits[::-1]

        for i, d in enumerate(reverse):

            n = int(d)

            if i % 2 == 1:

                n *= 2

                if n > 9:
                    n -= 9

            total += n

        return total % 10 == 0
