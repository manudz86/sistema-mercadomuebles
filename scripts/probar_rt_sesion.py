#!/usr/bin/env python3
"""Prueba (solo GET) si un sessionid de Real Trends Market Pro sirve.

Uso: venv/bin/python scripts/probar_rt_sesion.py <sessionid>
No escribe nada: no toca config/.env ni la base. Pide la lista de categorías
y un full-download de 1 día de almohadas (lo más chico).
"""
import sys
from datetime import date, timedelta

import requests

RT_BASE = 'https://marketpro.real-trends.com'

if len(sys.argv) != 2:
    print(__doc__)
    sys.exit(2)
sid = sys.argv[1].strip()
h = {'User-Agent': 'cannon/1.0', 'Accept': '*/*'}

r = requests.get(f'{RT_BASE}/api/reports/categories/', headers=h, cookies={'sessionid': sid}, timeout=30)
print('categories:', r.status_code, r.headers.get('content-type'), (r.text or '')[:150].replace('\n', ' '))

d = (date.today() - timedelta(days=2)).isoformat()
r = requests.get(f'{RT_BASE}/api/reports/full-download/',
                 params={'category_id': 7969, 'date_from': d, 'date_to': d,
                         'brand': 'cannon', 'include_attributes': 'true'},
                 headers=h, cookies={'sessionid': sid}, timeout=180)
ct = r.headers.get('content-type') or ''
print('full-download:', r.status_code, ct)
if 'application/json' in ct:
    j = r.json() or {}
    print(f"  filas={len(j.get('results', []))} truncated={j.get('truncated')} dia={d}")
else:
    print('  ', (r.text or '')[:200].replace('\n', ' '))
nuevo = r.cookies.get('sessionid')
print('set-cookie sessionid rotado:', bool(nuevo and nuevo != sid))
