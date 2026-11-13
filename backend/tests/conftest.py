"""Fixtures compartilhadas de teste — SQLite em memória.

Convenção de autenticação:
- `client` → AUTENTICADO (usuário padrão tester@syslink.com, já confirmado).
  Testes de CRUD usam `client` direto, sem gastar linhas com header.
- `unauth_client` → SEM token — para testar 401 e os fluxos de auth.
- `make_user(email)` → factory que cria outro usuário e devolve os headers
  Authorization dele (testes de isolamento entre usuários).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# SQLite em memória para testes
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

DEFAULT_EMAIL = "tester@syslink.com"
DEFAULT_PASSWORD = "senha12345"

# Hash do bcrypt é caro (~200ms); como todos os usuários de teste usam a
# mesma senha, o hash é computado uma vez e reaproveitado.
_HASH_CACHE: dict[str, str] = {}


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _fast_hash(password: str) -> str:
    if password not in _HASH_CACHE:
        from app.services.auth_service import hash_password

        _HASH_CACHE[password] = hash_password(password)
    return _HASH_CACHE[password]


def _seed_user(email: str, password: str = DEFAULT_PASSWORD) -> str:
    """Cria usuário já verificado no banco de teste e devolve um JWT."""
    from app.models.user_model import User
    from app.services.auth_service import create_access_token

    db = TestingSessionLocal()
    try:
        user = User(
            email=email,
            password_hash=_fast_hash(password),
            email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return create_access_token(user.id)
    finally:
        db.close()


def _begin() -> None:
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db


def _end() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _relaxed_rate_limits(monkeypatch):
    """Suíte: relaxa os rate limits e zera o limiter entre testes.

    Os testes de rate limit (test_rate_limit.py) rebaixam os limites com o
    MESMO monkeypatch depois — o valor do teste, aplicado por último, vence.
    """
    from app.config import settings
    from app.dependencies.rate_limit import limiter

    monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 100_000)
    monkeypatch.setattr(settings, "rate_limit_user_per_minute", 100_000)
    limiter.reset()


@pytest.fixture(autouse=True)
def _offline_tavily(monkeypatch):
    """Suíte: nunca chama a Tavily de verdade (rede) sem o teste pedir.

    Testes do Tavily reativam a chave com o MESMO monkeypatch depois —
    o valor do teste, aplicado por último, vence.
    """
    from app.config import settings

    monkeypatch.setattr(settings, "tavily_api_key", "")


@pytest.fixture()
def client() -> TestClient:
    """Client de teste AUTENTICADO com usuário padrão (tester@syslink.com)."""
    _begin()
    token = _seed_user(DEFAULT_EMAIL)
    with TestClient(app) as c:
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c
    _end()


@pytest.fixture()
def unauth_client() -> TestClient:
    """Client de teste SEM token — fluxos de auth e asserções de 401."""
    _begin()
    with TestClient(app) as c:
        yield c
    _end()


@pytest.fixture()
def db_session(client):
    """Sessão do banco de teste — para ajustar dados entre requests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def sent_emails(monkeypatch):
    """Substitui o envio real (Resend) e captura o que seria enviado."""
    from app.services import email_service

    sent: list[dict] = []

    async def _capture(to: str, subject: str, html: str) -> None:
        sent.append({"to": to, "subject": subject, "html": html})

    monkeypatch.setattr(email_service, "send_email", _capture)
    return sent


@pytest.fixture()
def make_user(client):
    """Factory: cria usuário verificado e devolve os headers Authorization."""

    def _make(email: str, password: str = DEFAULT_PASSWORD) -> dict:
        token = _seed_user(email, password)
        return {"Authorization": f"Bearer {token}"}

    return _make
