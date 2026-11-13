"""Handlers de erro padronizados (RFC 7807 problem+json)."""
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import ExternalServiceError
from app.logging_config import get_logger

logger = get_logger(__name__)

# Mensagens de validação em PT-BR (Pydantic devolve em inglês).
_VALIDATION_MESSAGES: dict[str, str] = {
    "missing": "campo obrigatório",
    "string_type": "deve ser texto",
    "string_too_short": "conteúdo curto demais",
    "string_too_long": "conteúdo longo demais",
    "string_pattern_mismatch": "formato inválido",
    "int_type": "deve ser um número inteiro",
    "int_parsing": "deve ser um número inteiro",
    "float_parsing": "deve ser um número",
    "bool_type": "deve ser verdadeiro ou falso",
    "bool_parsing": "deve ser verdadeiro ou falso",
    "greater_than_equal": "valor abaixo do mínimo permitido",
    "less_than_equal": "valor acima do máximo permitido",
    "enum": "valor não permitido",
    "literal_error": "valor não permitido",
    "extra_forbidden": "campo não permitido",
    "json_invalid": "JSON inválido",
    "value_error": "valor inválido",
}


def _field_path(loc: tuple) -> str:
    """['body', 'produto', '0'] → 'produto[0]'; ['body'] → 'dados'."""
    parts = [str(p) for p in loc]
    if parts and parts[0] in {"body", "query", "path", "header"}:
        parts = parts[1:]
    path = ""
    for part in parts:
        if part.isdigit():
            path += f"[{part}]"
        else:
            path = f"{path}.{part}" if path else part
    return path or "dados"


def register_error_handlers(app: FastAPI) -> None:
    """Registra handlers de erro globais."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """422 de validação no mesmo formato problem+json dos demais erros.

        Sem isso o FastAPI devolve `{"detail": [...]}` (lista) em
        application/json — o frontend lê `detail` como string e exibia
        "[object Object]" na tela.
        """
        request_id = getattr(request.state, "request_id", "unknown")
        errors = [
            {
                "field": _field_path(item.get("loc", ())),
                "type": item.get("type", "value_error"),
                "message": _VALIDATION_MESSAGES.get(
                    item.get("type", ""), item.get("msg", "valor inválido")
                ),
            }
            for item in exc.errors()
        ]
        detail = "; ".join(
            f"{err['field']}: {err['message']}" for err in errors
        ) or "Dados inválidos"
        logger.warning(
            "validation_error",
            errors=errors,
            path=request.url.path,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=422,
            content={
                "type": "https://syslink.com/errors/422",
                "title": "Validation Error",
                "status": 422,
                "detail": detail,
                "errors": errors,
                "instance": request_id,
            },
            media_type="application/problem+json",
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            "http_error",
            status=exc.status_code,
            detail=str(exc.detail),
            path=request.url.path,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"https://syslink.com/errors/{exc.status_code}",
                "title": "HTTP Error",
                "status": exc.status_code,
                "detail": str(exc.detail),
                "instance": request_id,
            },
            media_type="application/problem+json",
            # Encaminha headers do erro (ex.: Retry-After do 429).
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(ExternalServiceError)
    async def external_service_exception_handler(
        request: Request, exc: ExternalServiceError
    ) -> JSONResponse:
        """Serviço externo falhou (Resend, Apify…) → 502 com mensagem segura.

        `str(exc)` é SEGURA por contrato (docstring da exceção); o
        detalhe técnico fica no log. Sem este handler a exceção caía no
        genérico e virava 500 "erro interno" enganoso.
        """
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "external_service_error",
            error=str(exc),
            path=request.url.path,
            request_id=request_id,
            stack_trace=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=502,
            content={
                "type": "https://syslink.com/errors/502",
                "title": "Bad Gateway",
                "status": 502,
                "detail": str(exc),
                "instance": request_id,
            },
            media_type="application/problem+json",
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "unhandled_exception",
            error=str(exc),
            path=request.url.path,
            request_id=request_id,
            stack_trace=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={
                "type": "https://syslink.com/errors/500",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "Ocorreu um erro interno. Tente novamente.",
                "instance": request_id,
            },
            media_type="application/problem+json",
        )
