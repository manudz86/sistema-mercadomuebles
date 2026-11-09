#!/usr/bin/env python3
"""Prueba la promesa de entrega (sin escribir en la base):
1) tienda_bp.promesa_entrega_web: lo que se le mostró al cliente → fecha.
2) /ventas/<id>/promesa-entrega: validaciones y UPDATE (execute_db interceptado).
3) Formularios: nueva venta y editar venta muestran el campo (y ML no deja editarlo).
4) Panel del calendario: formulario "Cambiar" solo en ventas no-ML.

Uso: venv/bin/python scripts/probar_promesa_entrega.py
"""
import os
import sys
from datetime import date, datetime

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import werkzeug  # noqa: E402
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3'
import app as A  # noqa: E402
import tienda_bp as T  # noqa: E402

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    fallas += 0 if cond else 1


# ── 1) cálculo de la tienda ──────────────────────────────────────────────
vie = datetime(2026, 11, 6, 15, 0)   # viernes
lun = datetime(2026, 11, 9, 10, 0)   # lunes
P = T.promesa_entrega_web
check(P({'tipo_entrega': 'envio', 'zipnova_quote': {'dias': 3}}, lun) == date(2026, 11, 12), 'envío 3 hábiles desde lunes → jueves')
check(P({'tipo_entrega': 'envio', 'zipnova_quote': {'dias': 2}}, vie) == date(2026, 11, 10), 'envío 2 hábiles desde viernes → martes (salta finde)')
check(P({'tipo_entrega': 'envio', 'zipnova_quote': {'dias': 3}, 'demora_dias': 15}, lun) == date(2026, 11, 27),
      'con demora 15 + 3 → igual que el "aprox." del carrito (corridos)')
check(P({'tipo_entrega': 'envio', 'zipnova_quote': {'dias': '?'}}, lun) is None, 'cotizador sin días → sin promesa')
check(P({'tipo_entrega': 'envio', 'zipnova_quote': {'dias': '?'}, 'demora_dias': 10}, lun) == date(2026, 11, 19), 'sin días pero con demora → disponibilidad')
check(P({'tipo_entrega': 'retiro'}, lun) is None, 'retiro sin demora → sin promesa')
check(P({'tipo_entrega': 'retiro', 'demora_dias': 7}, lun) == date(2026, 11, 16), 'retiro con demora → fecha disponible')
check(P({}, None) is None, 'datos rotos → None sin excepción')

# ── 2) ruta de cambio ────────────────────────────────────────────────────
escrito = []
A.execute_db = lambda q, p=None: escrito.append((q, p))
A.app.config['LOGIN_DISABLED'] = True
cli = A.app.test_client()
no_ml = A.query_db("SELECT id FROM ventas WHERE canal<>'Mercado Libre' AND estado_entrega IN ('pendiente','en_proceso') ORDER BY id DESC LIMIT 1")
ml = A.query_db("SELECT id FROM ventas WHERE canal='Mercado Libre' AND estado_entrega IN ('pendiente','en_proceso') ORDER BY id DESC LIMIT 1")
hist = A.query_db("SELECT id FROM ventas WHERE canal<>'Mercado Libre' AND estado_entrega='entregada' ORDER BY id DESC LIMIT 1")
if no_ml:
    vid = no_ml[0]['id']
    r = cli.post(f'/ventas/{vid}/promesa-entrega', data={'fecha_entrega_estimada': '2026-11-20', 'volver': '/ventas/calendario-entregas?mes=2026-11'})
    check(r.status_code == 302 and r.location.endswith('/ventas/calendario-entregas?mes=2026-11'), 'cambio → vuelve al mes del calendario')
    check(escrito and escrito[-1][1] == (date(2026, 11, 20), vid), f'UPDATE con la fecha nueva (venta {vid})')
    n = len(escrito)
    cli.post(f'/ventas/{vid}/promesa-entrega', data={'fecha_entrega_estimada': ''})
    check(len(escrito) == n + 1 and escrito[-1][1] == (None, vid), 'vacío → quita la promesa')
    n = len(escrito)
    cli.post(f'/ventas/{vid}/promesa-entrega', data={'fecha_entrega_estimada': 'basura'})
    cli.post(f'/ventas/{vid}/promesa-entrega', data={'fecha_entrega_estimada': '2030-01-01'})
    check(len(escrito) == n, 'fecha inválida / a más de un año → no escribe')
    r = cli.post(f'/ventas/{vid}/promesa-entrega', data={'fecha_entrega_estimada': '2026-11-20', 'volver': 'https://otro.sitio'})
    check(r.location.endswith('/ventas/calendario-entregas'), 'volver externo → ignorado')
    escrito.clear()
if ml:
    cli.post(f'/ventas/{ml[0]["id"]}/promesa-entrega', data={'fecha_entrega_estimada': '2026-11-20'})
    check(not escrito, 'venta de ML → no se toca')
if hist:
    cli.post(f'/ventas/{hist[0]["id"]}/promesa-entrega', data={'fecha_entrega_estimada': '2026-11-20'})
    check(not escrito, 'venta ya entregada → no se toca')

# ── 3) formularios ───────────────────────────────────────────────────────
html = cli.get('/nueva-venta').get_data(as_text=True)
check('name="fecha_entrega_estimada"' in html, 'nueva venta: campo Promesa de entrega')
act_no_ml = A.query_db("SELECT id FROM ventas WHERE canal<>'Mercado Libre' AND estado_entrega='pendiente' ORDER BY id DESC LIMIT 1")
act_ml = A.query_db("SELECT id FROM ventas WHERE canal='Mercado Libre' AND estado_entrega='pendiente' ORDER BY id DESC LIMIT 1")
if act_no_ml:
    h = cli.get(f'/ventas/editar/{act_no_ml[0]["id"]}').get_data(as_text=True)
    check('name="fecha_entrega_estimada"' in h, 'editar venta no-ML: campo editable')
if act_ml:
    h = cli.get(f'/ventas/editar/{act_ml[0]["id"]}').get_data(as_text=True)
    check('name="fecha_entrega_estimada"' not in h and 'la fija Mercado Libre' in h, 'editar venta ML: solo lectura')

# ── 4) panel del calendario ──────────────────────────────────────────────
cal = cli.get('/ventas/calendario-entregas').get_data(as_text=True)
check("/promesa-entrega" in cal and "La fija Mercado Libre" in cal, 'calendario: formulario de cambio en el panel')

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
