#!/usr/bin/env python3
"""SOLO LECTURA: busca en la casilla IMAP (la misma de Zipnova, contacto@) el último
mail de Real Trends con el código de login y muestra asunto, fecha y el código.
No marca como leído (BODY.PEEK), no mueve ni borra nada.

Uso: venv/bin/python scripts/diag_rt_mail_codigo.py [desde DD-Mon-YYYY]
"""
import email
import html
import imaplib
import os
import re
import sys
from datetime import date
from email.header import decode_header, make_header

from dotenv import load_dotenv

load_dotenv('/home/cannon/app/config/.env')
HOST = os.getenv('ZIPNOVA_IMAP_HOST', 'imap.hostinger.com')
USER = os.getenv('ZIPNOVA_IMAP_USER', '')
PASS = os.getenv('ZIPNOVA_IMAP_PASS', '')
DESDE = sys.argv[1] if len(sys.argv) > 1 else date.today().strftime('%d-%b-%Y')


def _texto(msg):
    partes = []
    for p in msg.walk():
        ct = p.get_content_type()
        if ct in ('text/plain', 'text/html'):
            try:
                t = p.get_payload(decode=True).decode(p.get_content_charset() or 'utf-8', errors='replace')
            except Exception:
                continue
            if ct == 'text/html':
                t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
            partes.append(t)
    return re.sub(r'\s+', ' ', ' '.join(partes))


M = imaplib.IMAP4_SSL(HOST, 993, timeout=60)
M.login(USER, PASS)
encontrados = []
for carpeta in ('INBOX', 'INBOX.Spam', 'INBOX.Junk', 'Spam', 'Junk'):
    typ, _ = M.select(f'"{carpeta}"', readonly=True)
    if typ != 'OK':
        continue
    typ, data = M.search(None, 'SINCE', DESDE)
    for num in (data[0] or b'').split():
        typ, hd = M.fetch(num, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])')
        h = email.message_from_bytes(hd[0][1])
        de = str(make_header(decode_header(h.get('From', ''))))
        asunto = str(make_header(decode_header(h.get('Subject', ''))))
        if 'real' not in (de + asunto).lower() and 'market pro' not in (de + asunto).lower():
            continue
        typ, full = M.fetch(num, '(BODY.PEEK[])')
        txt = _texto(email.message_from_bytes(full[0][1]))
        codigos = re.findall(r'\b\d{6}\b', txt) or re.findall(r'\b[A-Z0-9]{6,8}\b', txt)
        encontrados.append((h.get('Date'), carpeta, de, asunto, codigos[:3], txt[:300]))
M.logout()

if not encontrados:
    print(f'No hay mails de Real Trends desde {DESDE}.')
for d, c, de, a, cods, txt in encontrados:
    print(f'{d} [{c}] {de} | {a}\n   códigos: {cods}\n   texto: {txt}\n')
