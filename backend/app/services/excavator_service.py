"""Service do Escavador — busca real de leads via Apify + Tavily + classificação IA."""
import asyncio
import json
import re
import traceback
from urllib.parse import urlparse

import httpx
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.exceptions import ExternalServiceError
from app.logging_config import get_logger

logger = get_logger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
TAVILY_BASE = "https://api.tavily.com"

# ── Timeouts e fatiamento da classificação ────────────────────────
EMBED_TIMEOUT_SECONDS = 30
CLASSIFY_TIMEOUT_SECONDS = 60
TAVILY_TIMEOUT_SECONDS = 30
# A API do Tavily aceita no máximo 20 resultados por chamada.
TAVILY_MAX_RESULTS = 20
# Perfis por chamada de classificação — fatiado para a resposta não
# estourar o max_tokens nem demorar uma eterna chamada única.
CLASSIFY_CHUNK_SIZE = 15
# Teto de perfis classificados por escavação (prompt é limitado a 50).
CLASSIFY_MAX_PROFILES = 50

# ── HTTP client compartilhado ─────────────────────────────────────
# Um AsyncClient por processo → keep-alive e reuso de conexão (antes um
# client novo por request, sem pool). O timeout fica por chamada porque
# embed e classificação têm prazos diferentes. Fechado no lifespan
# (app.main → close_http_client).
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Retorna o AsyncClient compartilhado (cria sob demanda)."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient()
    return _http_client


async def close_http_client() -> None:
    """Fecha o client compartilhado — chamado no shutdown do app."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
    _http_client = None

# ── Prompt de classificação (IA enriquece dados reais) ───────────
_CLASSIFY_SYSTEM_PROMPT = """\
Você é um classificador de leads para um CRM brasileiro. Receberá uma lista de \
perfis REAIS do Instagram já buscados. Para cada perfil, classifique:

1. "produto": qual serviço digital ele provavelmente precisa:
   - "Portfólio" (freelancer, artista, fotógrafo que precisa mostrar trabalhos)
   - "página de venda" (negócio que vende produto/serviço)
   - "Sistema" (empresa que precisa de ferramenta/sistema)
   - "link tree" (perfil pessoal/criador que precisa de página de links)

2. "dificuldade": facilidade de abordagem:
   - "Fácil" (perfil pequeno, engajamento pessoal, provavelmente acessível)
   - "Médio" (negócio estabelecido, mas não grande empresa)
   - "Difícil" (empresa grande, perfil verificado, muitos seguidores)

3. "confianca": de 0.0 a 1.0, quão provável é ser um bom lead para o nicho.

