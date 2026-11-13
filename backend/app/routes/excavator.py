"""Rotas do Escavador — busca de leads via IA + cota diária por usuário."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rate_limit import rate_limit_user
from app.exceptions import DailyQuotaError
from app.logging_config import get_logger
from app.models.user_model import User
from app.repositories.quota_repository import QuotaRepository
from app.services.excavator_service import ExcavatorService
from app.services.quota_service import QuotaService

# Todas as rotas do Escavador exigem autenticação (consomem Apify/Tavily/IA) e
# passam pela cota por user_id (100 req/min) — o /excavate é caro.
router = APIRouter(
    prefix="/api/v1",
    tags=["excavator"],
    dependencies=[Depends(get_current_user), Depends(rate_limit_user)],
)
logger = get_logger(__name__)

# Limite da busca completa (Apify + Tavily + classificação IA). Estourou → 504.
EXCAVATE_TIMEOUT_SECONDS = 180


# ── Schemas ───────────────────────────────────────────────────────
class ExcavateRequest(BaseModel):
    nicho: str = Field(..., min_length=1, max_length=500)
    quantidade: int = Field(default=30, ge=1, le=50)
    model_config = {"extra": "forbid"}


class ExcavatedLead(BaseModel):
    instagram: str
    nome: str
    empresa: str | None = None
    contato: str | None = None
    produto: str
    dificuldade: str
    confianca: float
    # Dados reais da fonte (Apify e/ou Tavily)
    seguidores: int = 0
    bio: str = ""
    categoria: str = ""
    verificado: bool = False
    negocio: bool = False
    url: str = ""


class QuotaInfo(BaseModel):
    """Cota diária de perfis escavados do usuário autenticado."""

    ativa: bool
    limite: int
    usado: int
    restante: int
    renova_em: str | None = None  # ISO 8601 da próxima meia-noite BRT


class ExcavateResponse(BaseModel):
    resultados: list[ExcavatedLead]
    # Estado da cota após esta escavação (o frontend atualiza o indicador).
    cota: QuotaInfo


class EmbedRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    model_config = {"extra": "forbid"}


class EmbedResponse(BaseModel):
    embedding: list[float] | None
    dimensions: int = 0


# ── Dependencies ──────────────────────────────────────────────────
def get_excavator_service() -> ExcavatorService:
    return ExcavatorService()


def get_quota_service(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QuotaService:
    # Cota é POR USUÁRIO: o repositório recebe o user_id (isolamento).
    return QuotaService(QuotaRepository(db, user.id))


# ── Rotas ─────────────────────────────────────────────────────────
@router.get("/excavate/quota", response_model=QuotaInfo)
def get_quota(quota: QuotaService = Depends(get_quota_service)):
    """Cota diária de perfis escavados do usuário autenticado."""
    return QuotaInfo(**quota.snapshot())


@router.post("/excavate", response_model=ExcavateResponse)
async def excavate(
    data: ExcavateRequest,
    service: ExcavatorService = Depends(get_excavator_service),
    quota: QuotaService = Depends(get_quota_service),
):
    """
    Busca perfis do Instagram para o nicho informado (Apify + Tavily em
    paralelo) e devolve a lista de leads potenciais já classificada por IA.

    Respeita a cota diária de perfis escavados: o espaço é RESERVADO antes
    da busca (falha devolve a reserva) e só o que é entregue é cobrado.
    """
    # 1. Reserva da cota — 0 = dia esgotado (ou corrida perdida).
    granted = quota.reserve(data.quantidade)
    if granted <= 0:
        raise DailyQuotaError(quota.seconds_until_reset(), quota.limit)

    # 2. Busca (só o `granted` reservado é pedido às fontes).
    results: list[dict] | None = None
    try:
        results = await asyncio.wait_for(
            service.excavate(data.nicho, granted),
            timeout=EXCAVATE_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.error(
            "excavate_timeout",
            nicho=data.nicho,
            timeout_s=EXCAVATE_TIMEOUT_SECONDS,
        )
        raise HTTPException(
            status_code=504,
            detail="A busca demorou mais que o esperado. Tente novamente.",
        ) from None
    except RuntimeError as exc:
        # ExternalServiceError já chega com mensagem segura (sem vazar
        # detalhe interno do Apify/OpenRouter — isso fica no log).
        logger.error("excavate_failed", nicho=data.nicho, error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        if results is None:
            # Busca falhou/estourou o tempo → a reserva volta para a cota.
            quota.release(granted)

    # 3. Só o entregue conta: achou menos que o reservado → devolve a diferença.
    quota.release(granted - len(results))

    return ExcavateResponse(
        resultados=results, cota=QuotaInfo(**quota.snapshot())
    )


@router.post("/embed", response_model=EmbedResponse)
async def embed(
    data: EmbedRequest,
    service: ExcavatorService = Depends(get_excavator_service),
):
    """
    Gera embedding do texto usando Nemotron (nvidia/nemotron-3.5-embed-1b:free).
    Útil para busca semântica de leads.
    """
    embedding = await service.embed(data.text)
    return EmbedResponse(
        embedding=embedding,
        dimensions=len(embedding) if embedding else 0,
    )
