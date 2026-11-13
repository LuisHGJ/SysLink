"""Exceções customizadas da aplicação."""
from fastapi import HTTPException


class BusinessLogicError(HTTPException):
    """Erro de regra de negócio → HTTP 400."""

    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)


class NotFoundError(HTTPException):
    """Recurso não encontrado → HTTP 404."""

    def __init__(self, detail: str = "Recurso não encontrado"):
        super().__init__(status_code=404, detail=detail)


class UnauthorizedError(HTTPException):
    """Não autenticado → HTTP 401."""

    def __init__(self, detail: str = "Não autenticado"):
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(HTTPException):
    """Sem permissão → HTTP 403."""

    def __init__(self, detail: str = "Sem permissão"):
        super().__init__(status_code=403, detail=detail)


class ConflictError(HTTPException):
    """Conflito (recurso duplicado, ex.: e-mail já cadastrado) → HTTP 409."""

    def __init__(self, detail: str = "Conflito"):
        super().__init__(status_code=409, detail=detail)


class RateLimitError(HTTPException):
    """Muitas tentativas → HTTP 429, com header Retry-After (segundos)."""

    def __init__(self, retry_after_seconds: int):
        super().__init__(
            status_code=429,
            detail="Muitas tentativas. Tente novamente em "
            f"{retry_after_seconds} segundos.",
            headers={"Retry-After": str(retry_after_seconds)},
        )


class DailyQuotaError(RateLimitError):
    """Cota diária de perfis escavados atingida → HTTP 429 + Retry-After.

    Herda de `RateLimitError` (status 429 + header Retry-After) e só
    troca a mensagem: a do rate limit fala de "segundos", o que
    confundiria num limite que dura o dia inteiro.
    """

    def __init__(self, retry_after_seconds: int, limit: int):
        super().__init__(retry_after_seconds)
        if retry_after_seconds >= 3600:
            when = f"em ~{retry_after_seconds // 3600}h"
        else:
            when = f"em ~{max(1, retry_after_seconds // 60)}min"
        self.detail = (
            f"Cota diária de {limit} perfis escavados atingida. "
            f"A cota renova {when}."
        )


class ExternalServiceError(RuntimeError):
    """Falha em serviço externo (Apify, OpenRouter) com mensagem SEGURA.

    Só o texto desta exceção vira `detail` na resposta HTTP; o detalhe
    técnico (URL, status, corpo cru) fica no log. É um RuntimeError para
    as rotas continuarem capturando com `except RuntimeError`.
    """
