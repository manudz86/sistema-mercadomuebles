#!/usr/bin/env python3
"""Clientes con carrito abandonado en un período (hora AR), solo lectura.

Uso: venv/bin/python scripts/analizar_abandonados_periodo.py "2026-11-02 00:00" "2026-11-05 23:59:59"

Abandonado = quedó en pedidos_pendientes (el cobro exitoso borra la fila) y el
cliente NO tiene una venta (por email o DNI, cualquier canal) desde el inicio del
período hasta hoy. Se agrupa por cliente (email). "Elegible" = tenía algún
colchón o sommier (no solo almohadas/bases).
"""
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, '/home/cannon/app/scripts')
from _common import conectar_db  # noqa: E402

ALMOHADAS = {'CLASICA', 'SUBLIME', 'CERVICAL', 'RENOVATION', 'PLATINO', 'DORAL',
             'DUAL', 'EXCLUSIVE', 'TRIANGULO', 'CONTOUR'}

if len(sys.argv) != 3:
    print(__doc__)
    sys.exit(2)
fmt = '%Y-%m-%d %H:%M:%S'


def parse(s):
    s = s.strip()
    return datetime.strptime(s if len(s) > 16 else s + ':00', fmt)


desde_ar, hasta_ar = parse(sys.argv[1]), parse(sys.argv[2])
desde_utc, hasta_utc = desde_ar + timedelta(hours=3), hasta_ar + timedelta(hours=3)

conn = conectar_db(solo_lectura=True)
cur = conn.cursor()
cur.execute("SELECT tipo, sku FROM productos_base")
tipo_sku = {}
for row in cur.fetchall():
    row = row if isinstance(row, dict) else {'tipo': row[0], 'sku': row[1]}
    tipo_sku[str(row['sku']).upper()] = row['tipo']


def es_colchon_o_sommier(sku):
    s = str(sku or '').strip().upper()
    if not s or s in ALMOHADAS:
        return False
    if len(s) > 1 and s[0] == 'S' and s[1].isalpha():
        return True                                   # conjunto
    return tipo_sku.get(s) == 'colchon' or tipo_sku.get(s.replace('_DEP', '')) == 'colchon'


cur.execute("SELECT ref, carrito_json, cliente_json, fecha_creacion FROM pedidos_pendientes "
            "WHERE fecha_creacion BETWEEN %s AND %s", (desde_utc.strftime(fmt), hasta_utc.strftime(fmt)))
pend = cur.fetchall()

# ventas desde el inicio del período (fecha_venta se guarda en hora AR)
cur.execute("SELECT LOWER(TRIM(email_cliente)) e, TRIM(dni_cliente) d FROM ventas WHERE fecha_venta >= %s",
            (desde_ar.strftime(fmt),))
mails_compra, dnis_compra = set(), set()
for v in cur.fetchall():
    v = v if isinstance(v, dict) else {'e': v[0], 'd': v[1]}
    if v['e']:
        mails_compra.add(v['e'])
    if v['d']:
        dnis_compra.add(v['d'])

clientes = defaultdict(lambda: {'eleg': False, 'monto': 0.0, 'dias': set(), 'dni': '', 'n': 0})
sin_email = 0
for p in pend:
    p = p if isinstance(p, dict) else dict(zip(['ref', 'carrito_json', 'cliente_json', 'fecha_creacion'], p))
    try:
        car = json.loads(p['carrito_json'] or '[]')
        cli = json.loads(p['cliente_json'] or '{}') or {}
    except Exception:
        continue
    email = (cli.get('email') or '').strip().lower()
    if not email:
        sin_email += 1
        continue
    c = clientes[email]
    c['n'] += 1
    c['dni'] = c['dni'] or str(cli.get('dni') or '').strip()
    c['dias'].add((p['fecha_creacion'] - timedelta(hours=3)).strftime('%d/%m'))
    if any(es_colchon_o_sommier(i.get('sku')) for i in car):
        c['eleg'] = True
    monto = sum(float(i.get('precio') or 0) * int(i.get('cantidad') or 0) for i in car)
    c['monto'] = max(c['monto'], monto)

compraron = {e for e, c in clientes.items() if e in mails_compra or (c['dni'] and c['dni'] in dnis_compra)}
abandon = {e: c for e, c in clientes.items() if e not in compraron}
eleg = {e: c for e, c in abandon.items() if c['eleg']}

print(f'Período AR: {desde_ar} → {hasta_ar}')
print(f'Pedidos pendientes en el período: {len(pend)} (sin email: {sin_email})')
print(f'Clientes distintos (por email): {len(clientes)}')
print(f'  después compraron (email/DNI en ventas): {len(compraron)}')
print(f'  siguen sin comprar: {len(abandon)}')
print(f'    con colchón o sommier: {len(eleg)}  ← ELEGIBLES')
print(f'    solo almohadas/bases: {len(abandon) - len(eleg)}')
print(f'  monto de los elegibles (carrito más grande de cada uno): ${sum(c["monto"] for c in eleg.values()):,.0f}'.replace(',', '.'))
por_dia = defaultdict(int)
for c in eleg.values():
    por_dia[min(c['dias'], key=lambda d: (d[3:], d[:2]))] += 1
print('  elegibles por día del primer intento:', dict(sorted(por_dia.items())))
