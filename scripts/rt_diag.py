#!/usr/bin/env python3
"""Diagnostico de SOLO LECTURA de la conexion con Market Pro (Real Trends).

Comprueba, por separado:
  1) si el RT_SESSIONID guardado sigue sirviendo,
  2) si el re-login con RT_LLAVE_USUARIO todavia funciona.

Uso:  venv/bin/python3 scripts/rt_diag.py

Solo hace GET/POST de autenticacion y una consulta chica. No escribe en
config/.env ni toca la base. Nunca imprime la llave ni el sessionid.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests as req_lib  # noqa: E402
from _common import cargar_env  # noqa: E402

ENV = cargar_env()
RT_BASE = 'https://marketpro.real-trends.com'
SID = (ENV.get('RT_SESSIONID') or '').strip()
LLAVE = (ENV.get('RT_LLAVE_USUARIO') or '').strip()


def _resumen(r):
    ct = (r.headers.get('content-type') or '').split(';')[0]
    print(f'      HTTP {r.status_code} · content-type: {ct or "(ninguno)"} · {len(r.content)} bytes')
    if 'json' in ct:
        try:
            d = r.json()
            if isinstance(d, dict):
                print(f'      claves: {list(d.keys())[:12]}')
                if 'results' in d:
                    print(f'      results: {len(d.get("results") or [])} filas · truncated={d.get("truncated")}')
                for k, v in d.items():
                    if k != 'results' and isinstance(v, (str, int, float, bool)):
                        print(f'      {k}: {str(v)[:200]}')
        except Exception:
            pass
    else:
        txt = (r.text or '').strip().replace('\n', ' ')
        print(f'      cuerpo: {txt[:220]}')


def probar_sessionid():
    print('\n1) SESSIONID guardado')
    if not SID:
        print('   No hay RT_SESSIONID en config/.env')
        return False
    print(f'   presente ({len(SID)} chars, no se muestra)')
    hoy = date.today()
    d0 = hoy.replace(day=1).isoformat()
    try:
        r = req_lib.get(f'{RT_BASE}/api/reports/full-download/',
                        params={'category_id': 1612, 'date_from': d0, 'date_to': hoy.isoformat(),
                                'brand': 'cannon', 'include_attributes': 'true'},
                        headers={'User-Agent': 'cannon/1.0', 'Accept': '*/*'},
                        cookies={'sessionid': SID}, timeout=120)
    except Exception as e:
        print(f'      EXC {type(e).__name__}: {e}')
        return False
    _resumen(r)
    ok = r.status_code == 200 and 'json' in (r.headers.get('content-type') or '')
    print(f'   >>> {"SIRVE" if ok else "NO SIRVE"}')
    return ok


def probar_llave():
    print('\n2) RE-LOGIN con la llave (RT_LLAVE_USUARIO)')
    if not LLAVE:
        print('   No hay RT_LLAVE_USUARIO en config/.env')
        return False
    print(f'   presente ({len(LLAVE)} chars, no se muestra)')
    s = req_lib.Session()
    s.headers['User-Agent'] = 'cannon/1.0'
    try:
        s.get(f'{RT_BASE}/', timeout=20)
    except Exception:
        pass
    h = {'Content-Type': 'application/json', 'Referer': f'{RT_BASE}/login'}
    if s.cookies.get('csrftoken'):
        h['X-CSRFToken'] = s.cookies.get('csrftoken')
    try:
        r = s.post(f'{RT_BASE}/api/auth/login/', json={'key': LLAVE}, headers=h, timeout=30)
    except Exception as e:
        print(f'      EXC {type(e).__name__}: {e}')
        return False
    _resumen(r)
    sid = s.cookies.get('sessionid')
    print(f'   >>> sessionid devuelto: {"SI" if sid else "NO"}')
    return bool(sid)


def main():
    print(f'ENTORNO: {RT_BASE}')
    a = probar_sessionid()
    b = probar_llave()
    print('\n' + '=' * 56)
    print(f'  sessionid guardado .......... {"OK" if a else "VENCIDO / INVALIDO"}')
    print(f'  re-login con la llave ....... {"OK" if b else "YA NO FUNCIONA"}')
    print('=' * 56)
    return 0


if __name__ == '__main__':
    sys.exit(main())
