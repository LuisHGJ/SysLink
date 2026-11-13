"""Testes do Escavador — escavação de leads via IA."""
import asyncio
import json

import pytest


# ─── Config ──────────────────────────────────────────────────────
class TestExcavatorConfig:
    def test_config_has_openrouter_key_field(self):
        """Settings deve ter openrouter_api_key."""
        from app.config import settings

        assert hasattr(settings, "openrouter_api_key")
        assert hasattr(settings, "ai_model")

    def test_config_ai_model_default(self):
        """Modelo padrão deve ser nemotron."""
        from app.config import settings

        assert "nemotron" in settings.ai_model

    def test_apify_client_is_importable(self):
        """Regressão: apify-shared 2.x removeu `ignore_docs` e o import
        de apify_client quebrava → TODO /excavate voltava 502."""
        from apify_client import ApifyClient

        assert ApifyClient is not None


# ─── Busca de leads ──────────────────────────────────────────────
class TestExcavate:
    def test_excavate_requires_niche(self, client):
        """POST sem nicho → 422."""
        res = client.post("/api/v1/excavate", json={})
        assert res.status_code == 422

    def test_excavate_empty_niche(self, client):
        """POST com nicho vazio → 422."""
        res = client.post("/api/v1/excavate", json={"nicho": ""})
        assert res.status_code == 422

    def test_excavate_with_valid_niche(self, client, monkeypatch):
        """POST com nicho válido → retorna resultados."""
        from app.services.excavator_service import ExcavatorService

        # Mock: evita chamada real à API
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
                },
                {
                    "instagram": "@teste2",
                    "nome": "Teste Dois",
                    "empresa": "Empresa B",
                    "contato": "teste2@email.com",
                    "produto": "Sistema",
                    "dificuldade": "Fácil",
                    "confianca": 0.85,
                },
            ]

        monkeypatch.setattr(ExcavatorService, "excavate", mock_excavate)
        res = client.post(
            "/api/v1/excavate", json={"nicho": "restaurantes", "quantidade": 5}
        )
        assert res.status_code == 200
        body = res.json()
        assert "resultados" in body
        assert len(body["resultados"]) == 2

    def test_excavate_missing_apify_token(self, client, monkeypatch):
        """Sem APIFY_API_TOKEN → 502 com mensagem clara."""
        from app.config import settings
        from app.services.excavator_service import ExcavatorService

        monkeypatch.setattr(settings, "apify_api_token", "")
        res = client.post(
            "/api/v1/excavate", json={"nicho": "test", "quantidade": 5}
        )
        assert res.status_code == 502
        assert "APIFY" in res.json()["detail"]

    def test_excavate_upstream_error_is_sanitized(self, client, monkeypatch):
        """Erro cru do Apify NÃO pode vazar no detail da resposta.

        O detail só pode conter a mensagem segura; o texto original
        (token, URL, stack) fica no log do servidor.
        """
        from app.config import settings
        from app.services.excavator_service import ExcavatorService

        # Com token presente a fonte entra na corrida (sem ele o serviço
        # nem chama a Apify e responderia "não configurada").
        monkeypatch.setattr(settings, "apify_api_token", "apify-test")

        def fake_apify_search(self, niche, count):
            raise ValueError("boom token=SEGREDO url=https://api.apify.com")

        monkeypatch.setattr(ExcavatorService, "_apify_search", fake_apify_search)
        res = client.post(
            "/api/v1/excavate", json={"nicho": "test", "quantidade": 1}
        )
        assert res.status_code == 502
        assert res.headers["content-type"] == "application/problem+json"
        detail = res.json()["detail"]
        assert isinstance(detail, str)
        assert "SEGREDO" not in detail
        assert "token=" not in detail
        assert "api.apify.com" not in detail
        assert "Apify" in detail  # mensagem amigável em PT-BR

    def test_excavate_timeout_returns_504(self, client, monkeypatch):
        """Busca que estoura o tempo limite → 504 (não trava o servidor)."""
        from app.routes import excavator as excavator_route
        from app.services.excavator_service import ExcavatorService

        async def slow_excavate(self, niche, count=30):
            await asyncio.sleep(1)
            return []

        monkeypatch.setattr(ExcavatorService, "excavate", slow_excavate)
        monkeypatch.setattr(excavator_route, "EXCAVATE_TIMEOUT_SECONDS", 0.05)
        res = client.post(
            "/api/v1/excavate", json={"nicho": "test", "quantidade": 1}
        )
        assert res.status_code == 504
        assert res.headers["content-type"] == "application/problem+json"
        assert "demorou" in res.json()["detail"]

    def test_excavate_result_shape(self, client, monkeypatch):
        """Cada resultado deve ter campos suficientes para a tabela de leads."""
        from app.services.excavator_service import ExcavatorService

        async def mock_excavate(self, niche, count=30):
            return [
                {
                    "instagram": "@teste",
                    "nome": "Teste",
                    "empresa": "Empresa X",
                    "contato": None,
                    "produto": "Portfólio",
                    "dificuldade": "Médio",
                    "confianca": 0.9,
                    "seguidores": 1200,
                    "bio": "Artista digital",
                    "categoria": "Artist",
                    "verificado": False,
                    "negocio": True,
                    "url": "https://instagram.com/teste",
                }
            ]

        monkeypatch.setattr(ExcavatorService, "excavate", mock_excavate)
        res = client.post(
            "/api/v1/excavate", json={"nicho": "test", "quantidade": 1}
        )
        result = res.json()["resultados"][0]
        for field in [
            "instagram",
            "nome",
            "empresa",
            "contato",
            "produto",
            "dificuldade",
            "confianca",
            "seguidores",
            "bio",
            "categoria",
            "verificado",
            "negocio",
            "url",
        ]:
            assert field in result, f"Campo '{field}' ausente"


