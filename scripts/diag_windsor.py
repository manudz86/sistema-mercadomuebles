#!/usr/bin/env python3
"""Consulta de SOLO LECTURA a la API de Windsor.ai (GET). Nunca imprime la API key.

Uso:
  venv/bin/python scripts/diag_windsor.py <conector> <campos> [date_preset|desde:hasta] [max_filas]
    conector: all | google_ads | facebook | ...
    campos:   date,source,campaign,clicks,spend
  venv/bin/python scripts/diag_windsor.py --campos <conector>     (lista de campos del conector)
  venv/bin/python scripts/diag_windsor.py --raw <ruta> [k=v ...]  (GET a https://connectors.windsor.ai/<ruta>)
"""
import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv('/home/cannon/app/config/.env')
KEY = (os.getenv('WINDSOR_API_KEY') or '').strip()
BASE = 'https://connectors.windsor.ai/'


def get(ruta, params):
    params = dict(params, api_key=KEY)
    try:
        r = requests.get(BASE + ruta, params=params, timeout=90)
    except Exception as e:
        print(f'ERROR de red: {type(e).__name__}')
        return None
    texto = r.text.replace(KEY, '***') if KEY else r.text
    print(f'HTTP {r.status_code} ({len(r.content)} bytes) {ruta}')
    try:
        return json.loads(texto)
    except ValueError:
        print(texto[:1500])
        return None


def mostrar(d, max_filas):
    if isinstance(d, dict) and 'data' in d:
        filas = d['data'] or []
        print(f'filas: {len(filas)}')
        for f in filas[:max_filas]:
            print(json.dumps(f, ensure_ascii=False))
        otros = {k: v for k, v in d.items() if k != 'data'}
        if otros:
            print('otros:', json.dumps(otros, ensure_ascii=False)[:800])
    else:
        print(json.dumps(d, ensure_ascii=False)[:4000])


if not KEY:
    sys.exit('falta WINDSOR_API_KEY en config/.env')
a = sys.argv[1:]
if not a:
    sys.exit(__doc__)
if a[0] == '--campos':
    import re
    d = get(f'{a[1]}/fields', {}) or []
    patron = re.compile(a[2], re.I) if len(a) > 2 else None
    print(f'total campos: {len(d)}')
    for f in d:
        if not patron or patron.search(f.get('id', '') + ' ' + (f.get('name') or '')):
            print(f"{f.get('id')} | {f.get('name')} | {(f.get('description') or '')[:90]}")
elif a[0] == '--raw':
    mostrar(get(a[1], dict(x.split('=', 1) for x in a[2:])), 50)
else:
    conector, campos = a[0], a[1]
    rango = a[2] if len(a) > 2 else 'last_7d'
    maxf = int(a[3]) if len(a) > 3 else 20
    p = {'fields': campos}
    if ':' in rango:
        p['date_from'], p['date_to'] = rango.split(':')
    else:
        p['date_preset'] = rango
    mostrar(get(conector, p), maxf)
