#!/usr/bin/env python3
"""Vista previa del mail de recupero de carrito, armado con un carrito REAL de
pedidos_pendientes (precios y stock de hoy), enviado a un mail de prueba.

Uso:
  venv/bin/python scripts/enviar_preview_recupero.py <ref> <CUPON> --html          # solo genera el HTML y muestra el resumen
  venv/bin/python scripts/enviar_preview_recupero.py <ref> <CUPON> <email_destino> # además lo envía
  ... [--crear-cupon]   crea el cupón único RECU-XXXXXX copiando la plantilla CUPON (ESCRIBE en la base)

No escribe en la base. El saludo dice "Manu" (no usa el nombre del cliente) y el
mail va SOLO al destino indicado, nunca al cliente del carrito.
"""
import os
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')

if len(sys.argv) not in (4, 5):
    print(__doc__)
    sys.exit(2)
ref, cupon, dest = sys.argv[1], sys.argv[2].upper(), sys.argv[3]

import app as A  # noqa: E402
import tienda_bp as T  # noqa: E402
from flask import render_template  # noqa: E402

# CUPON es la plantilla (ej. RECUCYBER). Sin --crear-cupon se muestra la plantilla
# tal cual (no escribe nada); con --crear-cupon crea el cupón único RECU-XXXXXX (escribe en `cupones`).
crear = '--crear-cupon' in sys.argv
with A.app.test_request_context('/'):
    prep = T.preparar_mail_recupero(ref, cupon, crear_cupon=crear)
    if not prep:
        print('No aplica: el ref no existe, no tiene colchón/sommier disponible o la plantilla no sirve:', ref)
        sys.exit(1)
    r, link, vence = prep['r'], prep['link'], prep['vence']
    print('código del mail:', prep['codigo'], '(creado)' if crear else '(plantilla, sin crear)')
    html = render_template('tienda/email_recupero_carrito.html', r=r, nombre='Manu',
                           link=link, fp=T.format_price, vence=vence)

print('elegible:', r['elegible'], '| cupon:', r['cupon'] and r['cupon']['codigo'])
for i in r['items']:
    print(f"  {i['sku']:<10} x{i['cantidad']} {i['estado']:<9} lista={i['lista']} web={i['precio']} cupon={i['precio_cupon']}")
print('subtotal', r['subtotal'], 'desc', r['descuento'], 'total', r['total'],
      '| con cupón del evento', r['total_evento'], '| demora hasta', r['fecha_demora'])
print('link:', link[:90] + '...')
out = '/tmp/claude-0/-home-cannon-app/6af6f7bf-a427-4667-8ecc-26d880886eb1/scratchpad/recupero_preview.html'
try:
    open(out, 'w', encoding='utf-8').write(html)
    print('HTML en', out)
except Exception:
    pass

if dest == '--html':
    sys.exit(0)
if '@' not in dest:
    print('Destino inválido')
    sys.exit(2)

host = os.getenv('MAIL_SMTP_HOST', 'smtp.gmail.com')
port = int(os.getenv('MAIL_SMTP_PORT', '587'))
user = os.getenv('MAIL_SMTP_USER', '')
pwd = os.getenv('MAIL_SMTP_PASS', '')
frm = os.getenv('MAIL_FROM', user)
msg = MIMEMultipart('alternative')
msg['Subject'] = f"[PREVIEW] Manu, te guardamos el carrito{': ' + r['cupon']['label'].replace('-', '') + ' OFF' if r['cupon'] else ''}"
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
