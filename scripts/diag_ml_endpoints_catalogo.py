#!/usr/bin/env python3
"""SOLO LECTURA: prueba qué endpoints de ML siguen respondiendo para armar el monitor
de competencia de un catálogo (tras el 403 PolicyAgent en /products/{id}/items).
Uso: venv/bin/python scripts/diag_ml_endpoints_catalogo.py MLA68660478 MLA3240391132 MLA3249133908
     (catálogo, item de un competidor, item propio)
"""
import sys

import requests

sys.path.insert(0, '/home/cannon/app')
from competencia_bp import _token  # noqa: E402

cat, comp, propio = sys.argv[1:4]
H = {'Authorization': f'Bearer {_token()}'}
B = 'https://api.mercadolibre.com'
pruebas = [
    ('products/items', f'{B}/products/{cat}/items', {'zip_code': '1425', 'limit': 5}),
    ('products/items sin zip', f'{B}/products/{cat}/items', {'limit': 5}),
    ('products/items sin token', f'{B}/products/{cat}/items', None),
    ('products', f'{B}/products/{cat}', None),
    ('item competidor', f'{B}/items/{comp}', {'attributes': 'id,price,original_price,seller_id,status'}),
    ('multiget competidor', f'{B}/items', {'ids': comp, 'attributes': 'id,price,original_price,seller_id'}),
    ('sale_price competidor', f'{B}/items/{comp}/sale_price', {'context': 'channel_marketplace'}),
    ('sale_price propio', f'{B}/items/{propio}/sale_price', {'context': 'channel_marketplace'}),
    ('item propio', f'{B}/items/{propio}', {'attributes': 'id,price,original_price'}),
    ('search product_id', f'{B}/sites/MLA/search', {'product_id': cat, 'limit': 5}),
    ('prices propio', f'{B}/items/{propio}/prices', None),
]
for nombre, url, params in pruebas:
    h = None if 'sin token' in nombre else H
    try:
        r = requests.get(url, headers=h, params=params, timeout=20)
        print(f'{nombre:28s} {r.status_code}  {r.text[:260]}')
    except Exception as e:
        print(f'{nombre:28s} ERROR {e}')
