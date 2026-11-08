#!/usr/bin/env python3
"""Qué sabe ML del seguimiento de nuestros envíos ME1 (Flete Propio y Zippin/Zipnova).
Solo GET a la API de ML. Para cada venta ME1 del período muestra status/substatus del
shipment, tracking_number/método y el historial de estados, y resume cuántas tuvieron
'shipped' (despacho) y 'delivered' (entrega) informados — lo que mide la
"Experiencia de envío" del panel de ML.

Uso: venv/bin/python scripts/analizar_me1_tracking.py [desde AAAA-MM-DD] [hasta] [max_por_tipo] [--detalle]
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ml_token, conectar_db  # noqa: E402
import requests  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith('--')]
detalle = '--detalle' in sys.argv
desde = args[0] if len(args) > 0 else '2026-10-01'
hasta = args[1] if len(args) > 1 else '2026-11-05'
maximo = int(args[2]) if len(args) > 2 else 25

tok = ml_token()
H = {'Authorization': f'Bearer {tok}'}


def get(path):
    r = requests.get('https://api.mercadolibre.com' + path, headers=H, timeout=20)
    return r.status_code, (r.json() if r.headers.get('content-type', '').startswith('application/json') else r.text)


db = conectar_db()
cur = db.cursor()
cur.execute("SELECT numero_venta, metodo_envio, fecha_venta, estado_entrega, ml_entregado_at FROM ventas "
            "WHERE canal='Mercado Libre' AND metodo_envio IN ('Zippin','Flete Propio') AND fecha_venta BETWEEN %s AND %s "
            "ORDER BY fecha_venta DESC", (desde, hasta + ' 23:59:59'))
filas = cur.fetchall()
por_tipo = {}
for f in filas:
    f = f if isinstance(f, dict) else dict(zip([d[0] for d in cur.description], f))
    por_tipo.setdefault(f['metodo_envio'], []).append(f)

for tipo, ventas in por_tipo.items():
    ventas = ventas[:maximo]
    res = Counter()
    print(f'\n===== {tipo}: {len(ventas)} ventas ({desde} a {hasta}) =====')
    for v in ventas:
        oid = v['numero_venta'].replace('ML-', '')
        sc, o = get(f'/orders/{oid}')
        sid = (o.get('shipping') or {}).get('id') if sc == 200 else None
        if not sid:
            res['sin_shipment'] += 1
            continue
        sc, s = get(f'/shipments/{sid}')
        if sc != 200:
            res[f'err_{sc}'] += 1
            continue
        sh = s.get('status_history') or {}
        hist_sc, hist = get(f'/shipments/{sid}/history')
        eventos = []
        if hist_sc == 200 and isinstance(hist, list):
            eventos = [(e.get('status'), e.get('substatus'), (e.get('date') or '')[:16]) for e in hist]
        tiene_shipped = bool(sh.get('date_shipped'))
        tiene_deliv = bool(sh.get('date_delivered'))
        res['mode_' + str(s.get('mode'))] += 1
        res['status_' + str(s.get('status'))] += 1
        res['con_shipped'] += tiene_shipped
        res['con_delivered'] += tiene_deliv
        res['con_ambos'] += tiene_shipped and tiene_deliv
        res['con_tracking_number'] += bool(s.get('tracking_number'))
        res['reportada_por_sistema'] += bool(v['ml_entregado_at'])
        if detalle:
            print(f"{v['numero_venta']} {str(v['fecha_venta'])[:10]} ship={sid} mode={s.get('mode')} "
                  f"status={s.get('status')}/{s.get('substatus')} tracking={s.get('tracking_number')!r} "
                  f"metodo={s.get('tracking_method')!r} shipped={sh.get('date_shipped')} delivered={sh.get('date_delivered')} "
                  f"reportada_sistema={bool(v['ml_entregado_at'])}")
            for e in eventos:
                print('      ', e)
    for k in sorted(res):
        print(f'  {k}: {res[k]}')
