#!/usr/bin/env python3
"""Da de alta un combo de ML como producto compuesto.

Los combos de ML (CPR8020+ = colchon + almohada) no existian como producto:
normalizar_sku_ml les recortaba el sufijo y la almohada nunca se descontaba
del stock. Creandolos como compuesto, descontar_stock_item los descompone
solo, y normalizar_sku_ml deja de recortarlos porque el SKU pasa a existir.

Se crean con activo=0, que es la convencion de los otros 12 combos '+' que ya
estan en el sistema: se venden en ML pero no se publican en la tienda web.

Sin --aplicar solo muestra lo que haria.

Uso:
    scripts/crear_combo_ml.py CPR8020+ "Colchón Princess 20cm 80x190 + 1 Almohada" CPR8020:1 PLATINO:1
    scripts/crear_combo_ml.py CPR8020+ "..." CPR8020:1 PLATINO:1 --aplicar
"""
import argparse
import os
import sys

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')


def conectar():
    return pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER'), password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME'), cursorclass=pymysql.cursors.DictCursor)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sku')
    ap.add_argument('nombre')
    ap.add_argument('componentes', nargs='+', help='SKU:cantidad, ej CPR8020:1 PLATINO:1')
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()

    comps = []
    for c in a.componentes:
        if ':' not in c:
            print(f'Componente mal escrito: {c!r}. Formato SKU:cantidad'); return 1
        s, n = c.rsplit(':', 1)
        comps.append((s.strip().upper(), int(n)))

    cn = conectar(); cur = cn.cursor()
    try:
        cur.execute('SELECT id FROM productos_compuestos WHERE sku=%s', (a.sku,))
        if cur.fetchone():
            print(f'{a.sku} ya existe como compuesto. Nada que hacer.'); return 1
        cur.execute('SELECT id FROM productos_base WHERE sku=%s', (a.sku,))
        if cur.fetchone():
            print(f'{a.sku} ya existe como producto base. Abortado.'); return 1

        # Resolver componentes y precio
        total = 0.0
        resueltos = []
        for s, n in comps:
            cur.execute('SELECT id, sku, nombre, precio_base FROM productos_base WHERE sku=%s', (s,))
            r = cur.fetchone()
            if not r:
                print(f'No existe el componente {s!r}. Abortado.'); return 1
            total += float(r['precio_base'] or 0) * n
            resueltos.append((r, n))

        print(f'compuesto .. {a.sku}')
        print(f'nombre ..... {a.nombre}')
        print(f'activo ..... 0  (combo de ML, no se publica en la tienda)')
        print(f'precio ..... ${total:,.0f}'.replace(',', '.') + '  (suma de componentes)')
        print('componentes:')
        for r, n in resueltos:
            print(f'   {n}x {r["sku"]:<12} {r["nombre"][:40]:<40} '
                  f'${float(r["precio_base"] or 0):,.0f}'.replace(',', '.'))

        if not a.aplicar:
            print('\n>> Vista previa. Agrega --aplicar para crearlo.')
            return 0

        cur.execute("""INSERT INTO productos_compuestos (sku, nombre, precio_base, activo)
                       VALUES (%s, %s, %s, 0)""", (a.sku, a.nombre, round(total, 2)))
        nuevo_id = cur.lastrowid
        for r, n in resueltos:
            cur.execute("""INSERT INTO componentes
                           (producto_compuesto_id, producto_base_id, cantidad_necesaria)
                           VALUES (%s, %s, %s)""", (nuevo_id, r['id'], n))
        cn.commit()
        print(f'\ncreado con id {nuevo_id} y {len(resueltos)} componentes')

        cur.execute("""SELECT pc.sku, pc.nombre, pc.activo, pb.sku comp, c.cantidad_necesaria
                       FROM productos_compuestos pc
                       JOIN componentes c ON c.producto_compuesto_id = pc.id
                       JOIN productos_base pb ON pb.id = c.producto_base_id
                       WHERE pc.id = %s""", (nuevo_id,))
        print('verificacion en base:')
        for r in cur.fetchall():
            print(f'   {r["sku"]} (activo={r["activo"]}) -> {r["cantidad_necesaria"]}x {r["comp"]}')
    finally:
        cur.close(); cn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
