"""Testes de rate limit — auth por IP + cota por usuário (TDD).

Escrito ANTES da implementação. Escopo acordado:
- 5 req/min por IP nos endpoints PÚBLICOS de auth (anti brute force);
- 100 req/min por user_id nas rotas autenticadas (leads/escavador);
- 429 problem+json PT-BR com header Retry-After; 0 = desativado.
"""
import pytest

from app.config import settings

# Login com conta inexistente → 401 rápido (sem bcrypt), mas CONTA
# para o limite: o balde é por tentativa, não por falha.
LOGIN_GHOST = {"email": "nao-existe@syslink.com", "password": "senha12345"}

VALID_LEAD = {
    "nome": "João Silva",
    "empresa": "Acme Corp",
    "contato": "joao@acme.com",
    "instagram": "@joaosilva",
    "produto": "Portfólio",
    "dificuldade": "Médio",
    "status": "Não contatado",
    "motivo_perda": None,
    "ultimo_contato": None,
    "arquivos": [],
}


# ─── Config ──────────────────────────────────────────────────────
class TestRateLimitConfig:
    def test_default_values(self):
        """Defaults das settings (model_fields — imune ao patch da suíte)."""
        from app.config import Settings

        assert Settings.model_fields["rate_limit_auth_per_minute"].default == 5
        assert Settings.model_fields["rate_limit_user_per_minute"].default == 100
        assert Settings.model_fields["trust_proxy_headers"].default is False


# ─── Unitário: janela deslizante ─────────────────────────────────
class FakeClock:
    def __init__(self):
        self.now = 1_000.0

    def __call__(self):
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestRateLimiterStore:
    def _make(self):
        from app.dependencies.rate_limit import RateLimiter

        clock = FakeClock()
        return RateLimiter(clock=clock), clock

    def test_allows_up_to_limit_then_denies(self):
        limiter, _ = self._make()
        assert [limiter.hit("k", 3) for _ in range(4)] == [
            True,
            True,
            True,
            False,
        ]

    def test_keys_are_independent(self):
        limiter, _ = self._make()
        for _ in range(3):
            limiter.hit("a", 3)
        assert limiter.hit("a", 3) is False
        assert limiter.hit("b", 3) is True

    def test_denied_attempts_do_not_extend_window(self):
        """Janela deslizante: tentativas negadas não empurram a liberação."""
        limiter, clock = self._make()
        for _ in range(3):
            limiter.hit("k", 3)
        assert limiter.hit("k", 3) is False
        clock.advance(59)
        assert limiter.hit("k", 3) is False  # ainda dentro dos 60s
        clock.advance(2)  # total 61s > janela
        assert limiter.hit("k", 3) is True

    def test_retry_after_counts_down(self):
        limiter, clock = self._make()
        for _ in range(3):
            limiter.hit("k", 3)
        assert limiter.hit("k", 3) is False
        assert limiter.retry_after("k") == 60
        clock.advance(40)
        assert limiter.retry_after("k") == 20

    def test_zero_or_negative_limit_disables(self):
        limiter, _ = self._make()
        assert all(limiter.hit("k", 0) for _ in range(10))
        assert limiter.hit("k", -1) is True


