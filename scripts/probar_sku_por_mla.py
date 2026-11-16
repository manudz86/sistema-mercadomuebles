#!/usr/bin/env python3
"""Prueba (solo lectura) el SKU de respaldo para items de ML sin seller_sku:
procesar_orden_ml con una orden armada en memoria → toma el SKU de sku_mla_mapeo.
Uso: venv/bin/python scripts/probar_sku_por_mla.py
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


def chequear(ok, txt):
    global fallas
    fallas += not ok
    print(('OK    ' if ok else 'FALLA ') + txt)


def orden(item):
    return {'id': 1, 'date_created': '2026-11-16T09:45:00.000-03:00', 'total_amount': 44000,
            'status': 'paid', 'buyer': {}, 'shipping': {},
            'order_items': [{'item': item, 'quantity': 1, 'unit_price': 44000}]}


with A.app.app_context():
    casos = [
        ({'id': 'MLA1299389478', 'title': 'Pack X 2 Doral', 'seller_sku': None}, 'DORALX2', 'pack Doral sin SKU → DORALX2'),
        ({'id': 'MLA1299389478', 'title': 'Pack X 2 Doral', 'seller_sku': 'CEXP150'}, 'CEXP150', 'con seller_sku manda el de ML'),
        ({'id': 'MLA0000000000', 'title': 'Inexistente', 'seller_sku': None}, '', 'MLA sin mapeo → vacío (mapeo manual)'),
        ({'id': None, 'title': 'Sin id'}, '', 'sin id → vacío'),
    ]
    for item, esperado, txt in casos:
        sku = A.procesar_orden_ml(orden(item))['items'][0]['sku']
        chequear(sku == esperado, f'{txt}: {sku!r}')
    sku = A.procesar_orden_ml(orden(casos[0][0]))['items'][0]['sku']
    norm = A.normalizar_sku_ml(sku)
    chequear(norm == ('DORALX2', 0), f'normalizar_sku_ml lo deja igual: {norm}')
    chequear(A.verificar_sku_en_bd('DORALX2')[0], 'DORALX2 existe en la base (combo)')
print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
