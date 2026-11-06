#!/usr/bin/env python3
"""Mail de recupero de carrito a los clientes con carrito abandonado de un período.

Uso:
  venv/bin/python scripts/enviar_recupero_masivo.py "2026-11-02 00:00" "2026-11-05 23:59:59" RECUCYBER            # PREVIEW: lista a quién, no escribe ni envía
  venv/bin/python scripts/enviar_recupero_masivo.py "2026-11-02 00:00" "2026-11-05 23:59:59" RECUCYBER --enviar   # crea 1 cupón RECU- por cliente y envía

Selección (igual que analizar_abandonados_periodo.py): clientes (por email) con
pedido pendiente en el período (hora AR), que NO compraron después (email o DNI en
ventas) y cuyo carrito tiene colchón o sommier. Por cliente se usa su pedido
pendiente MÁS RECIENTE del período que sea elegible HOY (precios/stock de hoy).

Al enviar, cada envío queda en data/recupero_enviados.jsonl: si se vuelve a
correr, a quien ya se le mandó NO se le manda de nuevo.
"""
import json
import os
import smtplib
import ssl
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
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
ENVIAR = len(sys.argv) == 5 and sys.argv[4] == '--enviar'
plantilla = sys.argv[3].upper()
fmt = '%Y-%m-%d %H:%M:%S'


def parse(s):
    s = s.strip()
    return datetime.strptime(s if len(s) > 16 else s + ':00', fmt)


desde_ar, hasta_ar = parse(sys.argv[1]), parse(sys.argv[2])
desde_utc, hasta_utc = desde_ar + timedelta(hours=3), hasta_ar + timedelta(hours=3)
LOG = '/home/cannon/app/data/recupero_enviados.jsonl'

import app as A  # noqa: E402
import tienda_bp as T  # noqa: E402
from flask import render_template  # noqa: E402

ya_enviados = set()
if os.path.exists(LOG):
    for line in open(LOG, encoding='utf-8'):
        try:
            ya_enviados.add(json.loads(line)['email'])
        except Exception:
            pass


def primer_nombre(n):
    n = (n or '').strip().split()
    # Si cargó el mail o algo raro como nombre, saludo genérico.
    if not n or '@' in n[0] or any(ch.isdigit() for ch in n[0]):
        return 'Hola'
    return n[0].capitalize()


with A.app.test_request_context('/'):
    db = T.get_db()
    cur = db.cursor()
    cur.execute("SELECT ref, cliente_json, fecha_creacion FROM pedidos_pendientes "
                "WHERE fecha_creacion BETWEEN %s AND %s ORDER BY fecha_creacion DESC",
                (desde_utc.strftime(fmt), hasta_utc.strftime(fmt)))
    pend = cur.fetchall()
    cur.execute("SELECT LOWER(TRIM(email_cliente)) e, TRIM(dni_cliente) d FROM ventas WHERE fecha_venta >= %s",
                (desde_ar.strftime(fmt),))
    ventas = cur.fetchall()
    cur.close()
    db.close()
    mails_compra = {v['e'] for v in ventas if v['e']}
    dnis_compra = {v['d'] for v in ventas if v['d']}

    por_cliente = defaultdict(list)   # email -> [(ref, cliente)] más reciente primero
    for p in pend:
        try:
            cli = json.loads(p['cliente_json'] or '{}') or {}
        except Exception:
            continue
        e = (cli.get('email') or '').strip().lower()
        if e:
            por_cliente[e].append((p['ref'], cli, p['fecha_creacion']))

    destinos = []
    for e, lista in por_cliente.items():
        dni = next((str(c.get('dni') or '').strip() for _, c, _ in lista if c.get('dni')), '')
        if e in mails_compra or (dni and dni in dnis_compra):
            continue
        for ref, cli, f in lista:
            r = T.armar_recupero_carrito(ref, None)
            if r and r['elegible']:
                destinos.append({'email': e, 'ref': ref, 'cli': cli, 'r': r, 'fecha': f})
                break

    print(f"{'ENVÍO' if ENVIAR else 'PREVIEW (no escribe ni envía)'} — plantilla {plantilla} — {len(destinos)} clientes\n")
    for i, d in enumerate(destinos, 1):
        r = d['r']
        prods = ', '.join(f"{it['nombre'][:38]}{' x' + str(it['cantidad']) if it['cantidad'] > 1 else ''}"
                          f"{' [DEMORA]' if it['estado'] == 'demora' else ' [SIN STOCK]' if it['estado'] == 'sin_stock' else ''}"
                          for it in r['items'])
        marca = ' (YA ENVIADO, se saltea)' if d['email'] in ya_enviados else ''
        print(f"{i:>2}. {primer_nombre(d['cli'].get('nombre')):<12} {d['email']:<34} "
              f"{(d['fecha'] - timedelta(hours=3)).strftime('%d/%m %H:%M')}  web {T.format_price(r['subtotal'])}{marca}\n      {prods}")

    if not ENVIAR:
        print('\nNo se creó ningún cupón ni se envió nada. Para enviar: agregar --enviar')
        sys.exit(0)

    host = os.getenv('MAIL_SMTP_HOST', 'smtp.gmail.com')
    port = int(os.getenv('MAIL_SMTP_PORT', '587'))
    user = os.getenv('MAIL_SMTP_USER', '')
    pwd = os.getenv('MAIL_SMTP_PASS', '')
    frm = os.getenv('MAIL_FROM', user)
    ok = err = 0
    for d in destinos:
        if d['email'] in ya_enviados:
            continue
        try:
            prep = T.preparar_mail_recupero(d['ref'], plantilla, crear_cupon=True)
            if not prep:
                print('  saltado (ya no aplica):', d['email'])
                continue
            nombre = primer_nombre(d['cli'].get('nombre'))
            html = render_template('tienda/email_recupero_carrito.html', r=prep['r'], nombre=nombre,
                                   link=prep['link'], fp=T.format_price, vence=prep['vence'])
            pct = prep['r']['cupon']['label'].replace('-', '')
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"{nombre}, te guardamos el carrito: {pct} OFF" + (f" hasta el {prep['vence']}" if prep['vence'] else '')
            msg['From'] = f'Mercadomuebles <{frm}>'
            msg['To'] = d['email']
            msg['Reply-To'] = frm
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
            with open(LOG, 'a', encoding='utf-8') as f:
                f.write(json.dumps({'email': d['email'], 'ref': d['ref'], 'codigo': prep['codigo'],
                                    'total': prep['r']['total'], 'fecha': datetime.now().strftime(fmt)}) + '\n')
            ok += 1
            print(f"  ✔ {d['email']}  {prep['codigo']}  total {T.format_price(prep['r']['total'])}")
            time.sleep(2)
        except Exception as e:
            err += 1
            print(f"  ✘ {d['email']}: {e}")
    print(f'\nEnviados: {ok} · errores: {err} · log: {LOG}')
