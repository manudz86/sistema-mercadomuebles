#!/usr/bin/env python3
"""Cotiza Zipnova para un carrito a varios codigos postales, usando la misma
logica de armado de bultos que el checkout. Solo cotiza: no crea envios.

Uso:
    venv/bin/python3 scripts/zipnova_cotizar.py DUAL:2
    venv/bin/python3 scripts/zipnova_cotizar.py PLATINO:2 1407 1832
    venv/bin/python3 scripts/zipnova_cotizar.py DUAL:1,PLATINO:2
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
import tienda_bp as T  # noqa: E402

# CP -> (ciudad, provincia) para completar el destino que pide Zipnova
DESTINOS = {
    '1407': ('Floresta', 'Capital Federal'),
    '1606': ('Carapachay', 'Buenos Aires'),
    '1832': ('Lomas de Zamora', 'Buenos Aires'),
    '1900': ('La Plata', 'Buenos Aires'),
    '2000': ('Rosario', 'Santa Fe'),
    '5000': ('Cordoba', 'Cordoba'),
    '3400': ('Corrientes', 'Corrientes'),
    '8300': ('Neuquen', 'Neuquen'),
    '4400': ('Salta', 'Salta'),
    '9410': ('Ushuaia', 'Tierra del Fuego'),
}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    carrito = []
    precio_total = 0.0
    with app.app_context():
        db = T.get_db()
        cur = db.cursor()
        for parte in sys.argv[1].split(','):
            sku, _, cant = parte.partition(':')
            cant = int(cant or 1)
            cur.execute("SELECT sku, nombre, precio_base FROM productos_base WHERE sku=%s",
                        (sku.strip().upper(),))
            p = cur.fetchone()
            if not p:
                print(f'No existe el SKU {sku}')
                return 1
            carrito.append({'sku': p['sku'], 'nombre': p['nombre'],
                            'precio': float(p['precio_base']), 'cantidad': cant})
            precio_total += float(p['precio_base']) * cant

        cps = [a for a in sys.argv[2:] if a.isdigit()] or list(DESTINOS)

        bultos = T.armar_bultos_zipnova(carrito, db)
        db.close()

        print(f'carrito: ' + ', '.join(f"{i['cantidad']}x{i['sku']}" for i in carrito)
              + f' · valor declarado ${precio_total:,.0f}')
        print(f'bultos armados: {len(bultos)}')
        for b in bultos:
            print(f"   {b.get('weight')}kg  {b.get('width')}x{b.get('height')}x"
                  f"{b.get('length')}cm  {str(b.get('description'))[:40]}")
        print()
        print(f"{'CP':<7}{'destino':<22}{'carrier':<22}{'cobra':>10}{'te cuesta':>11}  dias")
        print('-' * 81)
        for cp in cps:
            ciudad, prov = DESTINOS.get(cp, ('', 'Buenos Aires'))
            try:
                ops = T.zipnova_cotizar(bultos, cp, ciudad, prov, int(precio_total))
            except Exception as e:
                print(f'{cp:<7}{ciudad[:21]:<22}EXC {type(e).__name__}: {e}')
                continue
            if not ops:
                print(f'{cp:<7}{ciudad[:21]:<22}sin opciones')
                continue
            if '--raw' in sys.argv:
                import json as _j
                print(_j.dumps(ops[0], ensure_ascii=False, indent=2)[:1500])
                return 0
            def _precio(o):
                return float((o.get('amounts') or {}).get('price_incl_tax') or 9e9)

            # La mas barata, que es la que el checkout termina mostrando
            op = min(ops, key=_precio)
            am = op.get('amounts') or {}
            carrier = ((op.get('carrier') or {}).get('name') or '')
            dt = op.get('delivery_time') or {}
            dias = f"{dt.get('min')}-{dt.get('max')}" if dt.get('min') else ''
            print(f'{cp:<7}{ciudad[:21]:<22}{carrier[:21]:<22}'
                  f'{_precio(op):>10,.0f}'
                  f'{float(am.get("seller_price_incl_tax") or 0):>11,.0f}  {dias}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
