#!/usr/bin/env python3
"""Solo lectura. Envíos por mes (últimos N meses completos + el actual): Delega (almohadas /
compac / mixto, por canal), Zippin (Zipnova / ME1) y Flex. Excluye canceladas.
Uso: venv/bin/python scripts/analizar_envios_delega.py [MESES=4]
"""
import os
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, '/home/cannon/app')
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import pymysql  # noqa: E402

meses = int(sys.argv[1]) if len(sys.argv) > 1 else 4
hoy = date.today()
y, m = hoy.year, hoy.month - meses
while m <= 0:
    m += 12
    y -= 1
desde = date(y, m, 1)

con = pymysql.connect(host=os.getenv('DB_HOST', 'localhost'), user=os.getenv('DB_USER'),
                      password=os.getenv('DB_PASSWORD'), database=os.getenv('DB_NAME', 'inventario_cannon'),
                      cursorclass=pymysql.cursors.DictCursor)
cur = con.cursor()
cur.execute("SELECT sku FROM productos_base WHERE tipo='almohada'")
ALM = {r['sku'].upper() for r in cur.fetchall()}
cur.execute("""SELECT pc.sku FROM productos_compuestos pc JOIN componentes c ON c.producto_compuesto_id=pc.id
               JOIN productos_base pb ON pb.id=c.producto_base_id GROUP BY pc.sku
               HAVING SUM(pb.tipo<>'almohada')=0""")
ALM |= {r['sku'].upper() for r in cur.fetchall()}
cur.execute("""SELECT v.id, DATE_FORMAT(v.fecha_venta,'%%Y-%%m') mes, v.canal, v.metodo_envio, iv.sku
               FROM ventas v LEFT JOIN items_venta iv ON iv.venta_id=v.id
               WHERE v.fecha_venta >= %s AND v.metodo_envio IN ('Delega','Zippin','Flex')
                 AND IFNULL(v.estado_entrega,'') <> 'cancelada' AND IFNULL(v.estado,'') <> 'cancelada'""", (desde,))
ventas = {}
for r in cur.fetchall():
    v = ventas.setdefault(r['id'], {'mes': r['mes'], 'canal': r['canal'], 'metodo': r['metodo_envio'], 'skus': set()})
    if r['sku']:
        v['skus'].add(r['sku'].upper())


def clase(skus):
    es_c = lambda s: s.startswith(('CCO', 'CCP'))  # noqa: E731
    if skus and all(s in ALM for s in skus):
        return 'almohadas'
    if skus and all(es_c(s) for s in skus):
        return 'compac'
    if skus and all(s in ALM or es_c(s) for s in skus):
        return 'compac+almohada'
    return 'otro'


t = defaultdict(lambda: defaultdict(int))
for v in ventas.values():
    k = v['mes']
    t[k][v['metodo']] += 1
    if v['metodo'] == 'Delega':
        t[k]['D_' + clase(v['skus'])] += 1
        t[k]['D_canal_' + ('ML' if v['canal'] == 'Mercado Libre' else 'otros')] += 1
    if v['metodo'] == 'Zippin':
        t[k]['Z_' + ('ML' if v['canal'] == 'Mercado Libre' else 'otros')] += 1

cols = [('Delega', 'Delega'), ('D_almohadas', 'D alm'), ('D_compac', 'D compac'),
        ('D_compac+almohada', 'D comp+alm'), ('D_otro', 'D otro'), ('D_canal_ML', 'D de ML'),
        ('D_canal_otros', 'D web/ext'), ('Zippin', 'Zipnova'), ('Z_ML', 'Zip ML'), ('Z_otros', 'Zip web'),
        ('Flex', 'Flex')]
print(f"desde {desde} (mes actual {hoy:%Y-%m} parcial, al {hoy:%d/%m})")
print('mes      ' + ''.join(f'{c:>11}' for _, c in cols))
completos = [k for k in sorted(t) if k != f'{hoy:%Y-%m}']
for k in sorted(t):
    print(f'{k}  ' + ''.join(f'{t[k][c]:>11}' for c, _ in cols))
print(f'PROM {len(completos)}m ' + ''.join(f'{sum(t[k][c] for k in completos)/max(1, len(completos)):>11.1f}' for c, _ in cols))
