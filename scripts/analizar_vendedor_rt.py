#!/usr/bin/env python3
"""Solo lectura. Para vendedores (por alias o nickname de Real Trends) de un período:
nicknames, ciudad, y top publicaciones por facturación (modelo, unidades, facturación).
NO informa precio actual (eso sale del scraper).
Uso: venv/bin/python scripts/analizar_vendedor_rt.py 2026-11 "GPV" "A. AMALFI" "MILESI HOGAR"
"""
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
import competencia_v2_bp as C  # noqa: E402

periodo, buscados = sys.argv[1], [a.upper() for a in sys.argv[2:]]
for nombre in buscados:
    nicks, ciudades, items = Counter(), Counter(), defaultdict(lambda: {'u': 0, 'gmv': 0.0, 'tit': '', 'cat': ''})
    for fname, tipo in C.FILE_TIPOS:
        p = os.path.join(C.DATA_DIR, periodo, fname)
        if not os.path.exists(p):
            continue
        for r in json.load(open(p, encoding='utf-8')):
            q = int(r.get('sold_quantity') or 0)
            if q <= 0 or C._vend_key(r)[0].upper() != nombre:
                continue
            nicks[(r.get('nickname') or '').strip()] += q
            ciudades[f"{r.get('seller_city')}, {r.get('seller_state')}"] += q
            it = items[r.get('item_id')]
            it['u'] += q
            it['gmv'] += q * C._price(r.get('price'))
            it['tit'] = (r.get('title') or '')[:70]
            it['cat'] = C.CAT_LBL[tipo]
            it['envio'] = r.get('shipping_mode_type') or r.get('shipping_mode')
    print(f'\n=== {nombre} === nicknames={dict(nicks)} ciudad={ciudades.most_common(1)} publis con venta={len(items)}')
    for mla, it in sorted(items.items(), key=lambda x: -x[1]['gmv'])[:8]:
        print(f"   {mla:<14} {it['cat']:<10} {it['u']:>4}u ${it['gmv']:>13,.0f}  {it['envio']}  {it['tit']}")
