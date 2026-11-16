#!/usr/bin/env python3
"""Solo lectura. Top N del ranking de Real Trends (Competencia V2) y, para cada uno, si ya lo
seguimos: en Competencia V2 (VENDORS_ORDEN), en Ventas Competidores (VENDORS_VC) y en el
scraper de precios (columna tienda del CSV procesado). Para los no seguidos: lo vendido.
Uso: venv/bin/python scripts/analizar_ranking_vs_seguidos.py [PERIODO YYYY-MM] [N=12]
"""
import csv
import os
import sys
from collections import Counter

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
import competencia_v2_bp as C  # noqa: E402

pers = sorted(C.PERIODOS().keys(), reverse=True)
periodo = sys.argv[1] if len(sys.argv) > 1 else pers[0]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
print('períodos:', pers[:6], '→ uso', periodo)

alias_a_vendor = {m['alias']: k for k, m in C.VENDOR_META.items()}
tiendas_csv = Counter()
if os.path.exists(C.CSV_SCRAP):
    with open(C.CSV_SCRAP, encoding='utf-8') as f:
        rd = csv.DictReader(f)
        col = next((c for c in (rd.fieldnames or []) if c.lower() in ('tienda', 'vendedor', 'seller')), None)
        for r in rd:
            if col:
                tiendas_csv[(r.get(col) or '').strip()] += 1
print('scraper CSV tiendas:', dict(tiendas_csv))

d = C._ranking(periodo)
print(f"\nmercado: ${d['gmv_tot']:,.0f}  unidades {d['u_tot']}  vendedores {d['n_vend']}")
cats = d['cats_presentes']
for v in d['total'][:n]:
    k = alias_a_vendor.get(v['nombre'])
    meta = C.VENDOR_META.get(k) or {}
    en_v2 = k in C.VENDORS_ORDEN
    en_vc = k in C.VENDORS_VC
    en_scrap = bool(meta.get('tienda')) and tiendas_csv.get(meta['tienda'], 0) > 0
    det = '  '.join(f"{C.CAT_LBL[t]}: {v['cat'][t]['u']}u ${v['cat'][t]['gmv']:,.0f}" for t in cats if v['cat'][t]['u'])
    print(f"\n#{v['pos']:<2} {v['nombre']:<26} total {v['u']}u ${v['gmv']:,.0f} ({v['share']:.1f}%)"
          f"  | V2={'sí' if en_v2 else 'NO'} VentasComp={'sí' if en_vc else 'NO'} "
          f"scraper={'sí' if en_scrap else 'NO'} seller_id={meta.get('seller_id')}")
    print('    ' + det)
