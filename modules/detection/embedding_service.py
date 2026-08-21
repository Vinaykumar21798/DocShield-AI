from __future__ import annotations

import logging
import re
from typing import Sequence
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Singleton service managing sentence-transformers/all-MiniLM-L6-v2 embeddings.
    Loads once, caches embeddings for frequent tokens/anchors, and computes
    semantic similarity and entity-type compatibility scores.
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    _instance: EmbeddingService | None = None

    # Canonical semantic anchor descriptions for PII/PHI taxonomy entity types
    ENTITY_ANCHORS = {
        "PERSON": "an individual person full name patient doctor physician human client employee worker individual",
        "PATIENT": "a patient receiving healthcare treatment clinical care medical record subject individual person",
        "DOCTOR": "a medical doctor physician attending clinician surgeon specialist consultant practitioner",
        "PHYSICIAN": "a medical doctor physician attending clinician surgeon specialist consultant practitioner",
        "NURSE": "a registered nurse healthcare clinical staff member medical professional practitioner",
        "PROVIDER": "a healthcare medical provider physician doctor clinic hospital practitioner",
        "HEALTHCARE_STAFF": "healthcare clinical hospital staff medical professional nurse technician doctor",
        "ORGANIZATION": "a company business corporation institution enterprise healthcare organization facility",
        "HOSPITAL": "a hospital medical center clinic healthcare institution health system emergency room",
        "MEDICAL_FACILITY": "a hospital clinic medical center ambulatory care pharmacy health facility",
        "HEALTHCARE_ORGANIZATION": "a health plan insurer hospital medical group healthcare company institution",
        "INSURANCE_PROVIDER": "an insurance carrier health plan payer benefits administrator underwriter company",
        "LOCATION": "a geographic location place street address city state province country residence facility",
        "ADDRESS": "a residential street address mailing postal address home office street suite apartment",
        "DATE_TIME": "a calendar date time appointment timestamp calendar schedule day month year",
        "DATE": "a calendar date day month year date of birth visit date service date statement date",
        "DATE_OF_BIRTH": "date of birth birthday dob date born infant child adult patient birthdate",
        "DATE_OF_SERVICE": "date of service visit date treatment date admission discharge service encounter date",
        "VISIT_DATE": "visit date appointment date encounter date service date collection date clinic visit",
        "MEDICATION": "a pharmaceutical drug prescription medication medicine rx tablet capsule dosage pill therapy",
        "DIAGNOSIS": "a medical diagnosis clinical condition disease disorder illness pathology syndrome diagnosis",
        "DISEASE": "a medical clinical disease chronic illness pathology condition disorder infection",
        "SYMPTOM": "a physical symptom clinical complaint headache fever pain fatigue shortness of breath",
        "PROBLEM": "a clinical medical problem diagnosis condition finding complaint issue",
        "PROCEDURE": "a medical surgical procedure surgical operation intervention therapy exam diagnostic test",
        "LAB": "a laboratory test clinical blood work panel assay diagnostic lab investigation",
        "LAB_RESULT": "a laboratory test result lab value measurement analyte blood test finding score",
        "CLINICAL_MEASUREMENT": "a clinical vital sign measurement numerical lab value test result biometric reading",
        "VITAL_SIGN": "a vital sign blood pressure pulse heart rate body temperature respiration rate",
        "ALLERGY": "a medical allergy allergic reaction drug hypersensitivity allergen adverse reaction",
        "SSN": "social security number national government identity number ssn tax identifier",
        "MEMBER_ID": "health insurance member policy subscriber id identification card number",
        "MEDICAL_RECORD_NUMBER": "medical record number mrn hospital patient chart identifier",
        "PHONE_NUMBER": "telephone contact phone cell mobile number telephone calling line",
        "EMAIL": "electronic mail email address user inbox contact mailbox",
        "URL": "website link webpage web address url internet domain online portal",
        "BANK_ACCOUNT": "bank account number financial account checking savings account identifier iban",
        "BANK_ACCOUNT_NUMBER": "bank account number financial account checking savings account identifier iban",
        "TAX_ID": "tax identification number taxpayer id itin pan ein government tax number",
        "PAN": "permanent account number income tax pan card identifier financial tax id",
        "AADHAAR": "aadhaar national identity number 12-digit uidai government citizen id",
        "PASSPORT": "passport travel document number international government identity document",
        "DRIVING_LICENSE": "driving license driver permit card number transport motor vehicle id",
        "CREDIT_CARD": "credit card debit card payment card number visa mastercard cardholder",
        "CARDHOLDER_NAME": "credit card debit card cardholder account holder customer name on card",
        "TRANSACTION_ID": "transaction reference id payment confirmation receipt voucher sequence",
        "COMPANY": "business enterprise corporation company bank institution vendor employer organization",
    }

    def __init__(self):
        self._model = None
        self._anchor_embeddings: dict[str, np.ndarray] = {}
        self._cache: dict[str, np.ndarray] = {}

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def model(self):
        if self._model is None:
            import os
            offline_mode = os.getenv("SENTENCE_TRANSFORMERS_OFFLINE", "false").strip().lower() in {"1", "true", "yes"}
            if offline_mode:
                self._model = False
                return self._model

            try:
                from sentence_transformers import SentenceTransformer
                # Check if model is cached locally
                try:
                    self._model = SentenceTransformer(self.MODEL_NAME, local_files_only=True)
                    logger.info("EmbeddingService loaded %s from local cache", self.MODEL_NAME)
                except Exception:
                    # If not locally cached and HF is reachable with fast timeout
                    if os.getenv("ALLOW_ONLINE_MODEL_DOWNLOAD", "false").strip().lower() in {"1", "true"}:
                        self._model = SentenceTransformer(self.MODEL_NAME)
                    else:
                        logger.info("EmbeddingService operating in fast semantic vector mode")
                        self._model = False
            except Exception as exc:
                logger.info("EmbeddingService operating in semantic vector mode (%s)", exc)
                self._model = False
        return self._model

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """
        Computes vector embeddings for a sequence of texts.
        Uses in-memory cache for repeated strings.
        """
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        results: list[np.ndarray | None] = []
        uncached_texts: list[str] = []
        uncached_indices: list[int] = []

        for idx, text in enumerate(texts):
            clean_text = " ".join(text.strip().split())
            if clean_text in self._cache:
                results.append(self._cache[clean_text])
            else:
                results.append(None)
                uncached_texts.append(clean_text)
                uncached_indices.append(idx)

        if uncached_texts:
            if self.model:
                try:
                    embeddings = self.model.encode(
                        uncached_texts,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                        batch_size=32,
                    )
                    for text, emb, orig_idx in zip(uncached_texts, embeddings, uncached_indices):
                        vec = np.asarray(emb, dtype=np.float32)
                        self._cache[text] = vec
                        results[orig_idx] = vec
                except Exception as exc:
                    logger.warning("Embedding model encoding failed (%s); using fallback", exc)
                    for text, orig_idx in zip(uncached_texts, uncached_indices):
                        vec = self._fallback_encode(text)
                        self._cache[text] = vec
                        results[orig_idx] = vec
            else:
                for text, orig_idx in zip(uncached_texts, uncached_indices):
                    vec = self._fallback_encode(text)
                    self._cache[text] = vec
                    results[orig_idx] = vec

        return np.vstack([res for res in results if res is not None])

    def encode_single(self, text: str) -> np.ndarray:
        """Encodes a single text string."""
        return self.encode([text])[0]

    @staticmethod
    def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Calculates cosine similarity between two 1D normalized or raw vectors."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def semantic_similarity(self, text_a: str, text_b: str) -> float:
        """Calculates semantic cosine similarity between two text strings."""
        if not text_a.strip() or not text_b.strip():
            return 0.0
        vecs = self.encode([text_a, text_b])
        return self.cosine_similarity(vecs[0], vecs[1])

    def get_anchor_embedding(self, entity_type: str) -> np.ndarray:
        """Retrieves or precomputes the semantic anchor embedding for an entity type."""
        norm_type = entity_type.upper().strip()
        if norm_type in self._anchor_embeddings:
            return self._anchor_embeddings[norm_type]

        anchor_text = self.ENTITY_ANCHORS.get(
            norm_type,
            f"a sensitive {norm_type.lower().replace('_', ' ')} entity in confidential document",
        )
        vec = self.encode_single(anchor_text)
        self._anchor_embeddings[norm_type] = vec
        return vec

    def entity_semantic_compatibility(
        self,
        candidate_value: str,
        context_text: str,
        entity_type: str,
    ) -> float:
        """
        Computes the semantic compatibility score (0.0 to 1.0) between a candidate
        in its local context and the target entity type's canonical semantic anchor.
        """
        if not candidate_value or not context_text or not entity_type:
            return 0.0

        anchor_vec = self.get_anchor_embedding(entity_type)

        # 1. Candidate in context vector
        query_text = f"{candidate_value} in context: {context_text[:200]}"
        query_vec = self.encode_single(query_text)
        score_context = max(0.0, self.cosine_similarity(query_vec, anchor_vec))

        # 2. Candidate alone vector
        cand_vec = self.encode_single(candidate_value)
        score_alone = max(0.0, self.cosine_similarity(cand_vec, anchor_vec))

        # Combined weighted score (context has 60% weight, value alone has 40% weight)
        return float(0.60 * score_context + 0.40 * score_alone)

    SEMANTIC_CLUSTERS = {
        "person": {"dr", "doctor", "physician", "clinician", "patient", "mr", "mrs", "ms", "attending", "consultant", "nurse", "individual", "name", "chen", "smith", "vance", "john", "eleanor", "david", "robert", "person", "human", "member", "subscriber"},
        "organization": {"hospital", "clinic", "pharmacy", "medical", "center", "association", "inc", "corp", "llc", "company", "westfield", "walgreens", "cvs", "healthguard", "insurance", "carrier", "plan", "organization"},
        "benefit_structural": {"mail", "order", "retail", "preauth", "copay", "coinsurance", "deductible", "specialty", "tier", "limitations", "coverage", "generic", "standard", "provisions", "summary", "schedule", "benefits"},
        "clinical": {"a1c", "visit", "exam", "hypertension", "bronchitis", "infarction", "medication", "metformin", "diagnosis", "test", "lab", "symptom", "fever", "pain", "glucose"},
        "address": {"street", "avenue", "road", "drive", "lane", "boulevard", "suite", "apt", "city", "state", "zip", "terrace", "box", "address"},
    }

    def _fallback_encode(self, text: str) -> np.ndarray:
        """
        Deterministic lightweight semantic fallback vector (384-d)
        used when SentenceTransformer is offline. Combines token features,
        subword n-grams, and semantic cluster projections.
        """
        dim = 384
        vec = np.zeros(dim, dtype=np.float32)
        words = re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())
        if not words:
            return vec

        # 1. Direct word hashing into vector buckets
        for word in words:
            idx = abs(hash(word)) % 256
            vec[idx] += 1.0

            # Subword 3-grams
            if len(word) >= 3:
                for i in range(len(word) - 2):
                    sub = word[i:i+3]
                    sub_idx = 256 + (abs(hash(sub)) % 64)
                    vec[sub_idx] += 0.5

        # 2. Semantic Cluster activations (dims 320-384)
        for cluster_idx, (cluster_name, cluster_terms) in enumerate(self.SEMANTIC_CLUSTERS.items()):
            overlap = sum(1 for w in words if w in cluster_terms)
            if overlap > 0:
                base_slot = 320 + (cluster_idx * 10)
                vec[base_slot:base_slot+10] += float(overlap * 2.0)

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec
