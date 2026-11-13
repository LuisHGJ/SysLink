"""Testes da cota diária de perfis escavados (por usuário).

Regra: no máximo `excavate_daily_profile_limit` (50) perfis entregues por
usuário por dia BRT. A reserva é feita ANTES da busca; falha devolve a
reserva e entrega menor que o pedido devolve a diferença.
"""
from datetime import date, datetime, timedelta

from app.services.quota_service import BRT
from tests.test_excavator import _lead_profile, _mock_sources

LIMIT = 50


def _today() -> date:
    return datetime.now(BRT).date()


def _yesterday() -> date:
    return (datetime.now(BRT) - timedelta(days=1)).date()


def _excavate(client, quantidade: int = 10, nicho: str = "pizzaria"):
    return client.post(
        "/api/v1/excavate", json={"nicho": nicho, "quantidade": quantidade}
    )


def _quota(client) -> dict:
    res = client.get("/api/v1/excavate/quota")
    assert res.status_code == 200, res.text
    return res.json()


def _mock_full_sources(monkeypatch, failing: bool = False):
    """Fontes que devolvem exatamente `count` perfis (ou falham as duas)."""
    if failing:
        _mock_sources(
            monkeypatch,
            apify_exc=ValueError("boom SEGREDO"),
            tavily_exc=ValueError("boom SEGREDO"),
        )
        return

    from app.config import settings
    from app.services.excavator_service import ExcavatorService

    monkeypatch.setattr(settings, "apify_api_token", "apify-test")
    monkeypatch.setattr(settings, "tavily_api_key", "tvly-test")

    def fake_apify(self, niche, count):
        return [_lead_profile(f"a{i}") for i in range(count)]

    async def fake_tavily(self, niche, count):
        return []  # só a Apify entrega; o merge devolve `count` perfis

    monkeypatch.setattr(ExcavatorService, "_apify_search", fake_apify)
    monkeypatch.setattr(ExcavatorService, "_tavily_search", fake_tavily)


def _seed_used(db_session, used: int, day=None, user_id: int | None = None) -> None:
    """Grava `used` perfis já usados no dia para o usuário padrão."""
    from app.models.quota_model import DailyQuota
    from app.models.user_model import User

    if user_id is None:
        user_id = db_session.query(User).one().id
    db_session.add(
        DailyQuota(
            user_id=user_id,
            day=day or _today(),
            profiles_used=used,
        )
    )
    db_session.commit()


# ─── Endpoint de consulta ────────────────────────────────────────
class TestQuotaEndpoint:
    def test_starts_empty_with_full_limit(self, client):
        body = _quota(client)
        assert body["ativa"] is True
        assert body["limite"] == LIMIT
        assert body["usado"] == 0
        assert body["restante"] == LIMIT
        # Próxima virada: meia-noite BRT (offset fixo -03:00).
        assert body["renova_em"].endswith("T00:00:00-03:00")

    def test_requires_authentication(self, unauth_client):
        res = unauth_client.get("/api/v1/excavate/quota")
        assert res.status_code == 401


