"""Ponto de entrada da aplicação FastAPI."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import Base, engine
from app.error_handlers import register_error_handlers
from app.logging_config import get_logger, setup_logging
from app.middleware import RequestIDMiddleware
from app.services.excavator_service import close_http_client

logger = get_logger(__name__)


def _ensure_lead_user_column() -> None:
    """Migração leve (create_all não altera tabelas existentes).

    Em bancos dev criados ANTES do multi-usuário, adiciona leads.user_id.
    Linhas antigas ficam com user_id NULL e não aparecem em nenhuma
    listagem (a query filtra por usuário) — backfill manual se quiser
    resgatá-las: UPDATE leads SET user_id = <id>;
    """
    if engine.dialect.name != "postgresql":
        return  # testes usam SQLite em memória (tabela nova, já com a coluna)
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE leads ADD COLUMN IF NOT EXISTS user_id "
                "INTEGER REFERENCES users(id)"
            )
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cria tabelas no startup (substituir por Alembic em produção)."""
    try:
        Base.metadata.create_all(bind=engine)
        _ensure_lead_user_column()
    except Exception as exc:
        # Em testes o banco é SQLite override; em produção a causa fica no
        # log (engolir em silêncio esconderia o banco fora do ar).
        logger.warning("create_tables_skipped", error=str(exc))
    yield
    # Fecha o AsyncClient compartilhado do Escavador (httpx).
    await close_http_client()


app = FastAPI(
    title="SysLink API",
    version="0.1.0",
    description="API do SysLink — gestão de leads e funil de vendas.",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────
# CORS deve ser adicionado por último (LIFO → roda primeiro, outermost)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ── Handlers de erro ─────────────────────────────────────────────
register_error_handlers(app)

# ── Logging ──────────────────────────────────────────────────────
setup_logging()


@app.get("/health", tags=["health"])
async def health_check():
    """Health check da API."""
    return {"status": "ok", "environment": settings.environment}


# ── Rotas ─────────────────────────────────────────────────────────
from app.routes.auth import router as auth_router  # noqa: E402
from app.routes.leads import router as leads_router  # noqa: E402
from app.routes.excavator import router as excavator_router  # noqa: E402

app.include_router(auth_router)
app.include_router(leads_router)
app.include_router(excavator_router)
