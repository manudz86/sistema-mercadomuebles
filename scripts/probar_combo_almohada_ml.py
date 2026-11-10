#!/usr/bin/env python3
"""Prueba (sin escribir en la base ni llamar a ML) la importación automática de órdenes ML con
combo CPR8020+: debe entrar 1x CPR8020 + 1x PLATINO, aunque el título traiga "Almohada".
Se corta la ejecución justo después de armar los items (al pedir el shipping), antes de cualquier
INSERT, y se leen los mensajes [AUTO-ML] que imprime la función.

Uso: venv/bin/python scripts/probar_combo_almohada_ml.py
"""
import contextlib
import io
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


class Corte(BaseException):     # BaseException: no la ataja el `except Exception` de la función
    pass


def cortar(*a, **k):
    raise Corte()


class RespVacia:
    status_code = 500

    def json(self):
        return {}


def correr(items):
    datos = {'items': items, 'shipping': {'shipping_id': 1}, 'fecha_iso': ''}
    A.procesar_orden_ml = lambda orden: datos
    A.obtener_shipping_completo = cortar            # corta antes de cualquier INSERT
    A.verificar_sku_en_bd = lambda s: (True, 'producto', s)
    A.requests.get = lambda *a, **k: RespVacia()    # nada de llamadas reales a ML
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            A._importar_orden_automatica({'id': 999}, 'x')
        except Corte:
            pass
    return buf.getvalue()


# 1) Combo con "Almohada" en el título (caso real 2000019457931560): solo el desglose
out = correr([{'sku': 'CPR8020+', 'titulo': 'Colchón Cannon Princess 24kg 1 Plaza 80x190x20  Almohada',
               'cantidad': 1, 'precio': 175750}])
check('desglosado en' in out, 'combo CPR8020+ se desglosa')
check('Auto-agregado PLATINO' not in out, 'no se agrega otra PLATINO por el título')

# 2) Combo con título recortado (sin "Almohada"): igual que antes
out = correr([{'sku': 'CPR8020+', 'titulo': 'Colchón Cannon Princess 24kg 1 Plaza 80x190x20',
               'cantidad': 1, 'precio': 175750}])
check('desglosado en' in out and 'Auto-agregado PLATINO' not in out, 'título recortado: solo desglose')

# 3) Colchón normal con almohada en el título: sigue auto-agregando
out = correr([{'sku': 'CPR8020', 'titulo': 'Colchón Princess 80x190 + Almohada', 'cantidad': 1, 'precio': 1}])
check('Auto-agregado PLATINO x1' in out, 'colchón no-combo con "Almohada": auto-agrega 1 PLATINO')

out = correr([{'sku': 'CPR14020', 'titulo': 'Colchón Princess 140x190 + Almohadas', 'cantidad': 1, 'precio': 1}])
check('Auto-agregado PLATINO x2' in out, '2 plazas con "Almohadas": auto-agrega 2 PLATINO')

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
