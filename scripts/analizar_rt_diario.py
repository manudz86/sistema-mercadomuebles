#!/usr/bin/env python3
"""Ventas día por día de algunos vendedores según Real Trends (solo lectura).

Uso: venv/bin/python scripts/analizar_rt_diario.py AAAA-MM DIA1,DIA2,... "ALIAS1|ALIAS2|..."
Ej:  venv/bin/python scripts/analizar_rt_diario.py 2026-11 2,3,4 "TU MEJOR SOMMIER|GPV"
Facturación = unidades × precio (igual que el ranking). Usa el alias del sistema
(_alias_rt), así que DESCANSO WEB sale aunque RT lo traiga sin alias.
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import competencia_v2_bp as V  # noqa: E402

if len(sys.argv) != 4:
    print(__doc__)
    sys.exit(2)
per, dias_txt, vends_txt = sys.argv[1], sys.argv[2], sys.argv[3]
dias = [int(d) for d in dias_txt.split(',')]
vends = [v.strip() for v in vends_txt.split('|')]
MES = {m: i for i, m in enumerate(V._RT_MESES_EN, 1)}

for fn, tipo in V.FILE_TIPOS:
    if tipo == 'almohada':
        continue
    path = os.path.join(V.DATA_DIR, per, fn)
    if not os.path.exists(path):
        continue
    acc = defaultdict(lambda: [0, 0.0])   # (vend, dia) -> [u, $]
    for r in json.load(open(path, encoding='utf-8')):
        m = re.match(r'([A-Za-z]+) (\d+), (\d{4})', str(r.get('day') or ''))
        if not m:
            continue
        d = int(m.group(2))
        a = V._alias_rt(r)
        if d not in dias or a not in vends:
            continue
        q = int(r.get('sold_quantity') or 0)
        acc[(a, d)][0] += q
        acc[(a, d)][1] += q * V._price(r.get('price'))
    print(f'\n## {fn}')
    print('vendedor|' + '|'.join(f'd{d}_u|d{d}_$' for d in dias) + '|tot_u|tot_$')
    for v in vends:
        cel = []
        tu, tg = 0, 0.0
        for d in dias:
            u, g = acc.get((v, d), [0, 0.0])
            tu += u
            tg += g
            cel += [str(u), f'{g:.0f}']
        print(f'{v}|' + '|'.join(cel) + f'|{tu}|{tg:.0f}')
