from modules.detection.models.detection_result import DetectionResult
from modules.detection.taxonomy import TaxonomyService


class EntityMapper:
    """
    Maps detector-specific entity labels to a common schema.
    """

    ENTITY_MAPPING = {

        # ==========================
        # PERSON
        # ==========================
        "PERSON": "PERSON",
        "PATIENT": "PATIENT",
        "DOCTOR": "DOCTOR",
        "PHYSICIAN": "PHYSICIAN",
        "NURSE": "NURSE",
        "HEALTHCARE STAFF": "HEALTHCARE_STAFF",
        "HEALTHCARE_STAFF": "HEALTHCARE_STAFF",
        "PROVIDER": "PROVIDER",
        "EMPLOYEE_ID": "EMPLOYEE_ID",
        "DRIVING_LICENSE": "DRIVING_LICENSE",
        "START_DATE": "START_DATE",
        "SALARY": "SALARY",
        "POLICY_NUMBER": "POLICY_NUMBER",
        "ACCESS_CODE": "ACCESS_CODE",
        "TRACKING_NUMBER": "TRACKING_NUMBER",

        # ==========================
        # ORGANIZATION
        # ==========================
        "ORG": "ORGANIZATION",
        "ORGANIZATION": "ORGANIZATION",
        "COMPANY": "ORGANIZATION",
        "HOSPITAL": "HOSPITAL",
        "CLINIC": "ORGANIZATION",
        "INSTITUTE": "ORGANIZATION",
        "MEDICAL FACILITY": "MEDICAL_FACILITY",
        "MEDICAL_FACILITY": "MEDICAL_FACILITY",
        "HEALTHCARE ORGANIZATION": "HEALTHCARE_ORGANIZATION",
        "HEALTHCARE_ORGANIZATION": "HEALTHCARE_ORGANIZATION",
        "INSURANCE_PROVIDER": "INSURANCE_PROVIDER",

        # ==========================
        # ADDRESS
        # ==========================
        "ADDRESS": "ADDRESS",
        "CITY_STATE_ZIP": "ADDRESS",
        "LOCATION": "LOCATION",
        "CITY": "CITY",
        "STATE": "STATE",
        "COUNTRY": "COUNTRY",
        "ZIP": "ZIP_CODE",
        "POSTAL_CODE": "ZIP_CODE",

        # ==========================
        # CONTACT
        # ==========================
        "EMAIL": "EMAIL",
        "EMAIL_ADDRESS": "EMAIL",

        # ==========================
        # CONTACT
        # ==========================
        "PHONE": "PHONE_NUMBER",
        "PHONE NUMBER": "PHONE_NUMBER",
        "PHONE_NUMBER": "PHONE_NUMBER",
        "US_PHONE_NUMBER": "PHONE_NUMBER",
        "MOBILE": "PHONE_NUMBER",
        "CUSTOMER_SERVICE_NUMBER": "CUSTOMER_SERVICE_NUMBER",
        "ORGANIZATION_CONTACT_INFO": "ORGANIZATION_CONTACT_INFO",

        "URL": "URL",
        "IP_ADDRESS": "IP_ADDRESS",

        # ==========================
        # GOVERNMENT IDS
        # ==========================
        "AADHAAR": "AADHAAR_NUMBER",
        "AADHAAR NUMBER": "AADHAAR_NUMBER",

        "PAN": "PAN_NUMBER",
        "PAN NUMBER": "PAN_NUMBER",

        "PASSPORT": "PASSPORT_NUMBER",
        "PASSPORT NUMBER": "PASSPORT_NUMBER",

        "DRIVING LICENSE": "DRIVING_LICENSE",
        "DRIVER_LICENSE": "DRIVING_LICENSE",

        "VOTER ID": "VOTER_ID",

        # ==========================
        # FINANCIAL
        # ==========================
        "BANK ACCOUNT": "BANK_ACCOUNT_NUMBER",
        "BANK_ACCOUNT": "BANK_ACCOUNT_NUMBER",
        "BANK ACCOUNT NUMBER": "BANK_ACCOUNT_NUMBER",
        "FINANCIAL_AMOUNT": "FINANCIAL_AMOUNT",
        "AMOUNT": "FINANCIAL_AMOUNT",
        "COST_SHARING_AMOUNT": "COST_SHARING_AMOUNT",
        "PREMIUM_AMOUNT": "PREMIUM_AMOUNT",

        "IFSC": "IFSC_CODE",

        "CREDIT_CARD": "CREDIT_CARD_NUMBER",
        "CREDIT CARD": "CREDIT_CARD_NUMBER",

        "DEBIT CARD": "DEBIT_CARD_NUMBER",

        "IBAN_CODE": "IBAN",

        "SWIFT": "SWIFT_CODE",

        "UPI": "UPI_ID",

        # ==========================
        # DATES
        # ==========================
        "DATE": "DATE",
        "DATE_TIME": "DATE_TIME",
        "DATE_RANGE": "DATE_RANGE",
        "VISIT_DATE": "VISIT_DATE",
        "DATE_OF_SERVICE": "DATE_OF_SERVICE",
        "DOCUMENT_CREATION_DATE": "DOCUMENT_CREATION_DATE",
        "COVERAGE_DATE": "COVERAGE_DATE",
        "DUE_DATE": "DUE_DATE",
        "TIME": "TIME",
        "AGE": "AGE",

        # ==========================
        # MEDICAL IDENTIFIERS
        # ==========================
        "MRN": "MEDICAL_RECORD_NUMBER",
        "MEDICAL RECORD NUMBER": "MEDICAL_RECORD_NUMBER",
        "NPI": "NPI_NUMBER",
        "NPI_NUMBER": "NPI_NUMBER",
        "MEMBER_ID": "MEMBER_ID",
        "GROUP_NUMBER": "GROUP_NUMBER",
        "TAX_ID": "TAX_ID",
        "EIN": "TAX_ID",
        "EOB_NUMBER": "EOB_NUMBER",
        "PO_BOX": "ADDRESS",
        "CLINICAL_MEASUREMENT": "CLINICAL_MEASUREMENT",

        "PATIENT_ID": "PATIENT_ID",

        "INSURANCE ID": "INSURANCE_ID",

        # ==========================
        # CLINICAL
        # ==========================
        "PROBLEM": "PROBLEM",
        "DISEASE": "DISEASE",
        "DIAGNOSIS": "DIAGNOSIS",

        "MEDICATION": "MEDICATION",
        "DRUG": "MEDICATION",

        "DOSAGE": "DOSAGE",
        "SPECIMEN": "SPECIMEN",
        "CLINICAL_SECTION": "CLINICAL_SECTION",

        "SYMPTOM": "SYMPTOM",

        "PROCEDURE": "PROCEDURE",

        "LAB_RESULT": "LAB_RESULT",
        "LAB": "LAB",

        "TEST": "LAB_TEST",

        "ALLERGY": "ALLERGY",

        "VITAL_SIGN": "VITAL_SIGN",

        "BODY_PART": "BODY_PART",
        "CLINICAL FINDING": "CLINICAL_FINDING",
        "CLINICAL_FINDINGS": "CLINICAL_FINDING",

        # ==========================
        # DOCUMENT
        # ==========================
        "INVOICE NUMBER": "INVOICE_NUMBER",
        "INVOICE_ID": "INVOICE_NUMBER",

        "GSTIN": "GSTIN",

        "DOCUMENT ID": "DOCUMENT_ID",
        "REPORT ID": "REPORT_ID",
        "REPORT_ID": "REPORT_ID",
        "ACCESS CODE": "ACCESS_CODE",
        "TRACKING NUMBER": "TRACKING_NUMBER",

        "REFERENCE NUMBER": "REFERENCE_NUMBER",

        # ==========================
        # VEHICLE
        # ==========================
        "VEHICLE NUMBER": "VEHICLE_NUMBER",
        "LICENSE PLATE": "VEHICLE_NUMBER",

        # ==========================
        # BIOMETRIC
        # ==========================
        "FINGERPRINT": "FINGERPRINT",
        "FACE": "FACE",
        "RETINA": "RETINA",

        # ==========================
        # OTHER
        # ==========================
        "USERNAME": "USERNAME",
        "PASSWORD": "PASSWORD",
        "API_KEY": "API_KEY",
        "TOKEN": "TOKEN",
    }

    @classmethod
    def normalize(
        cls,
        detections: list[DetectionResult],
        document_type: str | None = None,
    ) -> list[DetectionResult]:

        for detection in detections:
            detection.entity_type = cls.ENTITY_MAPPING.get(
                detection.entity_type.upper(),
                detection.entity_type.upper(),
            )
            # Attach policy priority (MUST_HAVE / NICE_TO_HAVE / DROP)
            priority = TaxonomyService.get_priority(detection.entity_type, document_type)
            detection.metadata["policy_priority"] = priority
            detection.metadata["should_mask"] = TaxonomyService.should_mask(detection.entity_type, document_type)

        # Automatically assign privacy categories (PII/PHI) using Centralized PrivacyMapper
        PrivacyMapper.assign_categories(detections)

        return detections


