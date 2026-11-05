#!/usr/bin/env python3
"""Prueba que Descanso Web (TEMA.HILO.PASEO en Real Trends) aparezca con alias
DESCANSO WEB en el ranking, en Competencia V2 y en Ventas Competidores.
Solo lee (el _construir puede dejar un archivo .cache_ en data/, igual que la página).
"""
import os
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')

import competencia_v2_bp as V  # noqa: E402

per = sys.argv[1] if len(sys.argv) > 1 else '2026-11'
rk = V._ranking(per)
total = rk['total'] if isinstance(rk, dict) else rk[0]
for v in total[:8]:
    print(f"{v['pos']:>2} {v['nombre']:<28} nombrado={v['nombrado']} gmv={v['gmv']:,.0f} u={v['u']}")
print('TEMA.HILO.PASEO sigue suelto:', any(v['nombre'] == 'TEMA.HILO.PASEO' for v in total))

d = V._construir(per, 'DescansoWeb')
print('Competencia V2 DescansoWeb: claves', sorted(d.keys())[:8], '| filas A =', len(d.get('A', [])))
rows = V._ventas_detalle(per, 'DescansoWeb')
rows = rows[0] if isinstance(rows, tuple) else rows
print('Ventas competidores DescansoWeb: filas =', len(rows), '| unid =', sum(r.get('u', 0) for r in rows))
