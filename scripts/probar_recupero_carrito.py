#!/usr/bin/env python3
"""Prueba de punta a punta del link de recupero (sin escribir en la base):
abre el link firmado con el test client de Flask y verifica que el carrito
quede rearmado con el cupón y que el total del carrito coincida con el del mail.
También prueba un token adulterado y un carrito de solo almohadas.

Uso: venv/bin/python scripts/probar_recupero_carrito.py <ref_colchon> <ref_almohadas> [CUPON]
"""
import os
import re
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')

if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(2)
ref_ok, ref_alm = sys.argv[1], sys.argv[2]
cupon = (sys.argv[3] if len(sys.argv) > 3 else 'RECUCYBER').upper()

import app as A  # noqa: E402
import tienda_bp as T  # noqa: E402
import werkzeug  # noqa: E402
if not hasattr(werkzeug, '__version__'):   # Flask viejo + Werkzeug 3: el test client lo pide
    werkzeug.__version__ = '3'

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    fallas += 0 if cond else 1


def path_de(link):
    return link.split('mercadomuebles.com.ar', 1)[1]


with A.app.test_request_context('/'):
    r = T.armar_recupero_carrito(ref_ok, cupon)
    link = T.link_recupero_carrito(ref_ok, cupon)
    ra = T.armar_recupero_carrito(ref_alm, cupon)
    link_alm = T.link_recupero_carrito(ref_alm, cupon)

c = A.app.test_client()
resp = c.get(path_de(link))
check(resp.status_code == 302 and '/tienda/carrito' in resp.headers.get('Location', ''), 'link válido redirige al carrito')
# (session_transaction no anda con este Flask+Werkzeug: se verifica por el HTML del carrito)
html = c.get('/tienda/carrito').get_data(as_text=True)
check(all(i['nombre'] in html for i in r['carrito']), f"carrito rearmado con sus {len(r['carrito'])} items")
check(cupon in html, f'cupón {cupon} aplicado en el carrito')
total_fmt = T.format_price(r['total'])
check(total_fmt in html, f'el carrito muestra el total del mail ({total_fmt})')

# token adulterado
c2 = A.app.test_client()
c2.get(path_de(link).replace('/recuperar/', '/recuperar/x'))
html2 = c2.get('/tienda/carrito').get_data(as_text=True)
check(not any(i['nombre'] in html2 for i in r['carrito']), 'token adulterado no arma carrito')

# solo almohadas: arma el carrito pero sin cupón
c3 = A.app.test_client()
c3.get(path_de(link_alm))
html3 = c3.get('/tienda/carrito').get_data(as_text=True)
check(any(i['nombre'] in html3 for i in ra['carrito']) and cupon not in html3, 'solo almohadas: carrito sí, cupón no')
check(ra and not ra['elegible'], 'solo almohadas: no elegible para el mail')

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
