from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from redis import Redis
from sqlalchemy.orm import Session

from core.database import get_db, get_redis
from core.security import hash_token
from database.models import AuthSession, User
from database.repositories.user_repository import UserRepository


DatabaseSession = Annotated[Session, Depends(get_db)]

RedisClient = Annotated[Redis, Depends(get_redis)]


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: DatabaseSession = None,
) -> User:
    """
    Resolve the authenticated user from a ``Bearer`` token.

    Raises:
        HTTPException: 401 if the header is missing/malformed, the token is
            unknown, the session expired, or the user is deactivated.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = UserRepository(db)
    session = repo.get_session_by_token_hash(hash_token(token.strip()))
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if session.expires_at is not None:
        now = datetime.now(timezone.utc)
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            repo.delete_session(session)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    user = db.query(User).filter(User.id == session.user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is deactivated or no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    """
    Return a dependency that enforces the current user has one of ``roles``.

    The role check runs after ``get_current_user`` so the request must be
    authenticated first.
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return role_checker


def is_document_accessible(
    db: Session,
    user: User,
    document,
) -> bool:
    """
    Return whether ``user`` may access ``document`` under the RBAC rules.

    - ADMIN / REVIEWER: full access to any document.
    - USER: only documents they own (via ``owner_id``), falling back to the
      legacy ``uploaded_by`` email for documents created before ownership
      tracking existed.
    """
    if user.role in {"ADMIN", "REVIEWER"}:
        return True

    is_owner = (
        document.owner_id is not None
        and document.owner_id == user.id
    )
    legacy_owner = (
        document.owner_id is None
        and document.uploaded_by is not None
        and document.uploaded_by.strip().lower() == user.email.strip().lower()
    )

    return is_owner or legacy_owner


def require_document_access(
    db: Session,
    user: User,
    document,
):
    """
    Enforce RBAC on a single document.

    - ADMIN / REVIEWER: full access to any document.
    - USER: only documents they own (via ``owner_id``), falling back to the
      legacy ``uploaded_by`` email for documents created before ownership
      tracking existed.

    Returns the document (with the caller's access granted) or raises 403.
    """
    if is_document_accessible(db, user, document):
        return document

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this document.",
    )