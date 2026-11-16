#!/usr/bin/env python3
"""Solo lectura: renderiza Competencia V2, Ventas Competidores y Ranking con GPV como admin.
Uso: venv/bin/python scripts/probar_competencia_gpv.py
"""
import os
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import werkzeug  # noqa: E402
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3'
import app as A  # noqa: E402

A.app.config['TESTING'] = True
A.login_manager.request_loader(
    lambda req: A.load_user(req.headers['X-Test-User']) if req.headers.get('X-Test-User') else None)
c = A.app.test_client()
h = {'X-Test-User': '1'}
for url in ('/admin/competencia-v2?vendedor=GPV', '/admin/ventas-competidores?vendedor=GPV',
            '/admin/competencia-v2/ranking', '/admin/competencia-v2?vendedor=TMS'):
    r = c.get(url, headers=h)
    html = r.get_data(as_text=True)
    filas = html.count('<tr')
    print(f"{r.status_code} {url:<45} GPV en página={'GPV' in html}  filas={filas}  error={'Traceback' in html or 'error' in html.lower()[:0]}")
