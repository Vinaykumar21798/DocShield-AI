from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from core.config import settings
from core.security import hash_token
from database.models import AuthSession, User
from database.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.email == email.strip().lower())
            .first()
        )

    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: str,
    ) -> User:
        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def list_users(self) -> list[User]:
        return (
            self.db.query(User)
            .order_by(User.created_at.asc())
            .all()
        )

    def create_session(self, user_id: str, raw_token: str) -> AuthSession:
        ttl_hours = settings.auth_token_ttl_hours
        session = AuthSession(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
        )
        self.db.add(session)
        self.db.flush()
        return session

    def get_session_by_token_hash(self, token_hash: str) -> Optional[AuthSession]:
        return (
            self.db.query(AuthSession)
            .filter(AuthSession.token_hash == token_hash)
            .first()
        )

    def delete_session(self, session: AuthSession) -> None:
        self.db.delete(session)
        self.db.flush()

    def purge_expired_sessions(self, user_id: str) -> None:
        now = datetime.now(timezone.utc)
        expired = (
            self.db.query(AuthSession)
            .filter(
                AuthSession.user_id == user_id,
                AuthSession.expires_at < now,
            )
            .all()
        )
        for session in expired:
            self.db.delete(session)