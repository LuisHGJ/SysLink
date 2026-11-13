"""Rotas de leads — CRUD + export CSV."""
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rate_limit import rate_limit_user
from app.models.user_model import User
from app.repositories.lead_repository import LeadRepository
from app.schemas.lead_schema import (
    LeadCreate,
    LeadPatch,
    LeadResponse,
    LeadUpdate,
)
from app.services.lead_service import LeadService

# Cota por user_id (100 req/min) em TODAS as rotas de leads.
router = APIRouter(
    prefix="/api/v1/leads",
    tags=["leads"],
    dependencies=[Depends(rate_limit_user)],
)

CSV_HEADERS = [
    "Nome",
    "Empresa",
    "Contato",
    "Instagram",
    "Produto",
    "Dificuldade",
    "Status",
    "Motivo da perda",
    "Último contato",
    "Arquivos",
]


def _get_service(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LeadService:
    # Todo acesso a leads passa por aqui → rotas exigem Bearer token e o
    # repositório recebe o user_id (isolamento por usuário).
    repo = LeadRepository(db, user.id)
    return LeadService(repo)


@router.post("", response_model=LeadResponse, status_code=201)
def create_lead(
    data: LeadCreate,
    service: LeadService = Depends(_get_service),
):
    """Cria um novo lead."""
    return service.create_lead(data)


@router.get("", response_model=list[LeadResponse])
def list_leads(service: LeadService = Depends(_get_service)):
    """Lista todos os leads."""
    return service.list_leads()


@router.get("/export")
def export_csv(service: LeadService = Depends(_get_service)):
    """Exporta todos os leads em CSV."""
    leads = service.list_leads()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(CSV_HEADERS)

    for lead in leads:
        arquivos = ", ".join(lead.arquivos) if lead.arquivos else ""
        writer.writerow(
            [
                lead.nome,
                lead.empresa or "",
                lead.contato or "",
                lead.instagram or "",
                lead.produto,
                lead.dificuldade,
                lead.status,
                lead.motivo_perda or "",
                lead.ultimo_contato or "",
                arquivos,
            ]
        )

    filename = f"syslink_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    service: LeadService = Depends(_get_service),
):
    """Retorna um lead pelo ID."""
    return service.get_lead(lead_id)


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    data: LeadUpdate,
    service: LeadService = Depends(_get_service),
):
    """Atualiza completamente um lead."""
    return service.update_lead(lead_id, data)


@router.patch("/{lead_id}", response_model=LeadResponse)
def patch_lead(
    lead_id: int,
    data: LeadPatch,
    service: LeadService = Depends(_get_service),
):
    """Atualiza parcialmente um lead."""
    return service.patch_lead(lead_id, data)


@router.delete("/{lead_id}", status_code=204)
def delete_lead(
    lead_id: int,
    service: LeadService = Depends(_get_service),
):
    """Remove um lead."""
    service.delete_lead(lead_id)
    return Response(status_code=204)
