#!/usr/bin/env python3
"""Diagnóstico de SOLO LECTURA (GET) de envíos Zipnova: busca envíos por número de orden ML
(o cualquier texto) en la lista de envíos y muestra estado, fechas e historial de tracking.
No imprime datos personales del destinatario.

Uso: venv/bin/python scripts/diag_zipnova_seguimiento.py <desde YYYY-MM-DD> <texto1> [texto2 ...]
     venv/bin/python scripts/diag_zipnova_seguimiento.py --campos <desde>   # muestra las claves de un envío
"""
import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv('/home/cannon/app/config/.env')
BASE = 'https://api.zipnova.com.ar/v2'
AUTH = (os.getenv('ZIPNOVA_API_KEY', ''), os.getenv('ZIPNOVA_API_SECRET', ''))
ACCOUNT = os.getenv('ZIPNOVA_ACCOUNT_ID', '5786')
PERSONALES = {'destination', 'origin', 'recipient', 'sender', 'customer', 'buyer', 'contact'}


def get(path, **params):
    r = requests.get(f'{BASE}{path}', params=params, auth=AUTH, timeout=30)
    if r.status_code not in (200, 206):
        print('HTTP', r.status_code, path, r.text[:300])
        return None
    return r.json()


def listar(desde):
    out, page = [], 1
    while page <= 50:
        d = get('/shipments', account_id=ACCOUNT, **{'from': desde}, page=page, per_page=100)
        if not d:
            break
        data = d.get('data', d if isinstance(d, list) else [])
        out.extend(data)
        meta = d.get('meta') or {}
        if not data or page >= int(meta.get('last_page') or page):
            break
        page += 1
    return out


def sin_personales(o):
    return {k: v for k, v in o.items() if k not in PERSONALES}


args = sys.argv[1:]
if args and args[0] == '--campos':
    envs = listar(args[1])
    print(len(envs), 'envíos')
    if envs:
        print(json.dumps(sin_personales(envs[0]), indent=1, default=str)[:6000])
    sys.exit()

desde, textos = args[0], args[1:]
envs = listar(desde)
print(f'{len(envs)} envíos desde {desde}\n')
for t in textos:
    hits = [e for e in envs if t in json.dumps(e, default=str)]
    print('=' * 70, '\nBuscado:', t, '→', len(hits), 'envío(s)')
    for e in hits:
        det = get(f"/shipments/{e['id']}") or e
        campos = ('id', 'external_id', 'status', 'status_name', 'substatus_code', 'substatus_name',
                  'logistic_type', 'service_type', 'carrier_tracking_id', 'delivery_id',
                  'created_at', 'last_status_at', 'delivered_at')
        for c in campos:
            if c in det:
                print(f'  {c}: {det[c]}')
        car = det.get('carrier')
        if isinstance(car, dict):
            print('  carrier:', car.get('name') or car.get('id'))
        dt = det.get('delivery_time')
        if dt:
            print('  delivery_time:', json.dumps(dt, default=str)[:300])
        otras = [k for k in det if any(p in k.lower() for p in ('pick', 'retir', 'collect', 'manifest', 'dispatch', 'despach'))]
        for k in otras:
            print(f'  [{k}]:', json.dumps(det[k], default=str)[:300])
        tr = get(f"/shipments/{e['id']}/tracking", sort='oldest')
        filas = tr.get('data', []) if isinstance(tr, dict) else (tr or [])
        print('  tracking:')
        for x in filas or []:
            st = x.get('status') or {}
            print(f"    {x.get('occurred_at')} | {st.get('code')} | {st.get('visible_name') or st.get('name')} | {st.get('substatus') or ''}")
