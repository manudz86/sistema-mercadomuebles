#!/usr/bin/env python3
"""Carritos que llegaron a pagar (pedidos_pendientes) y no terminaron en venta.
Solo lectura. Muestra cuántos hay, qué SKUs/forma tienen los items y qué datos
del cliente se guardan (solo nombres de campos, no los valores).

Uso: venv/bin/python scripts/analizar_carritos_abandonados.py [dias=15]
"""
import json
import sys
from collections import Counter

sys.path.insert(0, '/home/cannon/app/scripts')
from _common import conectar_db  # noqa: E402

dias = int(sys.argv[1]) if len(sys.argv) > 1 else 15
conn = conectar_db(solo_lectura=True)
cur = conn.cursor()
cur.execute("SELECT ref, carrito_json, cliente_json, fecha_creacion FROM pedidos_pendientes "
            "WHERE fecha_creacion >= NOW() - INTERVAL %s DAY ORDER BY fecha_creacion DESC", (dias,))
rows = cur.fetchall()
print('pedidos_pendientes en', dias, 'días:', len(rows))

item_keys, cli_keys, skus = Counter(), Counter(), Counter()
con_email, solo_alm = 0, 0
for r in rows:
    r = r if isinstance(r, dict) else dict(zip(['ref', 'carrito_json', 'cliente_json', 'fecha_creacion'], r))
    try:
        car = json.loads(r['carrito_json'] or '[]')
        cli = json.loads(r['cliente_json'] or '{}')
    except Exception:
        continue
    for it in car:
        item_keys.update(it.keys())
        s = str(it.get('sku') or '')
        forma = ('S' if s.startswith('S') else 'C' if s.startswith('C') else s[:1]) + \
                ('+N' if '+' in s else '') + ('_DEP' if '_DEP' in s else '')
        skus[forma] += 1
    cli_keys.update(cli.keys() if isinstance(cli, dict) else [])
    if isinstance(cli, dict) and cli.get('email'):
        con_email += 1
    if car and all(str(i.get('sku', '')).upper().startswith('A') for i in car):
        solo_alm += 1
print('campos de item:', dict(item_keys))
print('campos de cliente:', sorted(cli_keys))
print('formas de SKU:', dict(skus))
print('con email:', con_email, '| solo almohadas (sku A*):', solo_alm)
print('ej refs:', [ (r['ref'] if isinstance(r, dict) else r[0]) for r in rows[:3]])
