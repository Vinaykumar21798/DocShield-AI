from modules.detection.service import DetectionService

sample_text = """
Invoice no: 12847181
Date of issue:	03/03/2012

Seller:	Client:
Fitzpatrick and Sons	Duncan PLC
00480 Cook Cove	Unit 8799 Box 0703
Spencerport, UT 12036	DPO AP 81970
Tax Id: 998-99-5253	Tax Id: 911-82-7132
IBAN: GB92PBPQ73499358975916
ITEMS

No. Description	Qty UM	Net price Net worth VAT [%]	Gross
worth
1. HP Desktop Computer PC	4,00 each	139,95	559,80	10%	615,78
Core i5 16GB 2TB HD 256GB
SSD 22" LCD Windows 10
2. CUSTOM BUILT AMD RYZEN	3,00 each	1 400,00 4 200,00	10% 4 620,00
THREADRIPPER GAMING
COMPUTER,32 GB RAM,
3. Fast Dell Optiplex Desktop PC	1,00 each	217,00	217,00	10%	238,70
Computer Dual Core 3.4Ghz
8GB 1TB Win 10 Pro WIFI
4. Dell Optiplex 790 Computer i7	3,00 each	159,99	479,97	10%	527,97
@ 3.40 Ghz Quad Core 250GB
4GB Working
5. Vintage Microsolutions Pentium	2,00 each	390,00	780,00	10%	858,00
133mhz Desktop Tower PC
Windows 95 5.25 Floppy

SUMMARY

VAT [%]	Net worth	VAT	Gross worth
10%	6 236,77	623,68	6 860,45
Total	$ 6 236,77 $ 623,68	$ 6 860,45

"""
import datetime
import uuid
from database.base import Base
from database.session import engine, SessionLocal

from database.models.entity import Entity
from database.models.confidence import ConfidenceScore
from database.models.redaction import Redaction
from database.models.report import Report
from database.models.review import Review

from database.repositories.entity_repository import EntityRepository
from database.repositories.confidence_repository import ConfidenceRepository
from database.repositories.redaction_repository import RedactionRepository
from database.repositories.report_repository import ReportRepository
from database.repositories.review_repository import ReviewRepository

# 1. Initialize database tables (drop and recreate to ensure latest schema is applied)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

service = DetectionService()

# 2. Run detection pipeline
results = service.detect(sample_text)

# 3. Store records in database tables (entities, confidence_scores, reviews, redactions, reports)
doc_id = str(uuid.uuid4())
with SessionLocal() as db:
    entity_repo = EntityRepository(db)
    confidence_repo = ConfidenceRepository(db)
    redaction_repo = RedactionRepository(db)
    report_repo = ReportRepository(db)
    review_repo = ReviewRepository(db)

    saved_entities = []

    for item in results:
        # Save entity details
        db_entity = Entity(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            ocr_result_id="ocr-poc-001",
            entity_type=item.entity_type,
            entity_value=item.entity_value,
            page_number=str(item.page_number),
            confidence_score=item.confidence_score,
            detector=item.detector,
            start_char=item.start,
            end_char=item.end,
            privacy_category=item.privacy_category,
            entity_owner=item.detector,
            canonical_type=item.entity_type,
            processing_stage="DETECTION",
            is_review_required=(item.confidence_score < 0.8),
            is_redacted=True,
            final_confidence=item.confidence_score
        )
        entity_repo.create(db_entity)
        saved_entities.append(db_entity)

        # Save confidence details
        db_score = ConfidenceScore(
            id=str(uuid.uuid4()),
            entity_id=db_entity.id,
            confidence_score=item.confidence_score,
            confidence_level="HIGH" if item.confidence_score >= 0.8 else "LOW",
            threshold=0.8
        )
        confidence_repo.create(db_score)

        # Save review log if confidence level is low
        if item.confidence_score < 0.8:
            db_review = Review(
                id=str(uuid.uuid4()),
                entity_id=db_entity.id,
                reviewer="SystemAutoReviewer",
                review_status="PENDING",
                review_comment="Flagged for manual review due to low confidence score.",
                reviewed_at=datetime.datetime.now(datetime.timezone.utc)
            )
            review_repo.create(db_review)

    # Save redaction log record
    db_redaction = Redaction(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        redaction_type="PII_PHI_REDACTION",
        redacted_file_path=f"/redacted/docs/{doc_id}_redacted.txt",
        redaction_summary=f"Redacted {len(results)} sensitive entities.",
        processed_by="SystemPipeline"
    )
    redaction_repo.create(db_redaction)

    # Save report log record
    total_pii = sum(1 for item in results if item.privacy_category == "PII")
    total_phi = sum(1 for item in results if item.privacy_category == "PHI")
    db_report = Report(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        report_type="AUDIT",
        total_entities=len(results),
        total_redactions=len(results),
        report_path=f"/reports/{doc_id}_audit_report.json",
        generated_by="SystemPipeline",
        processing_duration_ms=180,
        detectors_used=",".join(list(set(item.detector for item in results))),
        gemma_invoked=False,
        total_pii=total_pii,
        total_phi=total_phi,
        review_completion=True,
        redaction_completion=True
    )
    report_repo.create(db_report)

print(f"[SUCCESS] Saved {len(results)} entities to database under Document ID: {doc_id}")

print("\n========== MEDSPACY ROUTING TEST ==========\n")

for entity in results:
    print(
        f"{entity.detector:12} | "
        f"{entity.entity_type:25} | "
        f"{entity.privacy_category:10} | "
        f"{entity.confidence_score:<6.2f} | "
        f"{entity.entity_value}"
    )

print(f"\nTotal Entities : {len(results)}")
