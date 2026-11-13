"""Configurações centralizadas via variáveis de ambiente."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Carrega secrets exclusivamente de variáveis de ambiente / .env."""

    # ── Banco ────────────────────────────────────────────────────
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "syslink"

    # ── App ──────────────────────────────────────────────────────
    secret_key: str = "dev-secret-key-change-me"
    environment: str = "development"
    log_level: str = "INFO"
    sentry_dsn: str = ""

    # ── IA / OpenRouter ──────────────────────────────────────────
    openrouter_api_key: str = ""
    ai_model: str = "nvidia/nemotron-3.5-lightning:free"
    ai_chat_model: str = "nvidia/nemotron-3.5-lightning:free"

    # ── Apify (scraping Instagram) ───────────────────────────────
    apify_api_token: str = ""
    apify_actor_id: str = "apify/instagram-search-scraper"

    # ── Tavily (busca web de perfis do Instagram) ────────────────
    # Roda em paralelo com a Apify no Escavador; sem chave a busca
    # continua só com a Apify.
    tavily_api_key: str = ""

    # ── Cota do Escavador ────────────────────────────────────────
    # Máximo de perfis escavados por usuário por dia (calendário BRT).
    # 0 (ou negativo) desativa a cota.
    excavate_daily_profile_limit: int = 50

    # ── Resend (envio de e-mails) ────────────────────────────────
    resend_api_key: str = ""
    resend_from: str = ""

    # ── Frontend (links nos e-mails de verificação/recuperação) ───
    frontend_url: str = "http://localhost:3000"

    # ── Rate limit (janela deslizante de 60s, in-memory) ─────────
    # 0 (ou negativo) desativa o limite correspondente.
    rate_limit_auth_per_minute: int = 5      # por IP nos endpoints públicos de auth
    rate_limit_user_per_minute: int = 100    # por user_id nas rotas autenticadas
    # True só atrás de proxy confiável (X-Forwarded-For). Sem proxy,
    # manter False: sem isso qualquer cliente forjaria o IP.
    trust_proxy_headers: bool = False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = {
        "env_file": ".env",
        "extra": "forbid",
    }


settings = Settings()
