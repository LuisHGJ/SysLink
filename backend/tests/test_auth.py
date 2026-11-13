"""Testes de autenticação — registro, login, confirmação e recuperação (TDD).

Escrito ANTES da implementação. Fluxo coberto:
register → e-mail de confirmação (Resend) → confirm → login (JWT) → /me;
esqueci-senha → token → reset → login com a nova senha.
"""
import re
from datetime import datetime, timedelta, timezone

# ─── Helpers ──────────────────────────────────────────────────────
REGISTER_PAYLOAD = {"email": "novo@syslink.com", "password": "senha12345"}

LEAD_A = {
    "nome": "João Silva",
    "empresa": "Acme Corp",
    "contato": "joao@acme.com",
    "instagram": "@joaosilva",
    "produto": "Portfólio",
    "dificuldade": "Médio",
    "status": "Não contatado",
    "motivo_perda": None,
    "ultimo_contato": None,
    "arquivos": [],
}

LEAD_B = {
    "nome": "Maria Souza",
    "empresa": "Beta LLC",
    "contato": "5511999998888",
    "instagram": "@mariasouza",
    "produto": "Sistema",
    "dificuldade": "Fácil",
    "status": "Negociando",
    "motivo_perda": None,
    "ultimo_contato": None,
    "arquivos": [],
}


