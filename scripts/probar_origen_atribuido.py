#!/usr/bin/env python3
"""Compara, para las ventas web desde una fecha, el origen del navegador que pagó (origen_last)
con el origen atribuido (último contacto no directo de la persona, todos sus dispositivos).
Solo lectura.

Uso: venv/bin/python scripts/probar_origen_atribuido.py [desde=2026-11-07] [venta_esperada=canal ...]
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
import tienda_bp as T  # noqa: E402

desde = sys.argv[1] if len(sys.argv) > 1 else '2026-11-07'
esperados = dict(x.split('=', 1) for x in sys.argv[2:])
ventas = A.query_db("SELECT numero_venta, fecha_venta, email_cliente, telefono_cliente, origen_last FROM ventas "
                    "WHERE canal='tienda_web' AND fecha_venta >= %s ORDER BY fecha_venta", (desde,))
atr = T.canales_atribuidos(ventas)
fallas = 0
for v in ventas:
    nav = T.clasificar_origen_json(v['origen_last'])
    a = atr.get(v['numero_venta'])
    marca = ' ← cambia' if a != nav else ''
    print(f"{v['fecha_venta']:%Y-%m-%d %H:%M}  {v['numero_venta']:<24} navegador: {nav:<16} atribuido: {a}{marca}")
    if v['numero_venta'] in esperados and esperados[v['numero_venta']] != a:
        fallas += 1
        print('   FALLA: se esperaba', esperados[v['numero_venta']])
filas, _, ok = T._atribucion_datos(A.datetime.strptime(desde, '%Y-%m-%d').date(),
                                    (A.datetime.utcnow()).date())
dif = [f for f in filas if f['canal_ultimo'] != atr.get(f['numero_venta'])]
print('\nReporte de Atribución coincide con Estadísticas:', 'sí' if not dif else f'NO ({len(dif)} distintas)')
fallas += len(dif)
print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
