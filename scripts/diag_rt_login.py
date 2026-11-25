#!/usr/bin/env python3
"""Diagnóstico del login de Real Trends Market Pro con la llave (RT_LLAVE_USUARIO).

Hace lo mismo que competencia_v2_bp._rt_login() pero NO persiste nada: solo muestra
status, headers relevantes y el cuerpo de la respuesta (para entender un 409, etc.).
Uso: venv/bin/python scripts/diag_rt_login.py
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv('/home/cannon/app/config/.env')
RT_BASE = 'https://marketpro.real-trends.com'
llave = os.getenv('RT_LLAVE_USUARIO', '').strip()
print('llave cargada:', bool(llave), 'largo:', len(llave), 'termina en:', llave[-4:] if llave else '-')

s = requests.Session()
s.headers['User-Agent'] = 'cannon/1.0'
r0 = s.get(f'{RT_BASE}/', timeout=20)
print('home:', r0.status_code, 'csrftoken:', bool(s.cookies.get('csrftoken')))

h = {'Content-Type': 'application/json', 'Referer': f'{RT_BASE}/login'}
if s.cookies.get('csrftoken'):
    h['X-CSRFToken'] = s.cookies.get('csrftoken')
r = s.post(f'{RT_BASE}/api/auth/login/', json={'key': llave}, headers=h, timeout=30)
print('login:', r.status_code, r.headers.get('content-type'))
print('body:', (r.text or '')[:1500])
print('sessionid devuelto:', bool(s.cookies.get('sessionid')))
