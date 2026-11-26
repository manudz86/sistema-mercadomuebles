#!/usr/bin/env python3
"""SOLO LECTURA: muestra los campos de una fila de los JSON de Real Trends (competencia V2)
y las filas de un catálogo/título dado, para ver si alcanza para el monitor de competencia.
Uso: venv/bin/python scripts/analizar_rt_campos.py data/competencia_v2/2026-11/colchones.json [texto_titulo]
"""
import json
import sys

ruta = sys.argv[1]
filtro = (sys.argv[2] if len(sys.argv) > 2 else '').lower()
d = json.load(open(ruta))
filas = d if isinstance(d, list) else (d.get('results') or d.get('rows') or [])
print('total filas:', len(filas))
if filas:
    f0 = filas[0]
    print('campos:', sorted(f0.keys()) if isinstance(f0, dict) else type(f0))
    print('ejemplo:', {k: (str(v)[:60]) for k, v in f0.items() if k != 'attributes'} if isinstance(f0, dict) else f0)
if filtro:
    ult = {}
    for f in filas:
        if isinstance(f, dict) and filtro in str(f.get('title', '')).lower():
            ult.setdefault(f.get('day'), []).append(f)
    for dia in list(ult)[-1:]:
        print(f'\n{dia}: {len(ult[dia])} filas con "{filtro}"')
        for f in ult[dia][:15]:
            print({k: str(v)[:40] for k, v in f.items() if k in (
                'seller', 'nickname', 'official_store', 'listing_type', 'price', 'installments',
                'installment_type', 'is_catalog_product', 'sold_quantity', 'item_id', 'id',
                'catalog_product_id', 'logistic_type', 'title')})