# ─── Classificação IA (chunks paralelos) ────────────────────────
def _fake_profiles(n: int) -> list[dict]:
    return [
        {
            "username": f"user{i}",
            "fullName": f"User {i}",
            "biography": f"bio {i}",
            "followersCount": 100 + i,
            "isBusinessAccount": True,
            "businessCategoryName": "Restaurante",
        }
        for i in range(n)
    ]


class TestAiClassifyChunks:
    async def test_splits_into_chunks_and_merges_by_global_index(self, monkeypatch):
        """40 perfis → 3 chunks (15/15/10) classificados em paralelo,
        merge de volta alinhado ao índice original."""
        from app.services.excavator_service import CLASSIFY_CHUNK_SIZE, ExcavatorService

        seen_sizes: list[int] = []

        async def fake_chunk(self, niche, summaries):
            seen_sizes.append(len(summaries))
            await asyncio.sleep(0.01)  # força sobreposição real
            return [
                {
                    "index": s["index"],  # index global, direto do summary
                    "produto": "Sistema",
                    "dificuldade": "Fácil",
                    "confianca": 0.9,
                }
                for s in summaries
            ]

        monkeypatch.setattr(ExcavatorService, "_classify_chunk", fake_chunk)

        profiles = _fake_profiles(40)
        result = await ExcavatorService()._ai_classify("restaurantes", profiles)

        assert len(result) == 40
        assert all(r is not None for r in result), "índice perdido no merge"
        assert result[39]["produto"] == "Sistema"
        assert len(seen_sizes) == -(-40 // CLASSIFY_CHUNK_SIZE), "nº de chunks"
        assert sum(seen_sizes) == 40
        assert max(seen_sizes) <= CLASSIFY_CHUNK_SIZE

    async def test_chunk_failure_keeps_other_chunks(self, monkeypatch):
        """Falha num chunk não derruba a classificação dos demais."""
        from app.services.excavator_service import (
            CLASSIFY_CHUNK_SIZE,
            ExcavatorService,
        )

        async def flaky_chunk(self, niche, summaries):
            if summaries[0]["index"] >= CLASSIFY_CHUNK_SIZE:
                raise RuntimeError("OpenRouter 500: boom")
            return [
                {"index": s["index"], "produto": "Sistema", "dificuldade": "Fácil", "confianca": 0.8}
                for s in summaries
            ]

        monkeypatch.setattr(ExcavatorService, "_classify_chunk", flaky_chunk)

        result = await ExcavatorService()._ai_classify("x", _fake_profiles(40))

        assert all(
            result[i] is not None for i in range(CLASSIFY_CHUNK_SIZE)
        ), "chunk saudável perdeu dados"
        assert all(
            result[i] is None for i in range(CLASSIFY_CHUNK_SIZE, 40)
        ), "chunk com falha deve ficar None"

    async def test_profiles_over_cap_stay_unclassified(self, monkeypatch):
        """Só os CLASSIFY_MAX_PROFILES primeiros perfis são classificados."""
        from app.services.excavator_service import (
            CLASSIFY_MAX_PROFILES,
            ExcavatorService,
        )

        called: list[int] = []

        async def fake_chunk(self, niche, summaries):
            called.append(len(summaries))
            return [{"index": s["index"], "produto": "Sistema", "dificuldade": "Fácil", "confianca": 0.5} for s in summaries]

        monkeypatch.setattr(ExcavatorService, "_classify_chunk", fake_chunk)

        total = CLASSIFY_MAX_PROFILES + 10
        result = await ExcavatorService()._ai_classify("x", _fake_profiles(total))

        assert sum(called) == CLASSIFY_MAX_PROFILES, "teto de perfis classificados"
        assert all(result[i] is not None for i in range(CLASSIFY_MAX_PROFILES))
        assert all(result[i] is None for i in range(CLASSIFY_MAX_PROFILES, total))


# ─── HTTP client compartilhado ──────────────────────────────────
class TestSharedHttpClient:
    async def test_client_is_reused_across_calls(self):
        """get_http_client() deve devolver a MESMA instância (keep-alive)."""
        from app.services.excavator_service import get_http_client

        a = get_http_client()
        b = get_http_client()
        try:
            assert a is b
        finally:
            from app.services.excavator_service import close_http_client

            await close_http_client()

    async def test_close_then_get_creates_new_client(self):
        """Após close_http_client(), a próxima chamada cria um client novo."""
        from app.services.excavator_service import (
            close_http_client,
            get_http_client,
        )

        a = get_http_client()
        await close_http_client()
        b = get_http_client()
        try:
            assert b is not a
            assert not b.is_closed
        finally:
            await close_http_client()

    async def test_close_is_idempotent(self):
        """Fechar duas vezes (ou sem nunca ter criado) não pode explodir."""
        from app.services.excavator_service import close_http_client

        await close_http_client()
        await close_http_client()


# ─── Embeddings (Nemotron) ──────────────────────────────────────
class TestEmbedding:
    def test_embed_route_exists(self, client):
        """POST /api/v1/embed deve existir."""
        res = client.post("/api/v1/embed", json={"text": "teste"})
        # Pode falhar por API key ausente, mas rota deve existir (não 404)
        assert res.status_code != 404

    def test_embed_requires_text(self, client):
        """POST /api/v1/embed sem texto → 422."""
        res = client.post("/api/v1/embed", json={})
        assert res.status_code == 422


# ─── Tavily (busca de perfis do Instagram em paralelo à Apify) ──
class TestTavilyConfig:
    def test_config_has_tavily_key_field(self):
        """Settings deve ter tavily_api_key (vazia = busca só com Apify)."""
        from app.config import settings

        assert hasattr(settings, "tavily_api_key")
        assert isinstance(settings.tavily_api_key, str)


def _tavily_item(
    url: str,
    title: str = "Nome (@user) • Instagram photos and videos",
    content: str = "",
) -> dict:
    return {"url": url, "title": title, "content": content}


class TestTavilyParsing:
    """Resultado do Tavily → mesmo formato de perfil da Apify."""

    def test_profile_url_becomes_lead(self):
        from app.services.excavator_service import ExcavatorService

        profile = ExcavatorService._parse_tavily_result(
            _tavily_item(
                url="https://www.instagram.com/pizzaria.central/?hl=pt-br",
                title=(
                    "Pizzaria Central (@pizzaria.central) • "
                    "Instagram photos and videos"
                ),
                content=(
                    "1,512 Followers, 10 Following, 89 Posts - See Instagram "
                    "photos and videos from Pizzaria Central "
                    "(@pizzaria.central) Massa artesanal"
                ),
            )
        )

        assert profile is not None
        assert profile["username"] == "pizzaria.central"
        assert profile["fullName"] == "Pizzaria Central"
        assert profile["followersCount"] == 1512
        assert profile["url"] == "https://www.instagram.com/pizzaria.central/"
        # Meta description sai da bio (sobra o texto real).
        assert profile["biography"] == "Massa artesanal"

    def test_non_profile_urls_are_ignored(self):
        from app.services.excavator_service import ExcavatorService

        for url in [
            "https://www.instagram.com/p/ABC123/",
            "https://www.instagram.com/reel/XYZ9/",
            "https://www.instagram.com/explore/tags/pizzaria/",
            "https://www.instagram.com/pizzaria/explore/",
            "https://example.com/pizzaria/",  # fora do domínio
            "https://pizzaria.com/",
            "",
        ]:
            assert (
                ExcavatorService._parse_tavily_result(_tavily_item(url)) is None
            ), f"não era para aceitar {url!r}"

    def test_missing_name_falls_back_to_username(self):
        from app.services.excavator_service import ExcavatorService

        profile = ExcavatorService._parse_tavily_result(
            _tavily_item(
                url="https://www.instagram.com/sol.nature/",
                title="(@sol.nature) • Instagram photos and videos",
                content="",
            )
        )

        assert profile["fullName"] == ""  # excavate() usa o username
        assert profile["biography"] == ""
        assert profile["followersCount"] == 0

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("1.5K", 1500),
            ("1,5K", 1500),
            ("1,512", 1512),
            ("12.500", 12500),
            ("2M", 2_000_000),
            ("987", 987),
            ("", 0),
            ("abc", 0),
        ],
    )
    def test_parse_count(self, raw, expected):
        from app.services.excavator_service import ExcavatorService

        assert ExcavatorService._parse_count(raw) == expected


