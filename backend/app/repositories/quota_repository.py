"""Repository da cota diária — acesso a dados via SQLAlchemy.

A reserva é um UPDATE condicional (`profiles_used + n <= limite`): a
comparação acontece DENTRO do SQL, então duas requisições simultâneas
não conseguem ultrapassar o teto do dia.
"""
from datetime import date

from sqlalchemy import case, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.quota_model import DailyQuota


class QuotaRepository:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def _get(self, day: date) -> DailyQuota | None:
        return (
            self.db.query(DailyQuota)
            .filter(DailyQuota.user_id == self.user_id, DailyQuota.day == day)
            .first()
        )

    def _get_or_create(self, day: date) -> DailyQuota:
        row = self._get(day)
        if row is not None:
            return row
        row = DailyQuota(user_id=self.user_id, day=day, profiles_used=0)
        self.db.add(row)
        try:
            self.db.commit()
        except IntegrityError:
            # Duas requisições criando a linha do dia ao mesmo tempo:
            # uma vence, a outra reusa a linha já criada.
            self.db.rollback()
            row = self._get(day)
            if row is None:  # pragma: no cover — outra causa de IntegrityError
                raise
        return row

    def used_on(self, day: date) -> int:
        """Perfis já escavados pelo usuário naquele dia (0 se não há linha)."""
        row = self._get(day)
        return row.profiles_used if row else 0

    def reserve(self, day: date, count: int, limit: int) -> int:
        """Reserva `count` perfis devolvendo o efetivamente reservado.

        O `WHERE` condicional garante que `profiles_used` nunca passe do
        `limit`: se couber menos que `count`, nada é reservado (0).
        """
        if count <= 0:
            return 0
        row = self._get_or_create(day)
        result = self.db.execute(
            update(DailyQuota)
            .where(
                DailyQuota.id == row.id,
                DailyQuota.profiles_used + count <= limit,
            )
            .values(profiles_used=DailyQuota.profiles_used + count)
        )
        self.db.commit()
        return count if result.rowcount else 0

    def release(self, day: date, count: int) -> None:
        """Devolve perfis da cota (busca falhou ou achou menos que o pedido)."""
        if count <= 0:
            return
        row = self._get(day)
        if row is None:
            return
        remaining = case(
            (DailyQuota.profiles_used - count < 0, 0),
            else_=DailyQuota.profiles_used - count,
        )
        self.db.execute(
            update(DailyQuota)
            .where(DailyQuota.id == row.id)
            .values(profiles_used=remaining)
        )
        self.db.commit()
