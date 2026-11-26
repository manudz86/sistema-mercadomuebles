#!/usr/bin/env python3
"""SOLO LECTURA: para las últimas N ventas ML del sistema, compara el order_id (lo que usamos
en numero_venta = ML-{order_id}) con el pack_id que ML muestra en su panel cuando la compra
es un carrito. Uso: venv/bin/python scripts/analizar_pack_vs_orden.py [N=150]
"""
import json
import sys
import time

import pymysql
import requests
from dotenv import dotenv_values

N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
env = dotenv_values('/home/cannon/app/config/.env')
db = pymysql.connect(host=env.get('DB_HOST', 'localhost'), user=env.get('DB_RO_USER', 'cannon_ro'),
                     password=env.get('DB_RO_PASSWORD', ''), port=int(env.get('DB_PORT') or 3306),
                     database=env.get('DB_NAME', 'inventario_cannon'),
                     cursorclass=pymysql.cursors.DictCursor)
cur = db.cursor()
cur.execute("SELECT valor FROM configuracion WHERE clave='ml_token'")
tok = json.loads(cur.fetchone()['valor'])['access_token']
cur.execute("SELECT id, numero_venta, fecha_venta FROM ventas WHERE numero_venta LIKE 'ML-%%' "
            "ORDER BY fecha_venta DESC LIMIT %s", (N,))
ventas = cur.fetchall()

H = {'Authorization': f'Bearer {tok}'}
con_pack, sin_pack, err = [], 0, 0
packs = {}
for v in ventas:
    oid = v['numero_venta'][3:]
    r = requests.get(f'https://api.mercadolibre.com/orders/{oid}', headers=H, timeout=15)
    if not r.ok:
        err += 1
        continue
    pid = r.json().get('pack_id')
    if pid and str(pid) != oid:
        con_pack.append((v['fecha_venta'], v['numero_venta'], pid))
        packs.setdefault(pid, []).append(v['numero_venta'])
    else:
        sin_pack += 1
    time.sleep(0.1)

print(f'ventas revisadas: {len(ventas)} | número igual a ML: {sin_pack} | con pack distinto: {len(con_pack)} | error API: {err}')
print(f'packs distintos: {len(packs)} | packs con 2+ órdenes en el sistema: {sum(1 for p in packs.values() if len(p) > 1)}')
for f, nv, pid in con_pack[:25]:
    print(f'  {f}  {nv}  → ML muestra #{pid}  (otras del mismo pack: {[x for x in packs[pid] if x != nv]})')