def _utcnow() -> datetime:
    """UTC sem tzinfo (mesmo formato persistido pelo SQLAlchemy)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _register(client, **overrides):
    payload = {**REGISTER_PAYLOAD, **overrides}
    return client.post("/api/v1/auth/register", json=payload)


def _token_from_email(sent_emails, index=-1):
    """Extrai o token do link contido no e-mail capturado."""
    html = sent_emails[index]["html"]
    match = re.search(r"token=([A-Za-z0-9_\-]+)", html)
    assert match, "e-mail enviado não contém link com token"
    return match.group(1)


def _register_and_confirm(client, sent_emails, **overrides):
    """Atalho: registra, lê o token do e-mail e confirma."""
    res = _register(client, **overrides)
    assert res.status_code == 201, res.text
    token = _token_from_email(sent_emails)
    res = client.post("/api/v1/auth/confirm", json={"token": token})
    assert res.status_code == 200, res.text


def _login(client, email, password):
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


# ─── Registro ─────────────────────────────────────────────────────
class TestRegister:
    def test_register_success(self, unauth_client, sent_emails):
        """POST /api/v1/auth/register → 201 com mensagem (sem senha/hash)."""
        res = _register(unauth_client)
        assert res.status_code == 201
        body = res.json()
        assert "message" in body
        assert "password" not in str(body).lower()
        assert "hash" not in str(body).lower()

    def test_register_sends_confirmation_email(self, unauth_client, sent_emails):
        """Cadastro deve disparar 1 e-mail de confirmação com link + token."""
        _register(unauth_client)
        assert len(sent_emails) == 1
        assert sent_emails[0]["to"] == "novo@syslink.com"
        assert "token=" in sent_emails[0]["html"]

    def test_register_duplicate_email(self, unauth_client):
        """E-mail já cadastrado → 409."""
        _register(unauth_client)
        res = _register(unauth_client)
        assert res.status_code == 409

    def test_register_invalid_email(self, unauth_client):
        """E-mail fora do formato → 422 problem+json."""
        res = _register(unauth_client, email="nao-e-email")
        assert res.status_code == 422
        assert res.headers["content-type"] == "application/problem+json"

    def test_register_short_password(self, unauth_client):
        """Senha com menos de 8 caracteres → 422."""
        res = _register(unauth_client, password="123")
        assert res.status_code == 422

    def test_register_extra_field_rejected(self, unauth_client):
        """Campo extra (ex.: admin) → 422 (extra=forbid)."""
        res = unauth_client.post(
            "/api/v1/auth/register", json={**REGISTER_PAYLOAD, "admin": True}
        )
        assert res.status_code == 422

    def test_register_normalizes_email(self, unauth_client, sent_emails):
        """E-mail deve ser normalizado (minúsculo) no cadastro e no envio."""
        _register(unauth_client, email="NOVO@SYSLINK.COM")
        assert sent_emails[0]["to"] == "novo@syslink.com"


# ─── Confirmação de e-mail ────────────────────────────────────────
class TestConfirmEmail:
    def test_confirm_success_enables_login(self, unauth_client, sent_emails):
        """Token válido → 200 e o login passa a funcionar."""
        _register(unauth_client)
        token = _token_from_email(sent_emails)
        res = unauth_client.post("/api/v1/auth/confirm", json={"token": token})
        assert res.status_code == 200
        assert _login(unauth_client, **REGISTER_PAYLOAD).status_code == 200

    def test_confirm_invalid_token(self, unauth_client):
        """Token inexistente → 400 problem+json."""
        res = unauth_client.post(
            "/api/v1/auth/confirm", json={"token": "token-invalido"}
        )
        assert res.status_code == 400
        assert res.headers["content-type"] == "application/problem+json"

    def test_confirm_expired_token(self, unauth_client, sent_emails, db_session):
        """Token expirado → 400."""
        from app.models.user_model import User

        _register(unauth_client)
        token = _token_from_email(sent_emails)
        user = db_session.query(User).filter_by(email="novo@syslink.com").one()
        user.verification_expires_at = _utcnow() - timedelta(hours=1)
        db_session.commit()
        res = unauth_client.post("/api/v1/auth/confirm", json={"token": token})
        assert res.status_code == 400

    def test_confirm_token_is_single_use(self, unauth_client, sent_emails):
        """Token consumido não pode ser reutilizado → 400 na 2ª vez."""
        _register(unauth_client)
        token = _token_from_email(sent_emails)
        assert (
            unauth_client.post(
                "/api/v1/auth/confirm", json={"token": token}
            ).status_code
            == 200
        )
        res = unauth_client.post("/api/v1/auth/confirm", json={"token": token})
        assert res.status_code == 400

    def test_resend_confirmation_sends_new_email(self, unauth_client, sent_emails):
        """Reenviar confirmação para conta pendente → 202 + novo e-mail."""
        _register(unauth_client)
        before = len(sent_emails)
        res = unauth_client.post(
            "/api/v1/auth/resend-confirmation",
            json={"email": "novo@syslink.com"},
        )
        assert res.status_code == 202
        assert len(sent_emails) == before + 1

    def test_resend_confirmation_unknown_email_is_generic(
        self, unauth_client, sent_emails
    ):
        """E-mail inexistente → 202 genérico, SEM e-mail (anti-enumeration)."""
        res = unauth_client.post(
            "/api/v1/auth/resend-confirmation",
            json={"email": "ninguem@syslink.com"},
        )
        assert res.status_code == 202
        assert len(sent_emails) == 0


# ─── Login ────────────────────────────────────────────────────────
class TestLogin:
    def test_login_success_returns_token(self, unauth_client, sent_emails):
        """Credenciais válidas → 200 com access_token JWT."""
        _register_and_confirm(unauth_client, sent_emails)
        res = _login(unauth_client, **REGISTER_PAYLOAD)
        assert res.status_code == 200
        body = res.json()
        assert body["access_token"]
        assert body["token_type"] == "bearer"

    def test_login_token_works_on_me(self, unauth_client, sent_emails):
        """Token do login autentica GET /api/v1/auth/me."""
        _register_and_confirm(unauth_client, sent_emails)
        token = _login(unauth_client, **REGISTER_PAYLOAD).json()["access_token"]
        res = unauth_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        assert res.json()["email"] == "novo@syslink.com"

    def test_login_wrong_password(self, unauth_client, sent_emails):
        """Senha errada → 401 problem+json."""
        _register_and_confirm(unauth_client, sent_emails)
        res = _login(unauth_client, email="novo@syslink.com", password="senhaErrada")
        assert res.status_code == 401
        assert res.headers["content-type"] == "application/problem+json"

    def test_login_unknown_email_same_message(self, unauth_client, sent_emails):
        """E-mail inexistente e senha errada devolvem a MESMA mensagem.

        Evita enumeração de contas por meio das respostas do login.
        """
        _register_and_confirm(unauth_client, sent_emails)
        wrong_pass = _login(
            unauth_client, email="novo@syslink.com", password="senhaErrada"
        ).json()["detail"]
        unknown = _login(
            unauth_client, email="outro@syslink.com", password="senhaErrada"
        ).json()["detail"]
        assert wrong_pass == unknown == "E-mail ou senha incorretos"

    def test_login_unverified_email_blocked(self, unauth_client):
        """Conta sem confirmar o e-mail → 403 com instrução de confirmação."""
        _register(unauth_client)
        res = _login(unauth_client, **REGISTER_PAYLOAD)
        assert res.status_code == 403
        assert "confirm" in res.json()["detail"].lower()

    def test_login_missing_password(self, unauth_client):
        """Campo obrigatório ausente → 422."""
        res = unauth_client.post(
            "/api/v1/auth/login", json={"email": "novo@syslink.com"}
        )
        assert res.status_code == 422


# ─── /me e proteção das rotas ─────────────────────────────────────
class TestProtectedRoutes:
    def test_me_returns_current_user(self, client):
        """GET /auth/me com token válido → dados do usuário logado."""
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 200
        body = res.json()
        assert body["email"] == "tester@syslink.com"
        assert body["email_verified"] is True
        assert "password_hash" not in body

    def test_me_without_token(self, unauth_client):
        """Sem Authorization → 401 problem+json."""
        res = unauth_client.get("/api/v1/auth/me")
        assert res.status_code == 401
        assert res.headers["content-type"] == "application/problem+json"

    def test_me_invalid_token(self, unauth_client):
        """Token forjado → 401."""
        res = unauth_client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer xxx.yyy.zzz"}
        )
        assert res.status_code == 401

    def test_me_malformed_header(self, unauth_client):
        """Esquema != Bearer → 401."""
        res = unauth_client.get(
            "/api/v1/auth/me", headers={"Authorization": "Token abc"}
        )
        assert res.status_code == 401

    def test_me_expired_token(self, unauth_client):
        """Token expirado → 401."""
        from jose import jwt

        from app.config import settings

        exp = datetime.now(timezone.utc) - timedelta(minutes=5)
        token = jwt.encode(
            {"sub": "1", "exp": int(exp.timestamp())},
            settings.secret_key,
            algorithm="HS256",
        )
        res = unauth_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 401

    def test_leads_require_auth(self, unauth_client):
        """GET /leads sem token → 401 (rotas existentes protegidas)."""
        res = unauth_client.get("/api/v1/leads")
        assert res.status_code == 401

    def test_lead_create_requires_auth(self, unauth_client):
        """POST /leads sem token → 401."""
        res = unauth_client.post("/api/v1/leads", json=LEAD_A)
        assert res.status_code == 401

    def test_lead_delete_requires_auth(self, unauth_client):
        """DELETE /leads/{id} sem token → 401."""
        res = unauth_client.delete("/api/v1/leads/1")
        assert res.status_code == 401

    def test_excavate_requires_auth(self, unauth_client):
        """POST /excavate sem token → 401 (gasta Apify — protegido)."""
        res = unauth_client.post(
            "/api/v1/excavate", json={"nicho": "restaurantes", "quantidade": 1}
        )
        assert res.status_code == 401

    def test_embed_requires_auth(self, unauth_client):
        """POST /embed sem token → 401."""
        res = unauth_client.post("/api/v1/embed", json={"text": "oi"})
        assert res.status_code == 401


# ─── Isolamento de leads por usuário ──────────────────────────────
class TestLeadIsolation:
    def test_users_see_only_their_own_leads(self, client, make_user):
        """Cada usuário lista apenas os leads criados por ele."""
        client.post("/api/v1/leads", json=LEAD_A)
        headers_b = make_user("outra@syslink.com")
        client.post("/api/v1/leads", json=LEAD_B, headers=headers_b)

        res_a = client.get("/api/v1/leads")
        assert [lead["nome"] for lead in res_a.json()] == ["João Silva"]

        res_b = client.get("/api/v1/leads", headers=headers_b)
        assert [lead["nome"] for lead in res_b.json()] == ["Maria Souza"]

    def test_cannot_read_other_users_lead(self, client, make_user):
        """GET /leads/{id} de outro usuário → 404 (não vaza existência)."""
        created = client.post("/api/v1/leads", json=LEAD_A)
        lead_id = created.json()["id"]
        headers_b = make_user("outra@syslink.com")
        res = client.get(f"/api/v1/leads/{lead_id}", headers=headers_b)
        assert res.status_code == 404

    def test_cannot_delete_other_users_lead(self, client, make_user):
        """DELETE de lead alheio → 404 e o lead continua intacto."""
        created = client.post("/api/v1/leads", json=LEAD_A)
        lead_id = created.json()["id"]
        headers_b = make_user("outra@syslink.com")
        res = client.delete(f"/api/v1/leads/{lead_id}", headers=headers_b)
        assert res.status_code == 404
        assert client.get(f"/api/v1/leads/{lead_id}").status_code == 200

    def test_instagram_dedup_is_per_user(self, client, make_user):
        """Mesmo Instagram de outro usuário NÃO é tratado como duplicata."""
        client.post("/api/v1/leads", json=LEAD_A)
        headers_b = make_user("outra@syslink.com")
        res = client.post("/api/v1/leads", json=LEAD_A, headers=headers_b)
        assert res.status_code == 201
        assert res.json()["nome"] == "João Silva"  # criado, não reutilizado
        res_b = client.get("/api/v1/leads", headers=headers_b)
        assert len(res_b.json()) == 1


# ─── Esqueci a senha ──────────────────────────────────────────────
class TestForgotPassword:
    def test_forgot_existing_email_sends_token(self, unauth_client, sent_emails):
        """Conta existente → 202 + e-mail com link de redefinição."""
        _register_and_confirm(unauth_client, sent_emails)
        res = unauth_client.post(
            "/api/v1/auth/forgot", json={"email": "novo@syslink.com"}
        )
        assert res.status_code == 202
        assert "token=" in sent_emails[-1]["html"]

    def test_forgot_unknown_email_is_generic(self, unauth_client, sent_emails):
        """E-mail inexistente → 202 com a MESMA mensagem e sem e-mail."""
        res = unauth_client.post(
            "/api/v1/auth/forgot", json={"email": "naoexiste@syslink.com"}
        )
        assert res.status_code == 202
        assert len(sent_emails) == 0

    def test_forgot_same_response_for_existing_and_unknown(
        self, unauth_client, sent_emails
    ):
        """Resposta idêntica nos dois casos → não revela quem tem conta."""
        _register_and_confirm(unauth_client, sent_emails)
        known = unauth_client.post(
            "/api/v1/auth/forgot", json={"email": "novo@syslink.com"}
        ).json()
        unknown = unauth_client.post(
            "/api/v1/auth/forgot", json={"email": "naoexiste@syslink.com"}
        ).json()
        assert known == unknown

    def test_forgot_invalid_email(self, unauth_client):
        """E-mail fora do formato → 422."""
        res = unauth_client.post("/api/v1/auth/forgot", json={"email": "xxx"})
        assert res.status_code == 422


# ─── Redefinição de senha ─────────────────────────────────────────
class TestResetPassword:
    def test_reset_success_and_old_password_dies(
        self, unauth_client, sent_emails
    ):
        """Token válido → 200; nova senha loga, antiga não."""
        _register_and_confirm(unauth_client, sent_emails)
        unauth_client.post(
            "/api/v1/auth/forgot", json={"email": "novo@syslink.com"}
        )
        token = _token_from_email(sent_emails)
        res = unauth_client.post(
            "/api/v1/auth/reset",
            json={"token": token, "password": "novaSenha123"},
        )
        assert res.status_code == 200

        assert (
            _login(
                unauth_client, email="novo@syslink.com", password="novaSenha123"
            ).status_code
            == 200
        )
        assert (
            _login(
                unauth_client, email="novo@syslink.com", password="senha12345"
            ).status_code
            == 401
        )

    def test_reset_token_is_single_use(self, unauth_client, sent_emails):
        """Mesmo token não redefini a senha duas vezes → 400 na 2ª."""
        _register_and_confirm(unauth_client, sent_emails)
        unauth_client.post(
            "/api/v1/auth/forgot", json={"email": "novo@syslink.com"}
        )
        token = _token_from_email(sent_emails)
        payload = {"token": token, "password": "novaSenha123"}
        assert unauth_client.post("/api/v1/auth/reset", json=payload).status_code == 200
        res = unauth_client.post("/api/v1/auth/reset", json=payload)
        assert res.status_code == 400

    def test_reset_invalid_token(self, unauth_client):
        """Token inexistente → 400 problem+json."""
        res = unauth_client.post(
            "/api/v1/auth/reset",
            json={"token": "token-invalido", "password": "novaSenha123"},
        )
        assert res.status_code == 400
        assert res.headers["content-type"] == "application/problem+json"

    def test_reset_expired_token(self, unauth_client, sent_emails, db_session):
        """Token de redefinição expirado → 400."""
        from app.models.user_model import User

        _register_and_confirm(unauth_client, sent_emails)
        unauth_client.post(
            "/api/v1/auth/forgot", json={"email": "novo@syslink.com"}
        )
        token = _token_from_email(sent_emails)
        user = db_session.query(User).filter_by(email="novo@syslink.com").one()
        user.reset_expires_at = _utcnow() - timedelta(minutes=1)
        db_session.commit()
        res = unauth_client.post(
            "/api/v1/auth/reset",
            json={"token": token, "password": "novaSenha123"},
        )
        assert res.status_code == 400

    def test_reset_short_password(self, unauth_client):
        """Nova senha com menos de 8 caracteres → 422 (schema)."""
        res = unauth_client.post(
            "/api/v1/auth/reset", json={"token": "qualquer", "password": "123"}
        )
        assert res.status_code == 422


# ─── Falha no envio de e-mail (Resend fora do ar / recusado) ──────
class TestEmailSendFailure:
    def test_register_email_failure_returns_502(self, unauth_client, monkeypatch):
        """Envio falha (ex.: Resend 403) → 502 problem+json com detail SEGURO.

        O texto da exceção vira `detail` (PT-BR, sem detalhes técnicos);
        o corpo cru da API fica só no log. A conta é criada ANTES do
        envio → o retry não duplica o cadastro (409), e a recuperação
        é via /resend-confirmation.
        """
        from app.exceptions import ExternalServiceError
        from app.services import email_service

        async def _fail(to, subject, html):
            raise ExternalServiceError(
                "Não foi possível enviar o e-mail. Tente novamente."
            )

        monkeypatch.setattr(email_service, "send_email", _fail)
        res = _register(unauth_client)
        assert res.status_code == 502
        assert res.headers["content-type"] == "application/problem+json"
        body = res.json()
        assert body["status"] == 502
        assert "Não foi possível enviar o e-mail" in body["detail"]
        # conta já existe → novo POST /register devolve 409 (não recria)
        assert _register(unauth_client).status_code == 409

    def test_forgot_email_failure_returns_502(self, unauth_client, monkeypatch):
        """/forgot com envio falhando → 502 (não 500 genérico)."""
        from app.exceptions import ExternalServiceError
        from app.services import email_service

        async def _fail(to, subject, html):
            raise ExternalServiceError(
                "Não foi possível enviar o e-mail. Tente novamente."
            )

        monkeypatch.setattr(email_service, "send_email", _fail)
        _register(unauth_client)  # cria a conta (envio falha, mas ok)
        monkeypatch.setattr(email_service, "send_email", _fail)
        res = unauth_client.post(
            "/api/v1/auth/forgot", json={"email": "novo@syslink.com"}
        )
        assert res.status_code == 502
        assert res.headers["content-type"] == "application/problem+json"


# ─── Modo dev sem Resend (link de confirmação no log) ─────────────
class TestDevModeWithoutResend:
    def test_register_logs_confirmation_link_when_resend_disabled(
        self, unauth_client, monkeypatch
    ):
        """Sem RESEND configurado → o link de confirmação vai para o LOG.

        Em dev sem chave o e-mail nunca sai; sem este fallback o usuário
        ficaria preso (conta criada, sem token, sem como confirmar).
        """
        import structlog.testing

        from app.config import settings

        monkeypatch.setattr(settings, "resend_api_key", "")
        monkeypatch.setattr(settings, "resend_from", "")

        with structlog.testing.capture_logs() as cap_logs:
            res = _register(unauth_client)

        assert res.status_code == 201
        entry = next(
            (e for e in cap_logs if e["event"] == "verification_link_dev_only"),
            None,
        )
        assert entry is not None, "link de confirmação não foi logado"
        assert "/confirmar?token=" in entry["link"]

    def test_no_link_in_log_when_resend_is_configured(
        self, unauth_client, sent_emails, monkeypatch
    ):
        """Com Resend configurado o link NÃO vaza para o log (só o e-mail)."""
        import structlog.testing

        from app.config import settings

        monkeypatch.setattr(settings, "resend_api_key", "re_chave_teste")
        monkeypatch.setattr(settings, "resend_from", "SysLink <no-reply@t.com>")

        with structlog.testing.capture_logs() as cap_logs:
            res = _register(unauth_client)

        assert res.status_code == 201
        assert not any(
            e["event"] == "verification_link_dev_only" for e in cap_logs
        )
