"""Dependências FastAPI de autenticação (extras compartilhados entre rotas)."""
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import UnauthorizedError
from app.models.user_model import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import decode_access_token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Resolve o usuário a partir do header `Authorization: Bearer <jwt>`.

    Qualquer problema (ausente, formato errado, token inválido/expirado,
    usuário removido) → 401 problem+json em PT-BR.
    """
    if not authorization:
        raise UnauthorizedError("Cabeçalho Authorization ausente.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError(
            "Formato de token inválido. Use: Bearer <token>."
        )

    user_id = decode_access_token(token)
    if user_id is None:
        raise UnauthorizedError("Sessão inválida ou expirada. Faça login novamente.")

    user = UserRepository(db).get_by_id(user_id)
    if not user:
        raise UnauthorizedError("Usuário não encontrado.")
    return user
