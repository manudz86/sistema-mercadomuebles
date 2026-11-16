#!/usr/bin/env python3
"""Solo lectura. Por cada producto activo (colchones de productos_base + compuestos), si tiene
publicaciones ML activas mapeadas SIN Z (Flex) y CON Z (ME1), según sku_mla_mapeo.
Uso: venv/bin/python scripts/analizar_skus_z.py
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, '/home/cannon/app')
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import pymysql  # noqa: E402

con = pymysql.connect(host=os.getenv('DB_HOST', 'localhost'), user=os.getenv('DB_USER'),
                      password=os.getenv('DB_PASSWORD'), database=os.getenv('DB_NAME', 'inventario_cannon'),
                      cursorclass=pymysql.cursors.DictCursor)
cur = con.cursor()
cur.execute("SELECT sku, nombre, tipo, linea FROM productos_base WHERE activo=1 AND tipo IN ('colchon','almohada')")
prods = {r['sku'].upper(): (r['tipo'] if r['tipo'] == 'almohada' else 'colchon ' + (r['linea'] or ''), r['nombre'])
         for r in cur.fetchall()}
cur.execute("SELECT sku, nombre FROM productos_compuestos WHERE activo=1")
for r in cur.fetchall():
    prods.setdefault(r['sku'].upper(), ('compuesto', r['nombre']))
cur.execute("SELECT UPPER(sku) sku, COUNT(*) n FROM sku_mla_mapeo WHERE activo=1 GROUP BY UPPER(sku)")
mapa = {r['sku']: r['n'] for r in cur.fetchall()}

grupos = defaultdict(list)
for sku, (tipo, nombre) in sorted(prods.items()):
    n, z = mapa.get(sku, 0), mapa.get(sku + 'Z', 0)
    estado = 'ambas' if n and z else 'solo sin Z' if n else 'solo con Z' if z else 'sin publicaciones'
    grupos[(tipo.split()[0], estado)].append((sku, n, z, nombre))

tipos = sorted({t for t, _ in grupos})
print(f"{'tipo':<11}{'ambas':>8}{'solo sin Z':>12}{'solo con Z':>12}{'sin publi':>11}")
for t in tipos:
    print(f"{t:<11}" + ''.join(f"{len(grupos.get((t, e), [])):>{w}}" for e, w in
                               (('ambas', 8), ('solo sin Z', 12), ('solo con Z', 12), ('sin publicaciones', 11))))
for (t, e), lst in sorted(grupos.items()):
    if e == 'ambas':
        continue
    print(f'\n-- {t} / {e} ({len(lst)}) --')
    for sku, n, z, nombre in lst:
        print(f'   {sku:<14} sinZ={n:<3} conZ={z:<3} {nombre}')
