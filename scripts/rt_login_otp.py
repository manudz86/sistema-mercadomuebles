#!/usr/bin/env python3
"""Login a Real Trends Market Pro por mail + código (OTP).

Desde el 20/11/2026 la llave (RT_LLAVE_USUARIO) quedó vinculada a un mail y
/api/auth/login/ con {"key"} devuelve 409 key_has_email. El flujo nuevo es:

  1) venv/bin/python scripts/rt_login_otp.py pedir [email]
     → POST /api/auth/login/email/ {email}; RT manda un código al mail.
       Guarda las cookies del flujo en data/.rt_otp_flow.json.
  2) venv/bin/python scripts/rt_login_otp.py verificar <codigo>
     → POST /api/auth/otp/verify/ {code}; si da OK, prueba un full-download
       chico y guarda el sessionid en config/.env (RT_SESSIONID=...).

Hacer backup de config/.env antes del paso 2 (CLAUDE.md).
"""
import json
import os
import sys
from datetime import date, timedelta

import requests

APP_DIR = '/home/cannon/app'
RT_BASE = 'https://marketpro.real-trends.com'
FLOW = os.path.join(APP_DIR, 'data', '.rt_otp_flow.json')
ENV = os.path.join(APP_DIR, 'config', '.env')
EMAIL_DEFAULT = 'contacto@mercadomuebles.com.ar'


def _session(cookies=None):
    s = requests.Session()
    s.headers['User-Agent'] = 'cannon/1.0'
    if cookies:
        for k, v in cookies.items():
            s.cookies.set(k, v, domain='marketpro.real-trends.com')
    return s


def _post(s, path, body):
    s.get(f'{RT_BASE}/', timeout=20) if not s.cookies.get('csrftoken') else None
    h = {'Content-Type': 'application/json', 'Referer': f'{RT_BASE}/login'}
    if s.cookies.get('csrftoken'):
        h['X-CSRFToken'] = s.cookies.get('csrftoken')
    return s.post(f'{RT_BASE}{path}', json=body, headers=h, timeout=30)


def pedir(email):
    s = _session()
    r = _post(s, '/api/auth/login/email/', {'email': email})
    print('login/email:', r.status_code, (r.text or '')[:300])
    with open(FLOW, 'w') as f:
        json.dump(s.cookies.get_dict(), f)
    os.chmod(FLOW, 0o600)
    print('cookies del flujo guardadas:', sorted(s.cookies.get_dict().keys()))


def guardar_sessionid(sid):
    lines = open(ENV).read().splitlines()
    done = False
    for i, l in enumerate(lines):
        if l.startswith('RT_SESSIONID='):
            lines[i] = f'RT_SESSIONID={sid}'
            done = True
    if not done:
        lines.append(f'RT_SESSIONID={sid}')
    tmp = ENV + '.tmp'
    with open(tmp, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    os.replace(tmp, ENV)


def verificar(code):
    if not os.path.exists(FLOW):
        sys.exit('No hay flujo pendiente: correr primero "pedir".')
    s = _session(json.load(open(FLOW)))
    r = _post(s, '/api/auth/otp/verify/', {'code': code.strip()})
    print('otp/verify:', r.status_code, (r.text or '')[:300])
    sid = s.cookies.get('sessionid')
    if r.status_code != 200 or not sid:
        sys.exit('No se obtuvo sesión.')
    d = (date.today() - timedelta(days=2)).isoformat()
    t = requests.get(f'{RT_BASE}/api/reports/full-download/',
                     params={'category_id': 7969, 'date_from': d, 'date_to': d,
                             'brand': 'cannon', 'include_attributes': 'true'},
                     headers={'User-Agent': 'cannon/1.0', 'Accept': '*/*'},
                     cookies={'sessionid': sid}, timeout=180)
    ct = t.headers.get('content-type') or ''
    print('prueba full-download:', t.status_code, ct)
    if t.status_code != 200 or 'application/json' not in ct:
        sys.exit('La sesión no sirve para descargar; no se guarda.')
    print(f"  filas={len((t.json() or {}).get('results', []))} dia={d}")
    guardar_sessionid(t.cookies.get('sessionid') or sid)
    os.remove(FLOW)
    print('RT_SESSIONID guardado en config/.env')


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'pedir':
        pedir(sys.argv[2] if len(sys.argv) > 2 else EMAIL_DEFAULT)
    elif len(sys.argv) == 3 and sys.argv[1] == 'verificar':
        verificar(sys.argv[2])
    else:
        print(__doc__)
