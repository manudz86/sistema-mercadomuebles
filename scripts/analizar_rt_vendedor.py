#!/usr/bin/env python3
"""Lista qué filas tiene un vendedor (por nickname de ML) en los JSON de Real Trends.

Uso: venv/bin/python scripts/analizar_rt_vendedor.py <NICKNAME> [<periodo AAAA-MM>]
Solo lectura. Muestra filas, unidades y alias por archivo, y algunos item_id.
"""
import json
import os
import sys
from collections import Counter

DATA = '/home/cannon/app/data/competencia_v2'
if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)
nick = sys.argv[1].strip().upper()
periodos = [sys.argv[2]] if len(sys.argv) > 2 else sorted(os.listdir(DATA))

for p in periodos:
    for fn in ('colchones.json', 'sommiers.json', 'almohadas.json'):
        path = os.path.join(DATA, p, fn)
        if not os.path.exists(path):
            continue
        try:
            rows = json.load(open(path, encoding='utf-8'))
        except Exception as e:
            print(p, fn, 'ERROR', e)
            continue
        mias = [r for r in rows if (r.get('nickname') or '').strip().upper() == nick]
        if not mias:
            continue
        u = sum(int(r.get('sold_quantity') or 0) for r in mias)
        alias = Counter((r.get('alias') or '').strip() for r in mias)
        items = sorted(set(r.get('item_id') for r in mias if r.get('item_id')))
        print(f'{p} {fn}: filas={len(mias)} unid={u} alias={dict(alias)} items={len(items)}')
        ult = sorted(mias, key=lambda r: str(r.get('day') or ''))[-4:]
        for r in ult:
            print(f"    {r.get('day')} cat={r.get('catalog_product_id')} precio={r.get('price')} {(r.get('title') or '')[:50]}")
