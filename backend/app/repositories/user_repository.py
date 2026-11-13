"""Repository de usuários — acesso a dados via SQLAlchemy."""
from sqlalchemy.orm import Session

from app.models.user_model import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def find_by_verification_token(self, token: str) -> User | None:
        return (
            self.db.query(User)
            .filter(User.verification_token == token)
            .first()
        )

    def find_by_reset_token(self, token: str) -> User | None:
        return self.db.query(User).filter(User.reset_token == token).first()

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        verification_token: str,
        verification_expires_at,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            email_verified=False,
            verification_token=verification_token,
            verification_expires_at=verification_expires_at,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def save(self, user: User) -> None:
        self.db.commit()
        self.db.refresh(user)
