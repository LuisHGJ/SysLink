"""Service de leads — lógica de negócio."""
from app.exceptions import NotFoundError
from app.repositories.lead_repository import LeadRepository
from app.schemas.lead_schema import LeadCreate, LeadPatch, LeadResponse, LeadUpdate


class LeadService:
    def __init__(self, repo: LeadRepository):
        self.repo = repo

    def create_lead(self, data: LeadCreate) -> LeadResponse:
        # Verificação simples: se já existir lead com mesmo Instagram, retorna-o
        existing = self.repo.find_by_instagram(data.instagram)
        if existing:
            return LeadResponse.model_validate(existing)
        lead = self.repo.create(data)
        return LeadResponse.model_validate(lead)

    def list_leads(self) -> list[LeadResponse]:
        leads = self.repo.list_all()
        return [LeadResponse.model_validate(l) for l in leads]

    def get_lead(self, lead_id: int) -> LeadResponse:
        lead = self.repo.get_by_id(lead_id)
        if not lead:
            raise NotFoundError("Lead não encontrado")
        return LeadResponse.model_validate(lead)

    def update_lead(self, lead_id: int, data: LeadUpdate) -> LeadResponse:
        lead = self.repo.update(lead_id, data)
        if not lead:
            raise NotFoundError("Lead não encontrado")
        return LeadResponse.model_validate(lead)

    def patch_lead(self, lead_id: int, data: LeadPatch) -> LeadResponse:
        lead = self.repo.patch(lead_id, data)
        if not lead:
            raise NotFoundError("Lead não encontrado")
        return LeadResponse.model_validate(lead)

    def delete_lead(self, lead_id: int) -> None:
        deleted = self.repo.delete(lead_id)
        if not deleted:
            raise NotFoundError("Lead não encontrado")
