"""Service da cota diária de perfis escavados (por usuário)."""
from datetime import date, datetime, time, timedelta, timezone

from app.config import settings
from app.repositories.quota_repository import QuotaRepository

# Fuso da virada da cota: BRT (UTC-3), sem DST no Brasil desde 2019.
# Offset fixo evita depender de tzdata no container e garante que a cota
# renove à meia-noite LOCAL do usuário, seja qual for o TZ do host.
BRT = timezone(timedelta(hours=-3))


class QuotaService:
    """Teto diário de perfis escavados por usuário (calendário BRT).

    A janela de 24 h é de calendário (00:00–24:00 BRT), não rolante:
    `excavate` reserva a cota ANTES da busca e devolve o que não foi
    entregue, então falha de serviço nenhum consome cota.
    """

    def __init__(self, repo: QuotaRepository):
        self.repo = repo

    @property
    def limit(self) -> int:
        return settings.excavate_daily_profile_limit

    @property
    def active(self) -> bool:
        """False com limite <= 0 (escape hatch, igual ao rate limit)."""
        return self.limit > 0

    @staticmethod
    def now() -> datetime:
        return datetime.now(BRT)

    def today(self) -> date:
        return self.now().date()

    def used(self) -> int:
        if not self.active:
            return 0
        return self.repo.used_on(self.today())

    def remaining(self) -> int:
        if not self.active:
            return 0
        return max(0, self.limit - self.used())

    def reserve(self, requested: int) -> int:
        """Reserva espaço para `requested` perfis e devolve o liberado.

        Libera no máximo o que falta no dia; 0 significa cota esgotada
        (ou corrida perdida com outra requisição) → a rota responde 429.
        """
        if not self.active:
            return requested
        granted = min(requested, self.remaining())
        if granted <= 0:
            return 0
        return self.repo.reserve(self.today(), granted, self.limit)

    def release(self, count: int) -> None:
        """Devolve à cota os perfis reservados que não foram entregues."""
        if not self.active or count <= 0:
            return
        self.repo.release(self.today(), count)

    def _next_reset(self) -> datetime:
        now = self.now()
        return datetime.combine(
            now.date() + timedelta(days=1), time.min, tzinfo=BRT
        )

    def seconds_until_reset(self) -> int:
        """Segundos até a meia-noite BRT (>= 1) — vira header Retry-After."""
        return max(1, int((self._next_reset() - self.now()).total_seconds()))

    def reset_at(self) -> str:
        """Próxima virada em ISO 8601 (a UI mostra o horário de renovação)."""
        return self._next_reset().isoformat()

    def snapshot(self) -> dict:
        """Estado da cota do usuário para a resposta da API."""
        if not self.active:
            return {
                "ativa": False,
                "limite": 0,
                "usado": 0,
                "restante": 0,
                "renova_em": None,
            }
        used = self.used()
        return {
            "ativa": True,
            "limite": self.limit,
            "usado": used,
            "restante": max(0, self.limit - used),
            "renova_em": self.reset_at(),
        }
