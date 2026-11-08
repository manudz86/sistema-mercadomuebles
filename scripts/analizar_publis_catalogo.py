#!/usr/bin/env python3
"""Publicaciones del vendedor EN ML (no en el sistema) ligadas a un producto de catálogo. Solo GET.
Recorre todas las publis por estado (active, paused, closed, under_review, inactive) con scan,
las lee de a 20 (multiget) y lista las que tienen catalog_product_id = el pedido.

Uso: venv/bin/python scripts/analizar_publis_catalogo.py MLA18621344 [estados separados por coma]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ml_token  # noqa: E402
import requests  # noqa: E402

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)
catalogo = sys.argv[1].strip().upper()
estados = (sys.argv[2].split(',') if len(sys.argv) > 2 else ['active', 'paused', 'closed', 'under_review', 'inactive'])
H = {'Authorization': f'Bearer {ml_token()}'}
API = 'https://api.mercadolibre.com'
seller = requests.get(f'{API}/users/me', headers=H, timeout=20).json()['id']


def ids_por_estado(estado):
    ids, scroll = [], None
    while True:
        p = {'status': estado, 'search_type': 'scan', 'limit': 100}
        if scroll:
            p['scroll_id'] = scroll
        r = requests.get(f'{API}/users/{seller}/items/search', headers=H, params=p, timeout=30)
        if r.status_code != 200:
            print(f'   ({estado}: HTTP {r.status_code} {r.text[:120]})')
            break
        j = r.json()
        res = j.get('results') or []
        if not res:
            break
        ids += res
        scroll = j.get('scroll_id')
        if not scroll:
            break
    return list(dict.fromkeys(ids))


hallados = []
for est in estados:
    ids = ids_por_estado(est)
    print(f'{est}: {len(ids)} publis')
    for i in range(0, len(ids), 20):
        r = requests.get(f'{API}/items', headers=H, timeout=30,
                         params={'ids': ','.join(ids[i:i + 20]),
                                 'attributes': 'id,title,status,sub_status,catalog_product_id,catalog_listing,'
                                               'price,available_quantity,seller_custom_field,listing_type_id,permalink'})
        for x in r.json() if r.status_code == 200 else []:
            b = x.get('body') or {}
            if (b.get('catalog_product_id') or '').upper() == catalogo:
                hallados.append(b)

print(f'\n=== {len(hallados)} publis ligadas a {catalogo} ===')
for b in sorted(hallados, key=lambda b: (b.get('status') != 'paused', b.get('status'), b.get('id'))):
    print(f"{b['id']}  {b.get('status')}{'/' + ','.join(b.get('sub_status') or []) if b.get('sub_status') else ''}  "
          f"{'CATÁLOGO' if b.get('catalog_listing') else 'tradicional'}  ${b.get('price')}  stock {b.get('available_quantity')}  "
          f"SKU {b.get('seller_custom_field')}  {b.get('listing_type_id')}\n      {b.get('title')}\n      {b.get('permalink')}")
