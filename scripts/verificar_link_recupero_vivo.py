#!/usr/bin/env python3
"""Prueba el link de recupero contra la tienda EN VIVO (solo GET, sin escribir en
la base): genera el link firmado de un ref, lo abre con una sesión nueva y mira
que el carrito muestre los productos, el cupón y el total esperados.

Uso: venv/bin/python scripts/verificar_link_recupero_vivo.py <ref> <CUPON>
"""
import os
import sys

import requests

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import app as A  # noqa: E402
import tienda_bp as T  # noqa: E402

if len(sys.argv) != 3:
    print(__doc__)
    sys.exit(2)
ref, cupon = sys.argv[1], sys.argv[2].upper()
with A.app.test_request_context('/'):
    r = T.armar_recupero_carrito(ref, cupon)
    link = T.link_recupero_carrito(ref, cupon)

s = requests.Session()
s.headers['User-Agent'] = 'cannon-verificacion/1.0'
resp = s.get(link, timeout=30)
html = resp.text
print('status final:', resp.status_code, resp.url.split('?')[0])
print('productos en el carrito:', all(i['nombre'] in html for i in r['carrito']))
print('cupón aplicado:', cupon in html)
print('total esperado', T.format_price(r['total']), 'presente:', T.format_price(r['total']) in html)