# ─── Auth por IP ─────────────────────────────────────────────────
class TestAuthRateLimitByIP:
    def test_login_is_throttled_after_limit(self, unauth_client, monkeypatch):
        """5 tentativas passam (mesmo errando); a 6ª → 429."""
        monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 5)
        for _ in range(5):
            res = unauth_client.post("/api/v1/auth/login", json=LOGIN_GHOST)
            assert res.status_code == 401
        res = unauth_client.post("/api/v1/auth/login", json=LOGIN_GHOST)
        assert res.status_code == 429

    def test_throttled_response_is_problem_json(self, unauth_client, monkeypatch):
        monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 1)
        unauth_client.post("/api/v1/auth/login", json=LOGIN_GHOST)
        res = unauth_client.post("/api/v1/auth/login", json=LOGIN_GHOST)
        assert res.status_code == 429
        assert res.headers["content-type"] == "application/problem+json"
        body = res.json()
        assert body["status"] == 429
        assert isinstance(body["detail"], str)
        assert "tentativas" in body["detail"].lower()
        assert int(res.headers["Retry-After"]) >= 1

    @pytest.mark.parametrize(
        "path,payload",
        [
            (
                "/api/v1/auth/register",
                {"email": "novo@syslink.com", "password": "senha12345"},
            ),
            ("/api/v1/auth/confirm", {"token": "token-invalido"}),
            ("/api/v1/auth/forgot", {"email": "novo@syslink.com"}),
            ("/api/v1/auth/resend-confirmation", {"email": "novo@syslink.com"}),
            (
                "/api/v1/auth/reset",
                {"token": "token-invalido", "password": "senha12345"},
            ),
        ],
    )
    def test_all_public_auth_endpoints_are_throttled(
        self, unauth_client, monkeypatch, path, payload
    ):
        """Todos os endpoints PÚBLICOS de auth têm limite por IP (login já coberto)."""
        monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 2)
        unauth_client.post(path, json=payload)
        unauth_client.post(path, json=payload)
        assert unauth_client.post(path, json=payload).status_code == 429

    def test_me_is_not_ip_throttled(self, client, monkeypatch):
        """/me exige token — fora da cota por IP da auth (é rota autenticada)."""
        monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 2)
        for _ in range(5):
            assert client.get("/api/v1/auth/me").status_code == 200

    def test_zero_limit_disables_auth_throttle(self, unauth_client, monkeypatch):
        """RATE_LIMIT=0 desliga o limite (escape hatch de config)."""
        monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 0)
        for _ in range(10):
            res = unauth_client.post("/api/v1/auth/login", json=LOGIN_GHOST)
            assert res.status_code == 401

    def test_forwarded_ips_have_separate_buckets(
        self, unauth_client, monkeypatch
    ):
        """Com TRUST_PROXY_HEADERS, cada X-Forwarded-For tem balde próprio."""
        monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 1)
        monkeypatch.setattr(settings, "trust_proxy_headers", True)
        ip1 = {"X-Forwarded-For": "10.0.0.1"}
        ip2 = {"X-Forwarded-For": "10.0.0.2"}
        first = unauth_client.post(
            "/api/v1/auth/login", json=LOGIN_GHOST, headers=ip1
        )
        assert first.status_code == 401
        second = unauth_client.post(
            "/api/v1/auth/login", json=LOGIN_GHOST, headers=ip1
        )
        assert second.status_code == 429
        # outro IP não é afetado pelo balde do primeiro
        other = unauth_client.post(
            "/api/v1/auth/login", json=LOGIN_GHOST, headers=ip2
        )
        assert other.status_code == 401

    def test_forwarded_header_ignored_when_proxy_not_trusted(
        self, unauth_client, monkeypatch
    ):
        """Sem proxy confiável, X-Forwarded-For é IGNORADO (não spoofável)."""
        monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 1)
        # trust_proxy_headers permanece False (default)
        ip1 = {"X-Forwarded-For": "10.0.0.1"}
        ip2 = {"X-Forwarded-For": "10.0.0.2"}
        first = unauth_client.post(
            "/api/v1/auth/login", json=LOGIN_GHOST, headers=ip1
        )
        assert first.status_code == 401
        # segundo request "muda de IP" mas cai no mesmo balde (host real)
        second = unauth_client.post(
            "/api/v1/auth/login", json=LOGIN_GHOST, headers=ip2
        )
        assert second.status_code == 429


# ─── Cota por usuário ────────────────────────────────────────────
class TestPerUserQuota:
    def test_leads_throttled_over_quota(self, client, monkeypatch):
        """GET /leads passa 3x; a 4ª → 429 problem+json."""
        monkeypatch.setattr(settings, "rate_limit_user_per_minute", 3)
        for _ in range(3):
            assert client.get("/api/v1/leads").status_code == 200
        res = client.get("/api/v1/leads")
        assert res.status_code == 429
        assert res.headers["content-type"] == "application/problem+json"
        assert int(res.headers["Retry-After"]) >= 1

    def test_quota_is_per_user(self, client, make_user, monkeypatch):
        """Usuário no limite NÃO afeta os demais (balde por user_id)."""
        monkeypatch.setattr(settings, "rate_limit_user_per_minute", 2)
        client.get("/api/v1/leads")
        client.get("/api/v1/leads")
        assert client.get("/api/v1/leads").status_code == 429
        headers_b = make_user("outra@syslink.com")
        assert client.get("/api/v1/leads", headers=headers_b).status_code == 200

    def test_write_endpoints_respect_quota(self, client, monkeypatch):
        """POST /leads também passa pela cota (dependência no router)."""
        monkeypatch.setattr(settings, "rate_limit_user_per_minute", 1)
        first = client.post("/api/v1/leads", json=VALID_LEAD)
        assert first.status_code in (200, 201)
        second = client.post("/api/v1/leads", json=VALID_LEAD)
        assert second.status_code == 429

    def test_excavator_respects_quota(self, client, monkeypatch):
        """POST /excavate também é limitado (consome Apify/IA)."""
        from app.services.excavator_service import ExcavatorService

        async def mock_excavate(self, niche, count=30):
            return [
                {
                    "instagram": "@teste1",
                    "nome": "Teste Um",
                    "empresa": "Empresa A",
                    "contato": "teste1@email.com",
                    "produto": "Portfólio",
                    "dificuldade": "Médio",
                    "confianca": 0.9,
                }
            ]

        monkeypatch.setattr(ExcavatorService, "excavate", mock_excavate)
        monkeypatch.setattr(settings, "rate_limit_user_per_minute", 1)
        first = client.post(
            "/api/v1/excavate", json={"nicho": "restaurantes", "quantidade": 1}
        )
        assert first.status_code == 200
        second = client.post(
            "/api/v1/excavate", json={"nicho": "restaurantes", "quantidade": 1}
        )
        assert second.status_code == 429
