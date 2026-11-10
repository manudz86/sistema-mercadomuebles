#!/usr/bin/env python3
"""SOLO LECTURA: lista envíos recientes de la cuenta Zipnova (GET /v2/shipments) sin datos personales.
Sirve para ver si los envíos Zippin de ventas ML están en Zipnova, de dónde vienen y qué estados tienen.

Uso: venv/bin/python scripts/diag_zipnova_envios.py [tracking ...]
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
buscar = set(sys.argv[1:])

CAMPOS = ('id', 'external_id', 'source', 'status', 'status_name', 'tracking', 'tracking_external',
          'delivery_type', 'created_at', 'logistic_type', 'service_type', 'carrier')


def plano(d, pref=''):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            out.update(plano(v, pref + k + '.'))
        else:
            out[pref + k] = v
    return out


vistos = 0
for page in range(1, 6):
    r = requests.get(f'{BASE}/shipments', params={'account_id': ACCOUNT, 'page': page}, auth=AUTH, timeout=30)
    print(f'GET page {page}: HTTP {r.status_code}')
    if r.status_code != 200:
        print(r.text[:300])
        break
    data = r.json()
    items = data.get('data', data if isinstance(data, list) else [])
    if page == 1 and items:
        print('Claves de un envío:', sorted(items[0].keys()))
    for s in items:
        vistos += 1
        p = plano(s)
        fila = {k: v for k, v in p.items()
                if any(k == c or k.endswith('.' + c) for c in CAMPOS) and v not in (None, '', [])}
        txt = json.dumps(fila, ensure_ascii=False, default=str)
        if not buscar or any(t in json.dumps(s, default=str) for t in buscar):
            print(' ', txt[:400])
    if not items or len(items) < 20:
        break
print('Envíos leídos:', vistos)
