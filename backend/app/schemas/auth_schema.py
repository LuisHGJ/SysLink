"""Schemas Pydantic para autenticação — validação de entrada/saída."""
from pydantic import BaseModel, Field

# Formato básico de e-mail (sem dependência de email-validator).
EMAIL_PATTERN = r"^[\w.+-]+@[\w-]+\.[\w.-]+$"


class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=8, max_length=72)  # 72 = teto do bcrypt
    model_config = {"extra": "forbid"}


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(..., max_length=255)
    model_config = {"extra": "forbid"}


class ConfirmRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=255)
    model_config = {"extra": "forbid"}


class ForgotPasswordRequest(BaseModel):
    """E-mail puro — usado em /forgot e /resend-confirmation."""

    email: str = Field(..., max_length=255, pattern=EMAIL_PATTERN)
    model_config = {"extra": "forbid"}


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=72)
    model_config = {"extra": "forbid"}


# ── Saídas ─────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id: int
    email: str
    email_verified: bool

    model_config = {"from_attributes": True}
