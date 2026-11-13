"""Rotas de autenticação — registro, login, confirmação e recuperação."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rate_limit import rate_limit_auth
from app.models.user_model import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import (
    ConfirmRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _get_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=201,
    dependencies=[Depends(rate_limit_auth)],
)
async def register(
    data: RegisterRequest,
    service: AuthService = Depends(_get_service),
):
    """Cria uma conta e envia o e-mail de confirmação (Resend)."""
    return await service.register(data)


@router.post(
    "/confirm",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit_auth)],
)
def confirm(
    data: ConfirmRequest,
    service: AuthService = Depends(_get_service),
):
    """Confirma o e-mail com o token recebido no link."""
    return service.confirm(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_auth)],
)
def login(
    data: LoginRequest,
    service: AuthService = Depends(_get_service),
):
    """Troca e-mail + senha por um JWT (exige e-mail confirmado)."""
    return service.login(data)


@router.get("/me", response_model=UserResponse)
def me(
    user: User = Depends(get_current_user),
    service: AuthService = Depends(_get_service),
):
    """Dados do usuário autenticado (valida o token)."""
    return service.me(user)


@router.post(
    "/forgot",
    response_model=MessageResponse,
    status_code=202,
    dependencies=[Depends(rate_limit_auth)],
)
async def forgot(
    data: ForgotPasswordRequest,
    service: AuthService = Depends(_get_service),
):
    """Envia o link de redefinição de senha (resposta genérica sempre)."""
    return await service.forgot_password(data)


@router.post(
    "/resend-confirmation",
    response_model=MessageResponse,
    status_code=202,
    dependencies=[Depends(rate_limit_auth)],
)
async def resend_confirmation(
    data: ForgotPasswordRequest,
    service: AuthService = Depends(_get_service),
):
    """Reenvia o e-mail de confirmação para uma conta pendente."""
    return await service.resend_confirmation(data)


@router.post(
    "/reset",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit_auth)],
)
def reset(
    data: ResetPasswordRequest,
    service: AuthService = Depends(_get_service),
):
    """Redefine a senha com o token recebido no e-mail (uso único)."""
    return service.reset_password(data)