class TestTavilyRequest:
    async def test_search_is_restricted_to_instagram(self, monkeypatch):
        """POST /search só no instagram.com, com teto de 20 e chave no header."""
        from app.config import settings
        from app.services import excavator_service as module
        from app.services.excavator_service import ExcavatorService

        monkeypatch.setattr(settings, "tavily_api_key", "tvly-test")
        captured: dict = {}

        class FakeResponse:
            status_code = 200
            text = "{}"

            def json(self):
                return {"results": []}

        class FakeClient:
            async def post(self, url, **kwargs):
                captured["url"] = url
                captured.update(kwargs)
                return FakeResponse()

        monkeypatch.setattr(module, "get_http_client", lambda: FakeClient())

        result = await ExcavatorService()._tavily_search("restaurantes", 50)

        assert result == []
        assert captured["url"] == "https://api.tavily.com/search"
        assert captured["headers"]["Authorization"] == "Bearer tvly-test"
        body = captured["json"]
        assert "restaurantes" in body["query"]
        assert body["include_domains"] == ["instagram.com"]
        assert body["include_domains_mode"] == "restrict"
        assert body["max_results"] == 20  # teto da API

    async def test_without_key_raises_safe_error(self, monkeypatch):
        from app.config import settings
        from app.exceptions import ExternalServiceError
        from app.services.excavator_service import ExcavatorService

        monkeypatch.setattr(settings, "tavily_api_key", "")

        with pytest.raises(ExternalServiceError) as exc:
            await ExcavatorService()._tavily_search("x", 5)

        assert "TAVILY_API_KEY" in str(exc.value)

    async def test_http_error_raises_runtime_error(self, monkeypatch):
        """Status ≠ 200 vira RuntimeError (a rota devolve 502, sem vazar corpo)."""
        from app.config import settings
        from app.services import excavator_service as module
        from app.services.excavator_service import ExcavatorService

        monkeypatch.setattr(settings, "tavily_api_key", "tvly-test")

        class FakeResponse:
            status_code = 401
            text = '{"detail": {"error": "Unauthorized: bad key"}}'

            def json(self):
                return {}

        class FakeClient:
            async def post(self, url, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(module, "get_http_client", lambda: FakeClient())

        with pytest.raises(RuntimeError) as exc:
            await ExcavatorService()._tavily_search("x", 5)

        assert "401" in str(exc.value)


# ─── Execução paralela Apify + Tavily ────────────────────────────
def _lead_profile(username: str) -> dict:
    """Perfil no formato devolvido pelas fontes de busca."""
    return {
        "username": username,
        "fullName": username.title(),
        "biography": "bio real",
        "followersCount": 321,
        "isBusinessAccount": True,
        "businessCategoryName": "Restaurante",
        "url": f"https://www.instagram.com/{username}/",
    }


def _mock_sources(
    monkeypatch,
    apify_profiles: list[dict] | None = None,
    tavily_profiles: list[dict] | None = None,
    apify_exc: BaseException | None = None,
    tavily_exc: BaseException | None = None,
) -> None:
    """Configura as duas fontes com resultados (ou falha) fake."""
    from app.config import settings
    from app.services.excavator_service import ExcavatorService

    monkeypatch.setattr(settings, "apify_api_token", "apify-test")
    monkeypatch.setattr(settings, "tavily_api_key", "tvly-test")

    def fake_apify(self, niche, count):
        if apify_exc is not None:
            raise apify_exc
        return list(apify_profiles or [])

    async def fake_tavily(self, niche, count):
        if tavily_exc is not None:
            raise tavily_exc
        return list(tavily_profiles or [])

    monkeypatch.setattr(ExcavatorService, "_apify_search", fake_apify)
    monkeypatch.setattr(ExcavatorService, "_tavily_search", fake_tavily)


class TestExcavateParallelSources:
    def test_merges_dedupes_and_limits(self, client, monkeypatch):
        """As duas fontes entram na resposta, sem duplicar @username."""
        _mock_sources(
            monkeypatch,
            apify_profiles=[
                _lead_profile("apify1"),
                _lead_profile("apify2"),
                _lead_profile("duplicado"),
            ],
            tavily_profiles=[
                _lead_profile("tavily1"),
                _lead_profile("duplicado"),
                _lead_profile("tavily2"),
            ],
        )

        res = client.post(
            "/api/v1/excavate", json={"nicho": "pizzaria", "quantidade": 5}
        )

        assert res.status_code == 200
        handles = [r["instagram"] for r in res.json()["resultados"]]
        # Round-robin: as fontes se alternam e o duplicado aparece uma vez.
        assert handles == [
            "@apify1",
            "@tavily1",
            "@apify2",
            "@duplicado",
            "@tavily2",
        ]

    def test_limit_is_respected(self, client, monkeypatch):
        """quantidade é o teto da resposta mesmo com as duas fontes cheias."""
        _mock_sources(
            monkeypatch,
            apify_profiles=[_lead_profile(f"a{i}") for i in range(10)],
            tavily_profiles=[_lead_profile(f"t{i}") for i in range(10)],
        )

        res = client.post(
            "/api/v1/excavate", json={"nicho": "pizzaria", "quantidade": 3}
        )

        assert res.status_code == 200
        assert len(res.json()["resultados"]) == 3

    def test_apify_failure_keeps_tavily(self, client, monkeypatch):
        """Apify caiu → 200 com os resultados do Tavily (sem 502)."""
        _mock_sources(
            monkeypatch,
            apify_exc=ValueError("boom token=SEGREDO"),
            tavily_profiles=[_lead_profile("tavily1")],
        )

        res = client.post(
            "/api/v1/excavate", json={"nicho": "pizzaria", "quantidade": 5}
        )

        assert res.status_code == 200
        assert [r["instagram"] for r in res.json()["resultados"]] == ["@tavily1"]

    def test_tavily_failure_keeps_apify(self, client, monkeypatch):
        """Tavily caiu → 200 com os resultados da Apify."""
        _mock_sources(
            monkeypatch,
            apify_profiles=[_lead_profile("apify1")],
            tavily_exc=ValueError("boom 401 chave=SEGREDO"),
        )

        res = client.post(
            "/api/v1/excavate", json={"nicho": "pizzaria", "quantidade": 5}
        )

        assert res.status_code == 200
        assert [r["instagram"] for r in res.json()["resultados"]] == ["@apify1"]

    def test_both_sources_failing_returns_safe_502(self, client, monkeypatch):
        """Sem nenhuma fonte → 502 e nenhum detalhe cru vaza para o cliente."""
        _mock_sources(
            monkeypatch,
            apify_exc=ValueError("boom url=https://api.apify.com SEGREDO"),
            tavily_exc=ValueError("boom 401 chave=SEGREDO"),
        )

        res = client.post(
            "/api/v1/excavate", json={"nicho": "pizzaria", "quantidade": 5}
        )

        assert res.status_code == 502
        assert res.headers["content-type"] == "application/problem+json"
        detail = res.json()["detail"]
        assert "Apify" in detail and "Tavily" in detail
        assert "SEGREDO" not in detail
        assert "api.apify.com" not in detail

    def test_tavily_only_when_apify_token_missing(self, client, monkeypatch):
        """Sem APIFY_API_TOKEN o Escavador continua no Tavily (não quebra)."""
        from app.config import settings
        from app.services.excavator_service import ExcavatorService

        monkeypatch.setattr(settings, "apify_api_token", "")
        monkeypatch.setattr(settings, "tavily_api_key", "tvly-test")

        def apify_must_not_run(self, niche, count):
            raise AssertionError("Apify não deve ser chamada sem token")

        async def fake_tavily(self, niche, count):
            return [_lead_profile("tavily1")]

        monkeypatch.setattr(ExcavatorService, "_apify_search", apify_must_not_run)
        monkeypatch.setattr(ExcavatorService, "_tavily_search", fake_tavily)

        res = client.post(
            "/api/v1/excavate", json={"nicho": "pizzaria", "quantidade": 5}
        )

        assert res.status_code == 200
        assert [r["instagram"] for r in res.json()["resultados"]] == ["@tavily1"]

    def test_no_source_configured_returns_502(self, client, monkeypatch):
        """Nenhuma chave → 502 citando as duas variáveis que faltam."""
        from app.config import settings

        monkeypatch.setattr(settings, "apify_api_token", "")
        monkeypatch.setattr(settings, "tavily_api_key", "")

        res = client.post(
            "/api/v1/excavate", json={"nicho": "pizzaria", "quantidade": 5}
        )

        assert res.status_code == 502
        detail = res.json()["detail"]
        assert "APIFY_API_TOKEN" in detail
        assert "TAVILY_API_KEY" in detail
