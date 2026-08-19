from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import joinedload

from api.dependencies import DatabaseSession, require_roles, require_document_access
from api.schemas.review import (
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewEntityResponse,
    ReviewResponse,
)
from database.models import Document, Entity, Report, Review, User

router = APIRouter(tags=["Reviews"])

COMPLETED_REVIEW_STATUSES = {
    "APPROVED",
    "CONFIRMED",
    "CORRECTED",
    "REJECTED",
    "SKIPPED",
}


def _normalize_status(review_status: str) -> str:
    return review_status.strip().upper()


def _serialize_review(review: Review) -> ReviewResponse:
    entity = review.entity
    return ReviewResponse(
        review_id=review.id,
        entity_id=review.entity_id,
        document_id=entity.document_id,
        reviewer=review.reviewer,
        review_status=review.review_status,
        review_comment=review.review_comment,
        reviewed_at=review.reviewed_at,
        created_at=review.created_at,
        entity=ReviewEntityResponse(
            entity_id=entity.id,
            document_id=entity.document_id,
            ocr_result_id=entity.ocr_result_id,
            entity_type=entity.entity_type,
            entity_value=entity.entity_value,
            privacy_category=entity.privacy_category,
            confidence_score=entity.confidence_score,
            final_confidence=entity.final_confidence,
            detector=entity.detector,
            page_number=entity.page_number,
            start_char=entity.start_char,
            end_char=entity.end_char,
            is_review_required=bool(entity.is_review_required),
            is_redacted=bool(entity.is_redacted),
        ),
    )


def _update_report_review_completion(db, document_id: str) -> None:
    pending_count = (
        db.query(Review)
        .join(Entity, Review.entity_id == Entity.id)
        .filter(Entity.document_id == document_id)
        .filter(Review.review_status == "PENDING")
        .count()
    )
    reports = db.query(Report).filter(Report.document_id == document_id).all()
    for report in reports:
        report.review_completion = pending_count == 0
        db.add(report)


@router.get(
    "/documents/{document_id}/reviews",
    response_model=List[ReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="List Document Reviews",
)
def list_document_reviews(
    document_id: str,
    db: DatabaseSession = None,
    current_user: User = Depends(require_roles("REVIEWER", "ADMIN")),
) -> List[ReviewResponse]:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    require_document_access(db, current_user, document)

    reviews = (
        db.query(Review)
        .join(Entity, Review.entity_id == Entity.id)
        .options(joinedload(Review.entity))
        .filter(Entity.document_id == document_id)
        .order_by(Review.created_at.asc())
        .all()
    )
    return [_serialize_review(review) for review in reviews]


@router.patch(
    "/reviews/{review_id}",
    response_model=ReviewDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Human Review Decision",
)
def submit_review_decision(
    review_id: str,
    payload: ReviewDecisionRequest,
    db: DatabaseSession = None,
    current_user: User = Depends(require_roles("REVIEWER", "ADMIN")),
) -> ReviewDecisionResponse:
    review = (
        db.query(Review)
        .options(joinedload(Review.entity))
        .filter(Review.id == review_id)
        .first()
    )
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review not found: {review_id}",
        )

    entity = review.entity
    review_status = _normalize_status(payload.review_status)

    review.reviewer = current_user.name
    review.review_status = review_status
    review.review_comment = payload.review_comment
    review.reviewed_at = datetime.now(timezone.utc)

    if payload.entity_type is not None:
        entity.entity_type = payload.entity_type.strip().upper()
        entity.canonical_type = entity.entity_type
    if payload.entity_value is not None:
        entity.entity_value = payload.entity_value
    if payload.privacy_category is not None:
        entity.privacy_category = payload.privacy_category.strip().upper()
    if payload.final_confidence is not None:
        entity.final_confidence = payload.final_confidence
        entity.confidence_score = payload.final_confidence
    if payload.is_redacted is not None:
        entity.is_redacted = payload.is_redacted

    entity.is_review_required = review_status not in COMPLETED_REVIEW_STATUSES

    db.add(entity)
    db.add(review)
    db.flush()
    _update_report_review_completion(db, entity.document_id)
    db.commit()
    db.refresh(review)
    db.refresh(entity)

    return ReviewDecisionResponse(**_serialize_review(review).model_dump())

