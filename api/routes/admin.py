from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func

from api.dependencies import DatabaseSession, require_roles
from api.schemas.auth import VALID_ROLES, UserResponse
from database.models import Document, Entity, Report, Review, Redaction, User
from database.repositories.user_repository import UserRepository

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


class RoleUpdateRequest(BaseModel):
    role: str


class ActiveUpdateRequest(BaseModel):
    is_active: bool


class RecentDocument(BaseModel):
    document_id: str
    filename: str
    owner: str
    status: str
    entity_count: int
    created_at: Optional[datetime] = None


class UserStats(BaseModel):
    total_users: int
    total_documents: int
    total_reports: int
    total_entities: int
    total_redactions: int
    pending_reviews: int
    users_by_role: dict
    completion_rate: float
    processing_overview: dict
    privacy_summary: dict
    recent_documents: list[RecentDocument]


@router.get(
    "/users",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List Users",
    description="ADMIN only. Return all registered users.",
)
def list_users(
    db: DatabaseSession = None,
    _: User = Depends(require_roles("ADMIN")),
) -> List[UserResponse]:
    repo = UserRepository(db)
    return [UserResponse.model_validate(user) for user in repo.list_users()]


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Change User Role",
    description="ADMIN only. Update a user's role.",
)
def update_user_role(
    user_id: str,
    payload: RoleUpdateRequest,
    db: DatabaseSession = None,
    _: User = Depends(require_roles("ADMIN")),
) -> UserResponse:
    normalized = payload.role.strip().upper()
    if normalized not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{payload.role}'. Must be one of: "
            f"{', '.join(sorted(VALID_ROLES))}.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {user_id}",
        )

    user.role = normalized
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch(
    "/users/{user_id}/active",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate / Deactivate User",
    description="ADMIN only. Enable or disable a user account.",
)
def update_user_active(
    user_id: str,
    payload: ActiveUpdateRequest,
    db: DatabaseSession = None,
    _: User = Depends(require_roles("ADMIN")),
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {user_id}",
        )

    user.is_active = payload.is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get(
    "/stats",
    response_model=UserStats,
    status_code=status.HTTP_200_OK,
    summary="System Statistics",
    description="ADMIN only. Aggregate counts across the system.",
)
def get_stats(
    db: DatabaseSession = None,
    _: User = Depends(require_roles("ADMIN")),
) -> UserStats:
    users = db.query(User).all()
    documents = db.query(Document).all()
    total_users = len(users)
    total_documents = len(documents)
    total_reports = db.query(Report).count()
    total_entities = db.query(Entity).count()
    total_redactions = db.query(Redaction).count()
    pending_reviews = (
        db.query(Review)
        .filter(Review.review_status == "PENDING")
        .count()
    )

    users_by_role = {}
    for user in users:
        role = user.role or "USER"
        users_by_role[role] = users_by_role.get(role, 0) + 1

    pending_document_ids = {
        document_id
        for (document_id,) in (
            db.query(Entity.document_id)
            .join(Review, Review.entity_id == Entity.id)
            .filter(Review.review_status == "PENDING")
            .distinct()
            .all()
        )
    }
    processing_overview = {
        "completed": 0,
        "pending_review": 0,
        "failed": 0,
    }
    for document in documents:
        document_status = (document.status or "").strip().upper()
        if document_status in {"FAILED", "ERROR"}:
            processing_overview["failed"] += 1
        elif (
            document.id in pending_document_ids
            or document_status not in {"COMPLETED", "DONE", "SUCCESS"}
        ):
            processing_overview["pending_review"] += 1
        else:
            processing_overview["completed"] += 1

    completion_rate = (
        round(
            processing_overview["completed"] / total_documents * 100,
            1,
        )
        if total_documents
        else 0.0
    )

    privacy_summary = {"pii": 0, "phi": 0}
    for privacy_category, count in (
        db.query(Entity.privacy_category, func.count(Entity.id))
        .group_by(Entity.privacy_category)
        .all()
    ):
        normalized = (privacy_category or "").strip().upper()
        if normalized == "PII":
            privacy_summary["pii"] = count
        elif normalized == "PHI":
            privacy_summary["phi"] = count

    recent_documents = []
    for document in (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .limit(10)
        .all()
    ):
        owner = document.owner
        owner_label = (
            owner.name
            if owner is not None
            else (document.uploaded_by or "Unknown")
        )
        recent_documents.append(
            RecentDocument(
                document_id=document.id,
                filename=document.filename,
                owner=owner_label,
                status=document.status,
                entity_count=(
                    db.query(Entity)
                    .filter(Entity.document_id == document.id)
                    .count()
                ),
                created_at=document.created_at,
            )
        )

    return UserStats(
        total_users=total_users,
        total_documents=total_documents,
        total_reports=total_reports,
        total_entities=total_entities,
        total_redactions=total_redactions,
        pending_reviews=pending_reviews,
        users_by_role=users_by_role,
        completion_rate=completion_rate,
        processing_overview=processing_overview,
        privacy_summary=privacy_summary,
        recent_documents=recent_documents,
    )
