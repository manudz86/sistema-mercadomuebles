#!/usr/bin/env python3
"""Prueba de SOLO LECTURA de la casilla IMAP (Hostinger) para los mails de recolección de Zipnova.
Abre las carpetas en modo readonly y baja los mensajes con BODY.PEEK (no los marca como leídos,
no mueve ni borra nada). Guarda los PDF adjuntos en reportes/zipnova_recolecciones/ y muestra
su texto.

Uso: venv/bin/python scripts/diag_zipnova_mail.py [desde DD-Mon-YYYY, ej 10-Nov-2026]
"""
import email
import imaplib
import os
import sys
from email.header import decode_header, make_header

from dotenv import load_dotenv

load_dotenv('/home/cannon/app/config/.env')
HOST = os.getenv('ZIPNOVA_IMAP_HOST', 'imap.hostinger.com')
USER = os.getenv('ZIPNOVA_IMAP_USER', '')
PASS = os.getenv('ZIPNOVA_IMAP_PASS', '')
DESDE = sys.argv[1] if len(sys.argv) > 1 else '10-Nov-2026'
VER_CUERPO = sys.argv[2] if len(sys.argv) > 2 else ''   # texto del asunto cuyo cuerpo mostrar
SALIDA = '/home/cannon/app/reportes/zipnova_recolecciones'

if not USER or not PASS:
    sys.exit('Faltan ZIPNOVA_IMAP_USER / ZIPNOVA_IMAP_PASS en config/.env')

M = imaplib.IMAP4_SSL(HOST, 993)
try:
    M.login(USER, PASS)
except imaplib.IMAP4.error as e:
    sys.exit(f'Login rechazado: {e}')
print('Login OK en', HOST)
typ, carpetas = M.list()
nombres = []
for c in carpetas or []:
    linea = c.decode(errors='replace')
    nombre = linea.split(' "/" ')[-1].split(' "." ')[-1].strip().strip('"')
    nombres.append(nombre)
print('Carpetas:', nombres)

os.makedirs(SALIDA, exist_ok=True)
for carpeta in nombres:
    typ, _ = M.select(f'"{carpeta}"', readonly=True)
    if typ != 'OK':
        continue
    typ, data = M.search(None, 'FROM', '"zipnova"', 'SINCE', DESDE)
    ids = (data[0] or b'').split()
    if not ids:
        continue
    print(f'\n[{carpeta}] {len(ids)} mail(s) de Zipnova desde {DESDE}')
    for i in ids:
        typ, msg_data = M.fetch(i, '(BODY.PEEK[])')
        msg = email.message_from_bytes(msg_data[0][1])
        asunto = str(make_header(decode_header(msg.get('Subject', ''))))
        print(f"  - {msg.get('Date')} | {msg.get('From')} | {asunto}")
        if VER_CUERPO and VER_CUERPO.lower() in asunto.lower():
            import html as _h
            import re as _re
            for parte in msg.walk():
                if parte.get_content_type() in ('text/plain', 'text/html'):
                    t = parte.get_payload(decode=True).decode(parte.get_content_charset() or 'utf-8', 'replace')
                    if parte.get_content_type() == 'text/html' or '<html' in t.lower():
                        t = _re.sub(r'<(style|script)[^>]*>.*?</\1>', ' ', t, flags=_re.S | _re.I)
                        t = _h.unescape(_re.sub(r'<[^>]+>', ' ', t))
                    print('      CUERPO:', _re.sub(r'\s+', ' ', t)[:2500])
                    break
        for parte in msg.walk():
            fn = parte.get_filename()
            if not fn:
                continue
            fn = str(make_header(decode_header(fn)))
            if not fn.lower().endswith('.pdf'):
                continue
            ruta = os.path.join(SALIDA, fn)
            with open(ruta, 'wb') as fh:
                fh.write(parte.get_payload(decode=True))
            print(f'      adjunto guardado: {ruta} ({os.path.getsize(ruta)} bytes)')
M.logout()