class PrivacyMapper:
    """
    Centralized Privacy Category Mapper.
    Maps standardized entity types to privacy classifications (PII/PHI).
    """

    MAPPING = {
        # ==========================
        # PII
        # ==========================
        "EMAIL": "PII",
        "EMAIL_ADDRESS": "PII",
        "PHONE": "PII",
        "PHONE_NUMBER": "PII",
        "US_PHONE_NUMBER": "PII",
        "PERSON": "PII",
        "ADDRESS": "PII",
        "LOCATION": "PII",
        "CITY": "PII",
        "STATE": "PII",
        "COUNTRY": "PII",
        "DATE": "PII",
        "DATE_TIME": "PII",
        "DATE_RANGE": "PII",
        "DATE_OF_BIRTH": "PII",
        "TIME": "PII",
        "AGE": "PII",
        "AADHAAR": "PII",
        "AADHAAR_NUMBER": "PII",
        "PAN": "PII",
        "PAN_NUMBER": "PII",
        "PASSPORT": "PII",
        "PASSPORT_NUMBER": "PII",
        "SSN": "PII",
        "DRIVING_LICENSE": "PII",
        "DRIVING_LICENSE_NUMBER": "PII",
        "VOTER_ID": "PII",
        "BANK_ACCOUNT": "PII",
        "BANK_ACCOUNT_NUMBER": "PII",
        "IFSC": "PII",
        "IFSC_CODE": "PII",
        "UPI": "PII",
        "UPI_ID": "PII",
        "CREDIT_CARD": "PII",
        "CREDIT_CARD_NUMBER": "PII",
        "DEBIT_CARD": "PII",
        "DEBIT_CARD_NUMBER": "PII",
        "IP_ADDRESS": "PII",
        "URL": "PII",
        "PIN_CODE": "PII",
        "ZIP_CODE": "PII",
        "DEVICE_ID": "PII",
        "EMPLOYEE_ID": "PII",
        "DOCUMENT_ID": "PII",
        "REPORT_ID": "PII",
        "ACCESS_CODE": "PII",
        "TRACKING_NUMBER": "PII",
        "REFERENCE_NUMBER": "PII",
        "GSTIN": "PII",
        "INVOICE_NUMBER": "PII",
        "START_DATE": "PII",
        "SALARY": "PII",
        "FINANCIAL_AMOUNT": "PII",
        "AMOUNT": "PII",
        "COST_SHARING_AMOUNT": "PII",
        "PREMIUM_AMOUNT": "PII",
        "CUSTOMER_SERVICE_NUMBER": "PII",
        "ORGANIZATION_CONTACT_INFO": "PII",
        "DOCUMENT_CREATION_DATE": "PII",
        "DATE_OF_SERVICE": "PHI",
        "COVERAGE_DATE": "PHI",
        "DUE_DATE": "PII",

        # ==========================
        # PHI
        # ==========================
        "PATIENT": "PHI",
        "PROVIDER": "PHI",
        "DOCTOR": "PHI",
        "PHYSICIAN": "PHI",
        "NURSE": "PHI",
        "HOSPITAL": "PHI",
        "MEDICAL_FACILITY": "PHI",
        "HEALTHCARE_ORGANIZATION": "PHI",
        "INSURANCE_PROVIDER": "PHI",
        "DISEASE": "PHI",
        "PROBLEM": "PHI",
        "MEDICAL_CONDITION": "PHI",
        "DIAGNOSIS": "PHI",
        "SYMPTOM": "PHI",
        "MEDICATION": "PHI",
        "DRUG": "PHI",
        "DOSAGE": "PHI",
        "SPECIMEN": "PHI",
        "CLINICAL_SECTION": "PHI",
        "PROCEDURE": "PHI",
        "LAB": "PHI",
        "LAB_RESULT": "PHI",
        "LAB_TEST": "PHI",
        "VITAL_SIGN": "PHI",
        "CLINICAL_FINDING": "PHI",
        "CLINICAL FINDING": "PHI",
        "MEDICAL_RECORD_NUMBER": "PHI",
        "MRN": "PHI",
        "INSURANCE_ID": "PHI",
        "POLICY_NUMBER": "PHI",
        "CLAIM_NUMBER": "PHI",
        "PATIENT_ID": "PHI",
        "VISIT_DATE": "PHI",
        "CPT_CODE": "PHI",
        "ICD10_CODE": "PHI",
        "NPI_NUMBER": "PHI",
        "MEMBER_ID": "PHI",
        "GROUP_NUMBER": "PHI",
        "TAX_ID": "PII",
        "EOB_NUMBER": "PHI",
        "CLINICAL_MEASUREMENT": "PHI",
        "OTHER_PHI": "PHI",
    }

    @classmethod
    def get_category(cls, entity_type: str) -> str:
        """
        Returns the privacy category (PII, PHI, or OTHER) for a standardized entity type.
        """
        return cls.MAPPING.get(entity_type.upper(), "PII")

    @classmethod
    def assign_categories(
        cls,
        detections: list[DetectionResult],
    ) -> list[DetectionResult]:
        """
        Assigns the correct privacy category to each DetectionResult.
        """
        for detection in detections:
            detection.privacy_category = cls.get_category(detection.entity_type)
        return detections
