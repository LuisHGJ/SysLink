"""Repository de leads — acesso a dados via SQLAlchemy.

Todas as queries são filtradas por `user_id`: um lead pertence a um
único usuário e nunca aparece nas listagens dos demais.
"""
from sqlalchemy.orm import Session

from app.models.lead_model import Lead
from app.schemas.lead_schema import LeadCreate, LeadPatch, LeadUpdate


class LeadRepository:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def _scoped(self):
        return self.db.query(Lead).filter(Lead.user_id == self.user_id)

    def find_by_instagram(self, instagram: str) -> Lead | None:
        """Busca lead do usuário atual pelo Instagram (case-insensitive)."""
        instagram_normalized = instagram.strip().lower() if instagram else ""
        return (
            self._scoped()
            .filter(Lead.instagram != None)
            .filter(Lead.instagram.ilike(instagram_normalized))
            .first()
        )

    def create(self, data: LeadCreate) -> Lead:
        lead = Lead(**data.model_dump(), user_id=self.user_id)
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def list_all(self) -> list[Lead]:
        return self._scoped().order_by(Lead.id.desc()).all()

    def get_by_id(self, lead_id: int) -> Lead | None:
        return self._scoped().filter(Lead.id == lead_id).first()

    def update(self, lead_id: int, data: LeadUpdate) -> Lead | None:
        lead = self.get_by_id(lead_id)
        if not lead:
            return None
        for field, value in data.model_dump().items():
            setattr(lead, field, value)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def patch(self, lead_id: int, data: LeadPatch) -> Lead | None:
        lead = self.get_by_id(lead_id)
        if not lead:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lead, field, value)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def delete(self, lead_id: int) -> bool:
        lead = self.get_by_id(lead_id)
        if not lead:
            return False
        self.db.delete(lead)
        self.db.commit()
        return True
