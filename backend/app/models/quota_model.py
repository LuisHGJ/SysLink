"""Model SQLAlchemy para a cota diária de perfis escavados.

Uma linha por usuário por dia — é ela que garante o teto diário mesmo
com o container reiniciando (a janela NÃO vive em memória).
"""
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyQuota(Base):
    __tablename__ = "daily_quotas"
    __table_args__ = (
        UniqueConstraint("user_id", "day", name="uq_daily_quotas_user_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    # Dia da janela (calendário BRT — ver QuotaService.BRT).
    day: Mapped[date] = mapped_column(Date, nullable=False)
    # Perfis já entregues/escavados nesse dia.
    profiles_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
