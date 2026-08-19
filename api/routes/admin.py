from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

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


class UserStats(BaseModel):
    total_users: int
    total_documents: int
    total_reports: int
    total_entities: int
    total_redactions: int
    pending_reviews: int
    users_by_role: dict


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
    total_users = db.query(User).count()
    total_documents = db.query(Document).count()
    total_reports = db.query(Report).count()
    total_entities = db.query(Entity).count()
    total_redactions = db.query(Redaction).count()
    pending_reviews = (
        db.query(Review)
        .filter(Review.review_status == "PENDING")
        .count()
    )

    users_by_role = {}
    for user in db.query(User).all():
        role = user.role or "USER"
        users_by_role[role] = users_by_role.get(role, 0) + 1

    return UserStats(
        total_users=total_users,
        total_documents=total_documents,
        total_reports=total_reports,
        total_entities=total_entities,
        total_redactions=total_redactions,
        pending_reviews=pending_reviews,
        users_by_role=users_by_role,
    )