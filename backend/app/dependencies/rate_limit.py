"""Rate limit — janela deslizante de 60s, em memória (sem Redis).

Dois escopos:
- `rate_limit_auth` → por IP nos endpoints PÚBLICOS de auth (anti brute
  force). Balde único `auth:{ip}` compartilhado entre login/register/forgot/
  resend-confirmation/reset/confirm.
- `rate_limit_user` → por user_id nas rotas autenticadas (leads/escavador).

Notas de segurança:
- `X-Forwarded-For` só é lido quando `settings.trust_proxy_headers` é True
  (default False): sem proxy confiável, qualquer cliente forjaria o IP.
- `limit <= 0` desativa o limite (escape hatch de config).
- Estado em memória: zera no reinício do container e vale por processo
  (hoje há um único worker).
"""
import math
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Deque

from fastapi import Depends, Request

from app.config import settings
from app.dependencies.auth import get_current_user
from app.exceptions import RateLimitError
from app.models.user_model import User

WINDOW_SECONDS = 60


class RateLimiter:
    """Baldes de janela deslizante (timestamps das últimas 60s por chave)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    def _sweep(self, key: str, now: float) -> Deque[float]:
        """Descarta timestamps fora da janela (in-place, mantém a chave)."""
        bucket = self._hits[key]
        cutoff = now - WINDOW_SECONDS
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        return bucket

    def hit(self, key: str, limit: int) -> bool:
        """Registra uma tentativa. True = permitida; False = estourou o limite.

        Tentativas NEGADAS não são registradas (não estendem a janela).
        """
        if limit <= 0:
            return True  # limite desativado
        with self._lock:
            now = self._clock()
            bucket = self._sweep(key, now)
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def retry_after(self, key: str) -> int:
        """Segundos até a próxima tentativa ser liberada (>= 1)."""
        with self._lock:
            now = self._clock()
            bucket = self._sweep(key, now)
            if not bucket:
                # Janela inteira expirou → libera na hora.
                del self._hits[key]
                return 1
            remaining = bucket[0] + WINDOW_SECONDS - now
            return max(1, math.ceil(remaining))

    def reset(self) -> None:
        """Zera todos os baldes (usado entre testes)."""
        with self._lock:
            self._hits.clear()


# Singleton usado pelas dependências.
limiter = RateLimiter()


def _client_ip(request: Request) -> str:
    """IP do cliente — X-Forwarded-For só quando o proxy é confiável."""
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Primeiro hop da cadeia = cliente original.
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_auth(request: Request) -> None:
    """5 req/min por IP nos endpoints públicos de auth (padrão da settings)."""
    limit = settings.rate_limit_auth_per_minute
    if limit <= 0:
        return
    key = f"auth:{_client_ip(request)}"
    if not limiter.hit(key, limit):
        raise RateLimitError(limiter.retry_after(key))


async def rate_limit_user(
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    """100 req/min por user_id nas rotas autenticadas."""
    limit = settings.rate_limit_user_per_minute
    if limit <= 0:
        return
    key = f"user:{user.id}"
    if not limiter.hit(key, limit):
        raise RateLimitError(limiter.retry_after(key))
