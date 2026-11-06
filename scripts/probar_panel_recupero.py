#!/usr/bin/env python3
"""Prueba el panel de Recupero de carritos sin escribir en la base: renderiza el
listado, la vista previa del mail y verifica que enviar se frene si falta la tabla.

Uso: venv/bin/python scripts/probar_panel_recupero.py [desde AAAA-MM-DD] [hasta AAAA-MM-DD]
"""
import os
import re
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import app as A  # noqa: E402

desde = sys.argv[1] if len(sys.argv) > 1 else '2026-11-02'
hasta = sys.argv[2] if len(sys.argv) > 2 else '2026-11-05'


def sin_deco(f):
    while hasattr(f, '__wrapped__'):
        f = f.__wrapped__
    return f


fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    fallas += 0 if cond else 1


import time  # noqa: E402
t0 = time.time()
with A.app.test_request_context(f'/tienda-admin/recupero-carritos?desde={desde}&hasta={hasta}&plantilla=RECUCYBER'):
    html = sin_deco(A.recupero_carritos)()
seg = time.time() - t0
filas = len(re.findall(r'<tr id="rc-', html))
pend = len(re.findall(r'class="rc-sel"', html))
check(filas > 0, f'listado renderiza: {filas} clientes, {pend} pendientes seleccionables ({seg:.1f}s)')
for est in ('Pendiente', 'Compró', 'Solo almohadas', 'Mail enviado', 'Se dio de baja'):
    print(f'      {est}: {html.count(">" + est)}')
refs = re.findall(r'class="rc-sel" value="([0-9a-f]+)"', html)
if refs:
    with A.app.test_request_context(f'/tienda-admin/recupero-carritos/preview/{refs[0]}?plantilla=RECUCYBER'):
        prev = sin_deco(A.recupero_carritos_preview)(refs[0])
    check('RECUCYBER' in prev and 'carrito/recuperar/' in prev, 'vista previa del mail con cupón y link')
    check('No quiero recibir' not in prev, 'la vista previa no lleva link de baja (no hay destinatario)')
with A.app.test_request_context('/x', method='POST', json={'ref': refs[0] if refs else 'x', 'plantilla': 'RECUCYBER'}):
    res = sin_deco(A.recupero_carritos_enviar)().get_json()
tabla = bool(A.query_db("SHOW TABLES LIKE 'recupero_envios'"))
if not tabla:
    check(not res['ok'] and 'migración' in res['msg'], 'sin la tabla, enviar se frena y no escribe nada')
else:
    print('      (la tabla ya existe: no se probó el envío para no mandar un mail real)')
print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
