"""Model SQLAlchemy para usuários (autenticação multi-usuário)."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    """UTC sem tzinfo — compatível com SQLite (testes) e Postgres."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Tokens de uso único (aleatórios, com expiração, consumidos uma vez).
    # Guardados em claro: são secrets opacos de curta validade — hashear
    # não adiciona proteção real e impediria o lookup por valor.
    verification_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    verification_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    reset_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    reset_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
