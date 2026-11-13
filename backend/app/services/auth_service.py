"""Service de autenticação — registro, login, confirmação e recuperação.

- Senhas: bcrypt (passlib).
- Sessão: JWT (python-jose, HS256) com validade de 7 dias.
- E-mails: Resend (via app.services.email_service), sempre com token de
  uso único e expiração.
"""
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.exceptions import (
    BusinessLogicError,
    ConflictError,
    ForbiddenError,
    UnauthorizedError,
)
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
from app.services import email_service

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = timedelta(days=7)
VERIFY_TOKEN_EXPIRE = timedelta(hours=24)
RESET_TOKEN_EXPIRE = timedelta(minutes=60)

# Mensagem única para /forgot nos dois casos (conta existe ou não) —
# resposta idêntica não revela quem tem conta cadastrada.
_FORGOT_MESSAGE = (
    "Se existir uma conta com este e-mail, enviaremos as "
    "instruções de recuperação."
)


def _utcnow() -> datetime:
    """UTC sem tzinfo — mesmo formato persistido pelo SQLAlchemy."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except (ValueError, TypeError):
        # Hash corrompido/inválido não pode derrubar o login.
        return False


def create_access_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE
    return jwt.encode(
        {"sub": str(user_id), "exp": expires},
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> int | None:
    """Decodifica o JWT e devolve o user_id; inválido/expirado → None."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return int(payload.get("sub", ""))
    except (JWTError, ValueError, TypeError):
        return None


class AuthService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def register(self, data: RegisterRequest) -> MessageResponse:
        email = _normalize_email(data.email)
        if self.repo.find_by_email(email):
            raise ConflictError("Já existe uma conta com este e-mail")

        token = secrets.token_urlsafe(32)  # 43 chars → coluna String(64)
        self.repo.create(
            email=email,
            password_hash=hash_password(data.password),
            verification_token=token,
            verification_expires_at=_utcnow() + VERIFY_TOKEN_EXPIRE,
        )
        # Se o envio falhar, a conta já existe → o usuário se recupera
        # via /resend-confirmation (não pode duplicar o cadastro).
        await email_service.send_verification_email(email, token)
        return MessageResponse(
            message=(
                "Cadastro realizado. Enviamos um link de confirmação "
                "para o seu e-mail."
            )
        )

    def login(self, data: LoginRequest) -> TokenResponse:
        email = _normalize_email(data.email)
        user = self.repo.find_by_email(email)
        # Mensagem idêntica nos dois casos (anti-enumeração de contas).
        if not user or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("E-mail ou senha incorretos")
        if not user.email_verified:
            raise ForbiddenError(
                "E-mail não confirmado. Verifique sua caixa de entrada."
            )
        return TokenResponse(access_token=create_access_token(user.id))

    def confirm(self, data: ConfirmRequest) -> MessageResponse:
        user = self.repo.find_by_verification_token(data.token)
        if (
            not user
            or not user.verification_expires_at
            or user.verification_expires_at < _utcnow()
        ):
            raise BusinessLogicError(
                "Link de confirmação inválido ou expirado."
            )
        user.email_verified = True
        user.verification_token = None
        user.verification_expires_at = None
        self.repo.save(user)
        return MessageResponse(message="E-mail confirmado. Já pode fazer login.")

    async def resend_confirmation(
        self, data: ForgotPasswordRequest
    ) -> MessageResponse:
        user = self.repo.find_by_email(_normalize_email(data.email))
        if user and not user.email_verified:
            token = secrets.token_urlsafe(32)
            user.verification_token = token
            user.verification_expires_at = _utcnow() + VERIFY_TOKEN_EXPIRE
            self.repo.save(user)
            await email_service.send_verification_email(user.email, token)
        # Sempre a mesma resposta (não revela existência/estado da conta).
        return MessageResponse(
            message=(
                "Se existir uma conta pendente, enviaremos um novo "
                "link de confirmação."
            )
        )

    async def forgot_password(
        self, data: ForgotPasswordRequest
    ) -> MessageResponse:
        user = self.repo.find_by_email(_normalize_email(data.email))
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_expires_at = _utcnow() + RESET_TOKEN_EXPIRE
            self.repo.save(user)
            await email_service.send_password_reset_email(user.email, token)
        return MessageResponse(message=_FORGOT_MESSAGE)

    def reset_password(self, data: ResetPasswordRequest) -> MessageResponse:
        user = self.repo.find_by_reset_token(data.token)
        if (
            not user
            or not user.reset_expires_at
            or user.reset_expires_at < _utcnow()
        ):
            raise BusinessLogicError(
                "Link de recuperação inválido ou expirado."
            )
        user.password_hash = hash_password(data.password)
        user.reset_token = None
        user.reset_expires_at = None
        self.repo.save(user)
        return MessageResponse(
            message="Senha redefinida. Faça login com a nova senha."
        )

    @staticmethod
    def me(user: User) -> UserResponse:
        return UserResponse.model_validate(user)