# ─── Consumo ─────────────────────────────────────────────────────
class TestQuotaConsumption:
    def test_counts_delivered_profiles_in_response(self, client, monkeypatch):
        """A resposta carrega a cota atualizada (o UI não precisa refetch)."""
        _mock_sources(
            monkeypatch,
            apify_profiles=[_lead_profile(f"a{i}") for i in range(7)],
        )

        res = _excavate(client, quantidade=10)

        assert res.status_code == 200
        body = res.json()
        assert len(body["resultados"]) == 7
        assert body["cota"]["usado"] == 7
        assert body["cota"]["restante"] == 43

    def test_only_delivered_profiles_are_charged(self, client, monkeypatch):
        """Pediu 30, achou 7 → cobra 7 (o resto volta para a cota)."""
        _mock_sources(
            monkeypatch,
            apify_profiles=[_lead_profile(f"a{i}") for i in range(7)],
        )
        _excavate(client, quantidade=30)

        assert _quota(client)["usado"] == 7

    def test_caps_request_to_what_remains(self, client, monkeypatch):
        """Restam 20 → pedir 50 devolve 20 e zera a cota do dia."""
        _mock_full_sources(monkeypatch)

        first = _excavate(client, quantidade=30)
        assert first.status_code == 200
        assert first.json()["cota"]["usado"] == 30

        second = _excavate(client, quantidade=50)
        assert second.status_code == 200
        assert len(second.json()["resultados"]) == 20
        assert second.json()["cota"]["usado"] == LIMIT
        assert second.json()["cota"]["restante"] == 0

    def test_exhausted_returns_429_with_retry_after(self, client, monkeypatch):
        _mock_full_sources(monkeypatch)
        assert _excavate(client, quantidade=50).status_code == 200

        res = _excavate(client, quantidade=10)

        assert res.status_code == 429
        assert res.headers["content-type"] == "application/problem+json"
        assert int(res.headers["retry-after"]) > 0
        detail = res.json()["detail"].lower()
        assert "cota diária de 50 perfis escavados" in detail
        assert "renova" in detail

    def test_failed_search_returns_the_reservation(self, client, monkeypatch):
        """502/504 não pode comer cota do usuário."""
        _mock_full_sources(monkeypatch, failing=True)

        res = _excavate(client, quantidade=30)

        assert res.status_code == 502
        assert _quota(client)["usado"] == 0

    def test_timeout_returns_the_reservation(self, client, monkeypatch):
        """Igual ao 502, mas pelo caminho do 504 (wait_for)."""
        import asyncio

        from app.routes import excavator as excavator_route
        from app.services.excavator_service import ExcavatorService

        async def slow_excavate(self, niche, count=30):
            await asyncio.sleep(1)
            return []

        monkeypatch.setattr(ExcavatorService, "excavate", slow_excavate)
        monkeypatch.setattr(excavator_route, "EXCAVATE_TIMEOUT_SECONDS", 0.05)

        res = _excavate(client, quantidade=30)

        assert res.status_code == 504
        assert _quota(client)["usado"] == 0


# ─── Isolamento e janela ─────────────────────────────────────────
class TestQuotaIsolationAndWindow:
    def test_quota_is_per_user(self, client, make_user, monkeypatch):
        """Usuário A esgotado não bloqueia o usuário B."""
        _mock_full_sources(monkeypatch)
        assert _excavate(client, quantidade=50).status_code == 200
        assert _excavate(client, quantidade=10).status_code == 429

        other = make_user("outra-pessoa@syslink.com")
        res = client.post(
            "/api/v1/excavate",
            json={"nicho": "pizzaria", "quantidade": 10},
            headers=other,
        )

        assert res.status_code == 200
        assert res.json()["cota"]["usado"] == 10

    def test_full_quota_today_blocks(self, client, db_session):
        _seed_used(db_session, LIMIT)

        res = _excavate(client, quantidade=10)

        assert res.status_code == 429
        assert _quota(client)["restante"] == 0

    def test_resets_on_a_new_day(self, client, db_session, monkeypatch):
        """Linha cheia de ONTEM não bloqueia HOJE."""
        _mock_full_sources(monkeypatch)
        _seed_used(db_session, LIMIT, day=_yesterday())

        res = _excavate(client, quantidade=10)

        assert res.status_code == 200
        body = res.json()
        assert body["cota"]["usado"] == 10
        assert body["cota"]["restante"] == LIMIT - 10

    def test_zero_limit_disables_quota(self, client, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "excavate_daily_profile_limit", 0)
        _mock_full_sources(monkeypatch)

        for _ in range(3):
            res = _excavate(client, quantidade=50)
            assert res.status_code == 200
            assert res.json()["cota"]["ativa"] is False


# ─── Unidade: service + repository ───────────────────────────────
class TestQuotaServiceAndRepository:
    def test_reset_window_is_next_midnight_brt(self, db_session):
        from app.models.user_model import User
        from app.repositories.quota_repository import QuotaRepository
        from app.services.quota_service import QuotaService

        user_id = db_session.query(User).one().id
        service = QuotaService(QuotaRepository(db_session, user_id))

        assert 1 <= service.seconds_until_reset() <= 86400
        assert service.reset_at().endswith("T00:00:00-03:00")

    def test_repository_reserve_is_capped_and_releasable(self, db_session):
        from app.models.user_model import User
        from app.repositories.quota_repository import QuotaRepository

        user_id = db_session.query(User).one().id
        repo = QuotaRepository(db_session, user_id)
        day = _today()

        assert repo.reserve(day, 40, LIMIT) == 40
        # Só cabiam 10 e a reserva é atômica: não coube, não reservou.
        assert repo.reserve(day, 40, LIMIT) == 0
        assert repo.reserve(day, 10, LIMIT) == 10
        assert repo.used_on(day) == LIMIT

        repo.release(day, 15)
        assert repo.used_on(day) == LIMIT - 15
        # Nunca fica negativo (devolução exagerada).
        repo.release(day, 999)
        assert repo.used_on(day) == 0
