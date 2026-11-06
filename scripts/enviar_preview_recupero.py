#!/usr/bin/env python3
"""Envía la VISTA PREVIA del mail de recupero de carrito (Cyber) a un mail de prueba.

Uso: venv/bin/python scripts/enviar_preview_recupero.py <email_destino>
Usa el SMTP de la tienda (config/.env). No toca la base. El carrito del mail es
de ejemplo (un producto con stock y otro con demora).
"""
import os
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv('/home/cannon/app/config/.env')
if len(sys.argv) != 2 or '@' not in sys.argv[1]:
    print(__doc__)
    sys.exit(2)
dest = sys.argv[1].strip()

html = open('/home/cannon/app/templates/emails_preview/recupero_carrito_cyber.html', encoding='utf-8').read()
html = html.replace('{{NOMBRE}}', 'Manu').replace(
    '{{LINK}}', 'https://www.mercadomuebles.com.ar/tienda/carrito?cupon=RECUCYBER')

host = os.getenv('MAIL_SMTP_HOST', 'smtp.gmail.com')
port = int(os.getenv('MAIL_SMTP_PORT', '587'))
user = os.getenv('MAIL_SMTP_USER', '')
pwd = os.getenv('MAIL_SMTP_PASS', '')
frm = os.getenv('MAIL_FROM', user)
if not user or not pwd:
    print('Falta MAIL_SMTP_USER / MAIL_SMTP_PASS')
    sys.exit(1)

msg = MIMEMultipart('alternative')
msg['Subject'] = '[PREVIEW] Manu, te guardamos el carrito: 7% OFF solo hasta el domingo'
msg['From'] = f'Mercadomuebles <{frm}>'
msg['To'] = dest
msg.attach(MIMEText(html, 'html', 'utf-8'))
if port == 465:
    with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context()) as s:
        s.login(user, pwd)
        s.send_message(msg)
else:
    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, pwd)
        s.send_message(msg)
print('Enviado a', dest)