Responda APENAS com JSON válido, sem markdown:
{
  "classificacoes": [
    {"index": 0, "produto": "Portfólio", "dificuldade": "Fácil", "confianca": 0.9}
  ]
}
"""

# Campos extraídos do Apify
_ApifyProfile = dict  # typing simplificado


class ExcavatorService:
    """Busca perfis REAIS do Instagram (Apify + Tavily) e classifica com IA."""

    async def excavate(self, niche: str, count: int = 30) -> list[dict]:
        """
        Busca perfis reais do Instagram para o nicho (Apify + Tavily em
        paralelo, unidos e deduplicados), depois classifica com IA
        (produto, dificuldade, confiança).
        """
        # 1. Busca real nas fontes configuradas (em paralelo)
        profiles = await self._search_profiles(niche, count)

        if not profiles:
            return []

        # 2. Classifica com IA (se disponível)
        if settings.openrouter_api_key:
            try:
                classifications = await self._ai_classify(niche, profiles)
            except Exception as exc:
                logger.warning("ai_classify_failed", error=str(exc))
                classifications = [None] * len(profiles)
        else:
            classifications = [None] * len(profiles)

        # 3. Combina dados reais + classificação
        results = []
        for i, profile in enumerate(profiles):
            cls = classifications[i] if i < len(classifications) else None
            results.append(
                {
                    "instagram": f"@{profile['username']}",
                    "nome": profile.get("fullName")
                    or profile.get("username", ""),
                    "empresa": profile.get("fullName"),
                    "contato": self._extract_contact(profile),
                    "produto": (cls or {}).get("produto", "Portfólio"),
                    "dificuldade": (cls or {}).get("dificuldade", "Médio"),
                    "confianca": float((cls or {}).get("confianca", 0.5)),
                    "seguidores": profile.get("followersCount", 0),
                    "bio": profile.get("biography", ""),
                    "categoria": profile.get("businessCategoryName", ""),
                    "verificado": profile.get("verified", False),
                    "negocio": profile.get("isBusinessAccount", False),
                    "url": profile.get("url", ""),
                }
            )

        logger.info(
            "excavate_success",
            niche=niche,
            requested=count,
            returned=len(results),
        )
        return results

    # ── Busca nas fontes (Apify + Tavily em paralelo) ─────────────

    async def _search_profiles(self, niche: str, count: int) -> list[dict]:
        """Busca perfis nas fontes configuradas, em paralelo.

        A Apify (scraping) e o Tavily (busca web restrita ao
        instagram.com) rodam juntas com `asyncio.gather`; falha em UMA
        fonte não derruba a outra (só erro em TODAS vira 502). Sem
        nenhuma chave configurada → 502 com as duas variáveis citadas.
        """
        sources: list[tuple[str, object]] = []
        if settings.apify_api_token:
            # _apify_search é bloqueante (cliente síncrono) → threadpool
            # para não congelar o event loop (senão /health trava junto).
            sources.append(
                ("Apify", run_in_threadpool(self._apify_search, niche, count))
            )
        if settings.tavily_api_key:
            sources.append(("Tavily", self._tavily_search(niche, count)))

        if not sources:
            raise ExternalServiceError(
                "APIFY_API_TOKEN e TAVILY_API_KEY não configuradas no .env"
            )

        settled = await asyncio.gather(
            *(task for _, task in sources), return_exceptions=True
        )

        groups: list[list[dict]] = []
        failed: list[str] = []
        for (name, _), outcome in zip(sources, settled):
            if isinstance(outcome, asyncio.CancelledError):
                raise outcome
            if isinstance(outcome, BaseException):
                failed.append(name)
                # Erro cru (httpx/Apify) só pode ir para o log; o cliente
                # recebe mensagem genérica no final, se nada deu certo.
                logger.warning(
                    "search_source_failed",
                    source=name,
                    niche=niche,
                    error=str(outcome),
                    stack_trace="".join(
                        traceback.format_exception(
                            type(outcome), outcome, outcome.__traceback__
                        )
                    ),
                )
                continue
            groups.append(outcome)

        if not groups:
            # Nenhuma fonte respondeu → repassa a mensagem segura quando
            # a própria fonte já trouxe uma (ex.: chave ausente).
            safe = next(
                (o for o in settled if isinstance(o, ExternalServiceError)), None
            )
            if safe is not None:
                raise safe
            raise ExternalServiceError(
                "Não foi possível buscar perfis no "
                + " e no ".join(failed)
                + " agora. Tente novamente em instantes."
            )

        profiles = self._merge_profiles(groups, count)
        if failed:
            logger.warning(
                "search_partial_results",
                niche=niche,
                failed_sources=failed,
                profiles=len(profiles),
            )
        return profiles

    @staticmethod
    def _merge_profiles(groups: list[list[dict]], limit: int) -> list[dict]:
        """Intercala as fontes na ordem e deduplica por @username.

        O round-robin (Apify[0], Tavily[0], Apify[1], Tavily[1]…) evita
        que o Tavily fique sempre no fim: se a Apify já devolvesse
        `limit` perfis, os resultados do Tavily nunca apareceriam.
        """
        merged: list[dict] = []
        seen: set[str] = set()
        for i in range(max((len(g) for g in groups), default=0)):
            for group in groups:
                if i >= len(group):
                    continue
                username = (group[i].get("username") or "").strip().lower()
                if not username or username in seen:
                    continue
                seen.add(username)
                merged.append(group[i])
                if len(merged) >= limit:
                    return merged
        return merged

    async def embed(self, text: str) -> list[float] | None:
        """Gera embedding do texto usando modelo via OpenRouter."""
        if not settings.openrouter_api_key:
            return None
        try:
            res = await get_http_client().post(
                f"{OPENROUTER_BASE}/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": settings.ai_model, "input": text},
                timeout=EMBED_TIMEOUT_SECONDS,
            )
            res.raise_for_status()
            return res.json()["data"][0]["embedding"]
        except Exception as exc:
            logger.error("embed_error", error=str(exc))
            return None

    # ── Apify ───────────────────────────────────────────────────

    def _apify_search(self, niche: str, count: int) -> list[dict]:
        """Busca perfis reais no Instagram via Apify Search Scraper.

        SÍNCRONO de propósito: chamado via run_in_threadpool para não
        bloquear o event loop do uvicorn.
        """
        if not settings.apify_api_token:
            raise ExternalServiceError("APIFY_API_TOKEN não configurada no .env")

        from apify_client import ApifyClient

        client = ApifyClient(settings.apify_api_token)

        run_input = {
            "search": niche,
            "searchType": "profiles",
            "searchLimit": min(count, 250),
        }

        logger.info(
            "apify_run_start",
            niche=niche,
            limit=run_input["searchLimit"],
            actor=settings.apify_actor_id,
        )

        run = client.actor(settings.apify_actor_id).call(run_input=run_input)

        profiles = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            # Filtra apenas itens que parecem perfis (têm username)
            if not item.get("username"):
                continue
            # Pula perfis privados
            if item.get("private"):
                continue
            profiles.append(item)

        logger.info("apify_run_done", profiles_found=len(profiles))
        return profiles

    # ── Tavily (busca web restrita ao instagram.com) ─────────────

    async def _tavily_search(self, niche: str, count: int) -> list[dict]:
        """Busca páginas de perfil do Instagram no Tavily.

        Assíncrono (httpx) e rodado em paralelo com a Apify. Só entram
        URLs de perfil (um único segmento de caminho) — posts, reels e
        páginas do explore são descartados na hora.
        """
        if not settings.tavily_api_key:
            raise ExternalServiceError("TAVILY_API_KEY não configurada no .env")

        res = await get_http_client().post(
            f"{TAVILY_BASE}/search",
            headers={
                "Authorization": f"Bearer {settings.tavily_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "query": f"{niche} instagram",
                # basic = 1 crédito/pedido e já resolve o ranqueamento.
                "search_depth": "basic",
                "max_results": min(count, TAVILY_MAX_RESULTS),
                "topic": "general",
                # restrict = filtro duro: só resultados do Instagram.
                "include_domains": ["instagram.com"],
                "include_domains_mode": "restrict",
            },
            timeout=TAVILY_TIMEOUT_SECONDS,
        )
        if res.status_code != 200:
            # Texto cru só vai para o log (a fonte vira 502 genérica
            # se for a única configurada).
            raise RuntimeError(f"Tavily {res.status_code}: {res.text[:300]}")

        profiles = []
        for item in res.json().get("results", []):
            profile = self._parse_tavily_result(item)
            if profile:
                profiles.append(profile)

        logger.info(
            "tavily_search_done", niche=niche, profiles_found=len(profiles)
        )
        return profiles

    # ── Parsers do Tavily (resultado → formato de perfil) ────────

    # /usuario/ e /usuario — qualquer outro caminho não é perfil.
    _IG_PROFILE_PATH = re.compile(r"^/([A-Za-z0-9._]+)/?$")
    # Caminhos do Instagram que nunca são perfis (posts, reels…).
    _IG_RESERVED_PATHS = frozenset(
        {
            "p", "reel", "reels", "tv", "explore", "stories", "n",
            "about", "developer", "legal", "directory", "web", "accounts",
            "api", "settings", "direct", "inbox", "session", "emails",
        }
    )
    # Meta description do IG:
    # "1,512 Followers, 200 Following, 512 Posts - See Instagram photos… (@user)".
    _IG_META_PREFIX = re.compile(
        r"^\s*[\d.,]+\s*[KMB]?\s*(?:followers|seguidores)\b"
        r"[\s\S]*?\(@[\w.]+\)\s*",
        re.IGNORECASE,
    )
    _IG_FOLLOWERS = re.compile(
        r"([\d.,]+\s*[KMB]?)\s*(?:followers|seguidores)", re.IGNORECASE
    )

    @classmethod
    def _parse_tavily_result(cls, item: dict) -> dict | None:
        """Converte um resultado do Tavily no formato de perfil da Apify.

        Devolve None quando a URL não é um perfil (post, reel, lista…).
        """
        username = cls._username_from_url(str(item.get("url") or ""))
        if not username:
            return None

        title = str(item.get("title") or "")
        content = str(item.get("content") or "").strip()

        # "Nome (@user) • Instagram photos and videos" → "Nome"
        name = cls._name_from_title(title) or cls._name_from_title(content)

        followers = 0
        match = cls._IG_FOLLOWERS.search(content)
        if match:
            followers = cls._parse_count(match.group(1))

        # Remove a meta description (ruído) e mantém o texto da bio.
        bio = cls._IG_META_PREFIX.sub("", content).strip()[:300]

        return {
            "username": username,
            "fullName": name,
            "biography": bio,
            "followersCount": followers,
            "url": f"https://www.instagram.com/{username}/",
            "externalUrl": None,
            "isBusinessAccount": False,
            "businessCategoryName": "",
            "verified": False,
            "private": False,
        }

    @classmethod
    def _username_from_url(cls, url: str) -> str | None:
        """Usuário do Instagram na URL; None se não for um perfil."""
        try:
            parsed = urlparse(url)
        except ValueError:
            return None
        host = (parsed.hostname or "").lower()
        if host != "instagram.com" and not host.endswith(".instagram.com"):
            return None
        match = cls._IG_PROFILE_PATH.match(parsed.path)
        if not match:
            return None
        username = match.group(1)
        if username.lower() in cls._IG_RESERVED_PATHS:
            return None
        return username

    @classmethod
    def _name_from_title(cls, text: str) -> str:
        """Nome imediatamente antes de '(@usuario)' no título/conteúdo."""
        match = re.search(r"\(@[\w.]+\)", text)
        if not match:
            return ""
        before = text[: match.start()].strip()
        # Formato antigo traz curtidas antes: "42 likes - Nome".
        head, sep, tail = before.rpartition(" - ")
        if sep and re.search(
            r"(likes?|curtidas?|photos?|fotos?|videos?|vídeos?)", head, re.I
        ):
            before = tail.strip()
        before = before.strip(" ,;:•|·-–—")
        return before if re.search(r"[A-Za-zÀ-ÿ]", before) else ""

    @staticmethod
    def _parse_count(raw: str) -> int:
        """Contador do snippet do Tavily → inteiro: '1.5K'→1500, '1,512'→1512.

        Sufixo (K/M/B) casa com notação decimal ("1.5K"); sem sufixo,
        separadores são tratados como milhar e descartados.
        """
        raw = raw.replace(" ", "")
        if not raw:
            return 0
        multiplier = 1
        if raw[-1].upper() in ("K", "M", "B"):
            multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[
                raw[-1].upper()
            ]
            raw = raw[:-1]
            try:
                return int(float(raw.replace(",", ".")) * multiplier)
            except ValueError:
                return 0
        return int(re.sub(r"\D", "", raw) or 0)

    # ── IA ──────────────────────────────────────────────────────

    async def _ai_classify(
        self, niche: str, profiles: list[dict]
    ) -> list[dict | None]:
        """Classifica perfis reais com IA (produto, dificuldade, confiança).

        Os perfis são fatiados em chunks e classificados em paralelo
        (`asyncio.gather`) — menos latência e resposta menos propensa a
        truncar no max_tokens. Falha em um chunk deixa só aquele trecho
        sem classificação (default), sem derrubar os demais.
        """
        # Monta resumo compacto dos perfis para a IA
        summary = []
        for i, p in enumerate(profiles[:CLASSIFY_MAX_PROFILES]):
            summary.append(
                {
                    "index": i,
                    "username": p.get("username", ""),
                    "fullName": p.get("fullName", ""),
                    "bio": (p.get("biography") or "")[:200],
                    "followers": p.get("followersCount", 0),
                    "business": p.get("isBusinessAccount", False),
                    "category": p.get("businessCategoryName", ""),
                }
            )

        result: list[dict | None] = [None] * len(profiles)
        if not summary:
            return result

        chunks = [
            summary[i : i + CLASSIFY_CHUNK_SIZE]
            for i in range(0, len(summary), CLASSIFY_CHUNK_SIZE)
        ]
        settled = await asyncio.gather(
            *(self._classify_chunk(niche, chunk) for chunk in chunks),
            return_exceptions=True,
        )

        failed_chunks = 0
        for chunk, classified in zip(chunks, settled):
            if isinstance(classified, BaseException):
                failed_chunks += 1
                logger.warning(
                    "ai_classify_chunk_failed",
                    error=str(classified),
                    chunk_size=len(chunk),
                )
                continue
            for c in classified:
                idx = c.get("index")
                if isinstance(idx, int) and 0 <= idx < len(result):
                    result[idx] = c

        if failed_chunks:
            logger.warning(
                "ai_classify_partial",
                failed_chunks=failed_chunks,
                total_chunks=len(chunks),
            )
        return result

    async def _classify_chunk(
        self, niche: str, summaries: list[dict]
    ) -> list[dict]:
        """Chama a OpenRouter para um chunk de perfis e devolve as classificações.

        Cada item do summary carrega o `index` global (posição original no
        resultado), então o merge em `_ai_classify` é direto. JSON ilegível
        devolve lista vazia (equivalente ao "sem classificação").
        """
        res = await get_http_client().post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ai_chat_model,
                "messages": [
                    {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Nicho alvo: {niche}\n"
                            f"Perfis encontrados:\n"
                            f"{json.dumps(summaries, ensure_ascii=False, indent=1)}"
                        ),
                    },
                ],
                "temperature": 0.3,
                "max_tokens": 8000,
                "reasoning": {"enabled": False},
            },
            timeout=CLASSIFY_TIMEOUT_SECONDS,
        )
        if res.status_code != 200:
            raise RuntimeError(
                f"OpenRouter {res.status_code}: {res.text[:300]}"
            )
        content = res.json()["choices"][0]["message"]["content"] or ""

        # Parse do JSON
        cleaned = re.sub(r"```(?:json)?\s*", "", content)
        cleaned = re.sub(r"```\s*$", "", cleaned.strip())
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return []

        try:
            obj = json.loads(match.group())
        except json.JSONDecodeError:
            return []

        classifs = obj.get("classificacoes", [])
        return [c for c in classifs if isinstance(c, dict)]

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _extract_contact(profile: dict) -> str | None:
        """Extrai contato do perfil (external URL ou bio com telefone/email)."""
        # External URL (site, linktr.ee, etc.)
        ext = profile.get("externalUrl")
        if ext:
            return ext

        # Procura email/telefone na bio
        bio = profile.get("biography") or ""
        email_match = re.search(
            r"[\w.+-]+@[\w-]+\.[\w.-]+", bio
        )
        if email_match:
            return email_match.group()

        phone_match = re.search(
            r"\(?\d{2}\)?\s*9?\d{4}-?\d{4}", bio
        )
        if phone_match:
            return phone_match.group()

        return None
