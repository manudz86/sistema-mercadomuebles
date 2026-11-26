#!/usr/bin/env python3
"""SOLO LECTURA: GET crudo a la API de Real Trends Market Pro con la sesión de config/.env.
Uso: venv/bin/python scripts/diag_rt_get.py "/api/reports/catalog-products/?category_id=1612" [largo]
"""
import os
import sys

import requests
from dotenv import dotenv_values

sid = (dotenv_values('/home/cannon/app/config/.env').get('RT_SESSIONID') or '').strip()
path = sys.argv[1]
largo = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
r = requests.get('https://marketpro.real-trends.com' + path, cookies={'sessionid': sid},
                 headers={'User-Agent': 'cannon/1.0', 'Accept': 'application/json'}, timeout=60)
print(r.status_code, r.headers.get('content-type'))
print((r.text or '')[:largo])
