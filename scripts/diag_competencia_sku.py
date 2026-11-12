#!/usr/bin/env python3
"""Diagnóstico de SOLO LECTURA del monitor de competencia para un SKU: qué catálogos usa, si
entra en la lista a monitorear y qué devolvería el snapshot (sin borrar ni insertar nada).

Uso: venv/bin/python scripts/diag_competencia_sku.py DUALX2
"""
import os
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import competencia_bp as C  # noqa: E402

sku = sys.argv[1].upper()
todos = C._get_skus_monitorear()
print('¿Está en la lista a monitorear?', sku in [s.upper() for s in todos], f'({len(todos)} SKUs)')
filtro = [s for s in todos if s.upper() in [sku.rstrip('Z')]]
print('Coincidencia con el filtro del botón:', filtro)
cats = C._get_catalogos(sku)
print('Catálogos:', cats)
for cat in cats:
    res = C._ml_catalog_all(cat, '1425')
    propios = [r for r in res if r.get('seller_id') == C.MY_SELLER_ID]
    print(f'  {cat}: {len(res)} publicaciones en el catálogo, {len(propios)} propias')
    print('  meta:', C._sku_meta(sku))
