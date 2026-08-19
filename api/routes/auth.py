from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status

from api.dependencies import CurrentUser, DatabaseSession
from api.schemas.auth import (
    AuthResponse,
    LoginRequest,
    SignupRequest,
    UserResponse,
)
from core.security import (
    generate_session_token,
    hash_password,
    hash_token,
    verify_password,
)
from database.repositories.user_repository import UserRepository

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sign Up",
    description="Create a new user account and start an authenticated session.",
)
def signup(
    payload: SignupRequest,
    db: DatabaseSession = None,
) -> AuthResponse:
    repo = UserRepository(db)

    if repo.get_by_email(payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = repo.create_user(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )

    raw_token = generate_session_token()
    repo.create_session(user.id, raw_token)
    db.commit()
    db.refresh(user)

    return AuthResponse(
        access_token=raw_token,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Authenticate with email and password.",
)
def login(
    payload: LoginRequest,
    db: DatabaseSession = None,
) -> AuthResponse:
    repo = UserRepository(db)
    user = repo.get_by_email(payload.email)

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    repo.purge_expired_sessions(user.id)
    raw_token = generate_session_token()
    repo.create_session(user.id, raw_token)
    db.commit()
    db.refresh(user)

    return AuthResponse(
        access_token=raw_token,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Invalidate the current session token.",
)
def logout(
    authorization: Optional[str] = Header(default=None),
    current_user: CurrentUser = None,
    db: DatabaseSession = None,
) -> None:
    repo = UserRepository(db)
    if authorization:
        scheme, _, raw_token = authorization.partition(" ")
        if scheme.lower() == "bearer" and raw_token.strip():
            session = repo.get_session_by_token_hash(hash_token(raw_token.strip()))
            if session is not None:
                repo.delete_session(session)
                db.commit()


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Current User",
    description="Return the authenticated user's profile.",
)
def get_me(
    current_user: CurrentUser = None,
) -> UserResponse:
    return UserResponse.model_validate(current_user)