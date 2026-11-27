#!/usr/bin/env python3
"""SOLO LECTURA: compara un Excel de lista de precios Cannon (col A código, col C importe,
igual que /costos/importar) contra cannon_lista_precios cargada. Agrupa por familia
(colchones / bases / almohadas / otros) usando la descripción de cannon_productos o del Excel.
Uso: venv/bin/python scripts/analizar_lista_cannon_vs_actual.py <lista.xlsx> [detalle]
"""
import statistics
import sys
from collections import defaultdict

import pymysql
from dotenv import dotenv_values
from openpyxl import load_workbook

ruta = sys.argv[1]
detalle = len(sys.argv) > 2
env = dotenv_values('/home/cannon/app/config/.env')
db = pymysql.connect(host=env.get('DB_HOST', 'localhost'), user=env.get('DB_RO_USER'),
                     password=env.get('DB_RO_PASSWORD', ''), port=int(env.get('DB_PORT') or 3306),
                     database=env.get('DB_NAME', 'inventario_cannon'),
                     cursorclass=pymysql.cursors.DictCursor)
cur = db.cursor()
cur.execute("SELECT clp.codigo_material c, clp.precio_lista p, clp.vigencia v, cp.descripcion d, cp.sku "
            "FROM cannon_lista_precios clp LEFT JOIN cannon_productos cp ON cp.codigo_material = clp.codigo_material")
ACT = {int(r['c']): r for r in cur.fetchall()}

wb = load_workbook(ruta, read_only=True, data_only=True)
print('hojas:', wb.sheetnames)
ws = wb.active
NUEVA = {}
for row in ws.iter_rows(values_only=True):
    if not row or not isinstance(row[0], (int, float)) or len(row) < 3:
        continue
    if not isinstance(row[2], (int, float)) or not row[2]:
        continue
    NUEVA[int(row[0])] = (float(row[2]), str(row[1] or ''))


def familia(desc):
    d = (desc or '').upper()
    if d.startswith('ALM') or 'ALMOHADA' in d:
        return 'almohadas'
    if d.startswith(('BASE', 'SOMMIER', 'BAS ')) or ' BASE ' in f' {d} ' or 'SOMMIER' in d:
        return 'bases'
    if d.startswith(('COL', 'CLCH')) or 'COLCHON' in d or 'COLCHÓN' in d:
        return 'colchones'
    return 'otros'


grupos = defaultdict(list)
solo_nueva, solo_act = [], []
for cod, (pn, dx) in NUEVA.items():
    a = ACT.get(cod)
    desc = (a and a['d']) or dx
    if not a:
        solo_nueva.append((cod, desc, pn))
        continue
    pa = float(a['p'])
    grupos[familia(desc)].append((100 * (pn / pa - 1), cod, desc, pa, pn, a['v']))
for cod, a in ACT.items():
    if cod not in NUEVA:
        solo_act.append((cod, a['d'], float(a['p'])))

vig = sorted({str(a['v']) for a in ACT.values()})
print(f'Excel: {len(NUEVA)} códigos con precio | cargados: {len(ACT)} (vigencias {vig})')
print(f"{'familia':<11}{'n':>4}{'prom %':>8}{'mediana':>9}{'min':>8}{'max':>8}{'sin cambio':>11}")
for fam in ('colchones', 'bases', 'almohadas', 'otros'):
    g = grupos.get(fam)
    if not g:
        continue
    v = [x[0] for x in g]
    print(f"{fam:<11}{len(v):>4}{statistics.mean(v):>7.1f}%{statistics.median(v):>8.1f}%"
          f"{min(v):>7.1f}%{max(v):>7.1f}%{sum(1 for x in v if abs(x) < 0.05):>11}")
    # distribución por tramo
    tramos = defaultdict(int)
    for x in v:
        tramos[round(x)] += 1
    print('           tramos (% redondeado: cantidad):', dict(sorted(tramos.items())))
    if detalle:
        for x, cod, desc, pa, pn, vg in sorted(g):
            print(f'    {x:>6.1f}%  {cod}  {desc[:45]:<45} {pa:>12,.0f} → {pn:>12,.0f}  (vig {vg})')
print(f'\nen el Excel y NO cargados: {len(solo_nueva)}')
for cod, desc, pn in solo_nueva[:40]:
    print(f'    {cod}  {desc[:50]:<50} {pn:>12,.0f}')
print(f'cargados y NO en el Excel: {len(solo_act)}')
for cod, desc, pa in solo_act[:40]:
    print(f'    {cod}  {(desc or "")[:50]:<50} {pa:>12,.0f}')
