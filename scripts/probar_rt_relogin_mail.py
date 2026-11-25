#!/usr/bin/env python3
"""Prueba el re-login automático de Real Trends (competencia_v2_bp).

  venv/bin/python scripts/probar_rt_relogin_mail.py leer 2026-11-25T17:46:00
      → solo lee por IMAP el código recibido después de esa hora UTC (no loguea).
  venv/bin/python scripts/probar_rt_relogin_mail.py completo
      → _rt_login() de punta a punta (pide código, lo lee del mail, verifica y
        guarda RT_SESSIONID en config/.env) y prueba un full-download de 1 día.
"""
import datetime
import sys

sys.path.insert(0, '/home/cannon/app')
from dotenv import load_dotenv
load_dotenv('/home/cannon/app/config/.env')

import competencia_v2_bp as c

if len(sys.argv) == 3 and sys.argv[1] == 'leer':
    desde = datetime.datetime.fromisoformat(sys.argv[2])
    print('código:', c._rt_codigo_mail(desde, espera_seg=15))
elif len(sys.argv) == 2 and sys.argv[1] == 'completo':
    sid = c._rt_login()
    print('sessionid nuevo:', sid[:6] + '…')
    d = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
    res, trunc = c._rt_fetch(7969, d, d)
    print(f'full-download almohadas {d}: {len(res)} filas, truncated={trunc}')
else:
    print(__doc__)
