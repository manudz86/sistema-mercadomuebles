"""
scraper_alerts.py
Módulo para enviar alertas de fallas del scraper de competencia por email.
Reutiliza la config SMTP existente en config/.env.
"""
import os, smtplib, ssl
from email.message import EmailMessage
from datetime import datetime, timezone, timedelta

# Buenos Aires: GMT-3, sin DST
TZ_BSAS = timezone(timedelta(hours=-3))


def enviar_alerta(asunto, cuerpo, destinatario=None):
    """Envía un mail de alerta. Devuelve (ok, mensaje_de_error)."""
    host = os.environ.get('MAIL_SMTP_HOST')
    port = int(os.environ.get('MAIL_SMTP_PORT', '465'))
    user = os.environ.get('MAIL_SMTP_USER')
    pwd  = os.environ.get('MAIL_SMTP_PASS')
    sender = os.environ.get('MAIL_FROM', user)
    dest = destinatario or os.environ.get('MAIL_VENDEDOR') or user

    if not (host and user and pwd):
        return False, 'SMTP no configurado'

    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From']    = sender
    msg['To']      = dest
    msg.set_content(cuerpo)

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as s:
            s.login(user, pwd)
            s.send_message(msg)
        return True, None
    except Exception as e:
        return False, str(e)


def alerta_falla_scraper(motivo, detalle=''):
    """Helper específico para fallas del scraper de competencia."""
    ts = datetime.now(TZ_BSAS).strftime('%Y-%m-%d %H:%M')
    asunto = f'[Sistema Cannon] Falla scraper competencia ({ts})'
    cuerpo = (
        f'Falló el scraper automático de competencia.\n\n'
        f'Fecha: {ts}\n'
        f'Motivo: {motivo}\n\n'
        f'Detalle:\n{detalle or "(sin detalle adicional)"}\n\n'
        f'El próximo intento es en 1 hora. Si vuelve a fallar, '
        f'recibirás otro mail.\n\n'
        f'Para revisar manualmente, mirá el log: '
        f'C:\\Users\\manud\\Downloads\\scraper.log\n'
    )
    return enviar_alerta(asunto, cuerpo)
