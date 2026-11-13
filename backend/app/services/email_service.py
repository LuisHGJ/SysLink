"""Envio de e-mails transacionais via API do Resend.

Variáveis: RESEND_API_KEY (chave da conta) e RESEND_FROM (remetente).
Sem chave configurada o envio é IGNORADO com warning — permite rodar
o fluxo de cadastro em dev antes da chave existir.
"""
import httpx

from app.config import settings
from app.exceptions import ExternalServiceError
from app.logging_config import get_logger

logger = get_logger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def emails_configured() -> bool:
    """True quando o Resend está pronto para enviar de verdade."""
    return bool(settings.resend_api_key and settings.resend_from)


async def send_email(to: str, subject: str, html: str) -> None:
    """Envia um e-mail HTML. Falha de rede/API → ExternalServiceError (502)."""
    if not emails_configured():
        logger.warning("email_skipped", reason="RESEND não configurado", to=to)
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.resend_from,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        # Corpo cru (com detalhes da API) fica só no log.
        logger.error("email_send_failed", to=to, error=str(exc))
        raise ExternalServiceError(
            "Não foi possível enviar o e-mail. Tente novamente."
        ) from exc

    logger.info("email_sent", to=to, subject=subject)


async def send_verification_email(to: str, token: str) -> None:
    """E-mail de confirmação de cadastro (link com token de uso único)."""
    link = f"{settings.frontend_url}/confirmar?token={token}"
    await send_email(
        to,
        "Confirme seu e-mail — SysLink",
        f"""<html><body style="font-family:sans-serif;color:#18181b;">
<h2>Confirme seu e-mail</h2>
<p>Olá! Para ativar sua conta no SysLink, clique no botão abaixo:</p>
<p>
  <a href="{link}"
     style="background:#10b981;color:#fff;padding:10px 16px;
            border-radius:6px;text-decoration:none;display:inline-block;">
    Confirmar e-mail
  </a>
</p>
<p>Ou copie e cole este link no navegador:<br>{link}</p>
<p>Se você não criou esta conta, ignore este e-mail.</p>
</body></html>""",
    )
    if not emails_configured():
        # Modo dev: sem Resend o envio é ignorado — logar o link permite
        # concluir a confirmação sem servidor de e-mail real.
        logger.warning("verification_link_dev_only", link=link)


async def send_password_reset_email(to: str, token: str) -> None:
    """E-mail de recuperação de senha (link com token de uso único)."""
    link = f"{settings.frontend_url}/redefinir-senha?token={token}"
    await send_email(
        to,
        "Recuperação de senha — SysLink",
        f"""<html><body style="font-family:sans-serif;color:#18181b;">
<h2>Recuperação de senha</h2>
<p>Recebemos uma solicitação para redefinir sua senha. Clique abaixo:</p>
<p>
  <a href="{link}"
     style="background:#10b981;color:#fff;padding:10px 16px;
            border-radius:6px;text-decoration:none;display:inline-block;">
    Redefinir senha
  </a>
</p>
<p>Ou copie e cole este link no navegador:<br>{link}</p>
<p>Este link expira em 1 hora. Se você não pediu isso, ignore este e-mail.</p>
</body></html>""",
    )
    if not emails_configured():
        logger.warning("reset_link_dev_only", link=link)
