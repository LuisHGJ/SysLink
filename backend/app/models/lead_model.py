"""Model SQLAlchemy para leads."""
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Dono do lead — todo acesso é filtrado por ele (isolamento multi-usuário).
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    empresa: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contato: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instagram: Mapped[str | None] = mapped_column(String(255), nullable=True)
    produto: Mapped[str] = mapped_column(String(50), nullable=False)
    dificuldade: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Não contatado")
    motivo_perda: Mapped[str | None] = mapped_column(Text, nullable=True)
    ultimo_contato: Mapped[str | None] = mapped_column(String(30), nullable=True)
    arquivos: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
