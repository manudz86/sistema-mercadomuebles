#!/usr/bin/env python3
"""Por cada vendedor de Competencia V2 (VENDOR_META), cuántas filas/unidades trae
Real Trends en el período y hasta qué día. Solo lectura.

Uso: venv/bin/python scripts/verificar_rt_vendedores.py [AAAA-MM]
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

per = sys.argv[1] if len(sys.argv) > 1 else '2026-11'
MES = {m: i for i, m in enumerate(V._RT_MESES_EN, 1)}


def dia(t):
    m = re.match(r'([A-Za-z]+) (\d+), (\d{4})', str(t or ''))
    return f'{m.group(3)}-{MES.get(m.group(1), 0):02d}-{int(m.group(2)):02d}' if m else ''


st = defaultdict(lambda: defaultdict(lambda: [0, 0, '']))
max_archivo = {}
for fn, tipo in V.FILE_TIPOS:
    path = os.path.join(V.DATA_DIR, per, fn)
    if not os.path.exists(path):
        continue
    rows = json.load(open(path, encoding='utf-8'))
    max_archivo[fn] = max((dia(r.get('day')) for r in rows), default='')
    for r in rows:
        a = V._alias_rt(r)
        s = st[a][tipo]
        s[0] += 1
        s[1] += int(r.get('sold_quantity') or 0)
        s[2] = max(s[2], dia(r.get('day')))

print('Último día por archivo:', max_archivo)
for k, meta in V.VENDOR_META.items():
    s = st.get(meta['alias'], {})
    det = '  '.join(f"{t}: {v[0]} filas/{v[1]} u (hasta {v[2]})" for t, v in s.items()) or 'SIN DATOS'
    print(f"{k:<15} {meta['alias']:<24} {det}")
