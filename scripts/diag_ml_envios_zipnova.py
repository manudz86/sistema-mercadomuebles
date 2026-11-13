#!/usr/bin/env python3
"""Diagnóstico de SOLO LECTURA (GET a ML): para ventas ML despachadas por Zipnova, muestra
qué ve ML del envío (modo, estado, historial, tracking) y qué mensajes hubo en la compra.
Los mensajes se leen con mark_as_read=false (no los marca como leídos). Del comprador solo
se muestra fecha y largo (no el texto); del vendedor/integrador se muestra el texto.

Uso: venv/bin/python scripts/diag_ml_envios_zipnova.py 2000018493120564 [2000018531175094 ...]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ml_token  # noqa: E402
import requests  # noqa: E402

SELLER = 29563319
API = 'https://api.mercadolibre.com'
tok = ml_token()
H = {'Authorization': f'Bearer {tok}'}


def get(path, params=None, extra=None):
    r = requests.get(API + path, headers={**H, **(extra or {})}, params=params, timeout=30)
    if r.status_code not in (200, 206):
        return {'_http': r.status_code, '_txt': r.text[:200]}
    return r.json()


for oid in sys.argv[1:]:
    print('=' * 78)
    o = get(f'/orders/{oid}')
    pack = o.get('pack_id') or oid
    sid = (o.get('shipping') or {}).get('id')
    print(f'Orden {oid} | pack {pack} | shipment {sid}')
    if sid:
        s = get(f'/shipments/{sid}', extra={'x-format-new': 'true'})
        log = s.get('logistic') or {}
        print('  modo:', s.get('mode') or log.get('mode'), '| logistic_type:', s.get('logistic_type') or log.get('type'),
              '| estado:', s.get('status'), '/', s.get('substatus'),
              '| tracking:', s.get('tracking_number'), '| método:', s.get('tracking_method'))
        h = get(f'/shipments/{sid}/history')
        filas = h if isinstance(h, list) else h.get('results') or h.get('data') or []
        if isinstance(h, dict) and '_http' in h:
            print('  history HTTP', h['_http'])
        for x in filas:
            print(f"    hist: {x.get('date')} | {x.get('status')} / {x.get('substatus')}")
        sh = s.get('status_history') or {}
        if sh:
            print('  status_history:', {k: v for k, v in sh.items() if v})
    m = get(f'/messages/packs/{pack}/sellers/{SELLER}', {'tag': 'post_sale', 'mark_as_read': 'false', 'limit': 50})
    if '_http' in m:
        print('  mensajes HTTP', m['_http'], m['_txt'])
        continue
    msgs = m.get('messages') or []
    print(f'  mensajes: {len(msgs)}')
    for x in sorted(msgs, key=lambda y: (y.get('message_date') or {}).get('created') or ''):
        de = (x.get('from') or {}).get('user_id')
        fecha = (x.get('message_date') or {}).get('created')
        txt = (x.get('text') or '').replace('\n', ' ')
        if str(de) == str(SELLER):
            print(f'    {fecha} VENDEDOR: {txt[:220]}')
        else:
            print(f'    {fecha} comprador ({len(txt)} caracteres)')
