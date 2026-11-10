#!/usr/bin/env python3
"""Prueba (sin escribir en la base) que las ventas ML Full / Colecta no llevan fecha de entrega elegida:
1) app.entrega_sin_fecha: regla por canal + método de envío.
2) _fecha_entrega.html: el Set VENTAS_SIN_FECHA que arma la página solo trae Full / Colecta de ML.

Uso: venv/bin/python scripts/probar_entrega_sin_fecha.py
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

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    if not cond:
        fallas += 1


casos = [
    ({'canal': 'Mercado Libre', 'metodo_envio': 'Full'}, True),
    ({'canal': 'Mercado Libre', 'metodo_envio': 'Colecta'}, True),
    ({'canal': 'Mercado Libre', 'metodo_envio': 'Flex'}, True),
    ({'canal': 'Mercado Libre', 'metodo_envio': 'Delega'}, True),
    ({'canal': 'Mercado Libre', 'metodo_envio': 'Zippin'}, False),
    ({'canal': 'tienda_web', 'metodo_envio': 'Delega'}, False),
    ({'canal': 'Mercado Libre', 'metodo_envio': 'Flete Propio'}, False),
    ({'canal': 'Mercado Libre', 'metodo_envio': 'Turbo'}, False),
    ({'canal': 'Mercado Libre', 'metodo_envio': None}, False),
    ({'canal': 'tienda_web', 'metodo_envio': 'Colecta'}, False),
    ({'canal': 'Fuera de ML', 'metodo_envio': 'Full'}, False),
]
for v, esperado in casos:
    check(A.entrega_sin_fecha(v) is esperado, f'{v["canal"]}/{v["metodo_envio"]} → sin fecha={esperado}')

ventas = [
    {'id': 1, 'canal': 'Mercado Libre', 'metodo_envio': 'Full'},
    {'id': 2, 'canal': 'Mercado Libre', 'metodo_envio': 'Colecta'},
    {'id': 3, 'canal': 'Mercado Libre', 'metodo_envio': 'Flete Propio'},
    {'id': 4, 'canal': 'tienda_web', 'metodo_envio': 'Delega'},
    {'id': 5, 'canal': 'Mercado Libre', 'metodo_envio': 'Delega'},
    {'id': 6, 'canal': 'Mercado Libre', 'metodo_envio': 'Flex'},
]
with A.app.app_context():
    tpl = A.app.jinja_env.get_template('_fecha_entrega.html')
    html = tpl.render(ventas=ventas)
    linea = next(l for l in html.splitlines() if 'VENTAS_SIN_FECHA = new Set' in l)
    check(all(f"'{i}'," in linea for i in (1, 2, 5, 6)), 'Set incluye Full, Colecta, Delega y Flex de ML')
    check("'3'," not in linea and "'4'," not in linea, 'Set excluye Flete Propio y tienda web (aunque sea Delega)')
    html_vacio = tpl.render()
    check('new Set([])' in html_vacio, 'sin ventas en el contexto: Set vacío, no rompe')

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
