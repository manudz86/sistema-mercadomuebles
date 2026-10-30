#!/usr/bin/env python3
"""Comprueba que el feed refleje el estado ACTUAL de la base.

Arma el feed de cero y, para cada item, compara contra lo que dice la base en
este momento:
  - availability  vs  get_stock_disponible_sku()
  - price         vs  precio_base

Sirve para demostrar que los datos se consultan en cada build y no quedan
congelados. Solo lectura.
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')

G = '{http://base.google.com/ns/1.0}'


def main():
    from flask import Flask
    import tienda_bp as tb

    app = Flask(__name__, root_path='/home/cannon/app',
                static_folder='/home/cannon/app/static',
                template_folder='/home/cannon/app/templates')
    app.secret_key = 'frescura'
    app.register_blueprint(tb.tienda_bp, url_prefix='/tienda')

    with app.test_request_context('/tienda/feed/meta.xml?nocache=1'):
        xml = app.ensure_sync(tb.feed_meta)().get_data(as_text=True)

        raiz = ET.fromstring(xml)
        items = raiz.findall('./channel/item')

        db = tb.get_db(); cur = db.cursor()

        disc = {'in stock': 0, 'out of stock': 0}
        malos_stock, malos_precio, sin_fila = [], [], []

        for it in items:
            sku = it.find(G + 'id').text
            avail = it.find(G + 'availability').text
            disc[avail] = disc.get(avail, 0) + 1
            precio_feed = float(re.match(r'([0-9.]+)', it.find(G + 'price').text).group(1))

            # Stock real en este instante
            cur.execute('SELECT sku FROM productos_base WHERE sku=%s', (sku,))
            es_base = cur.fetchone() is not None

            if es_base:
                stock = tb.get_stock_disponible_sku(cur, sku)
                cur.execute('SELECT precio_base FROM productos_base WHERE sku=%s', (sku,))
                p_db = float((cur.fetchone() or {}).get('precio_base') or 0)
                if p_db and abs(p_db - precio_feed) > 0.5:
                    malos_precio.append((sku, precio_feed, p_db))
            else:
                # Compuesto: el stock sale de la vista stock_compuestos
                cur.execute('SELECT stock_disponible FROM stock_compuestos WHERE sku=%s', (sku,))
                row = cur.fetchone()
                if row is None:
                    sin_fila.append(sku)
                    continue
                stock = int(row['stock_disponible'] or 0)

            esperado = 'in stock' if stock > 0 else 'out of stock'
            # Los conjuntos se limitan por el stock de la base que los compone,
            # así que el feed puede decir out of stock con el colchón en stock.
            if avail != esperado and not (avail == 'out of stock' and stock > 0):
                malos_stock.append((sku, avail, stock, esperado))

        cur.close(); db.close()

    print(f'items en el feed         : {len(items)}')
    print(f'  in stock               : {disc.get("in stock", 0)}')
    print(f'  out of stock           : {disc.get("out of stock", 0)}')
    print()
    print(f'precio feed != precio DB : {len(malos_precio)}')
    for s, pf, pd in malos_precio[:10]:
        print(f'  ✗ {s}: feed {pf:.0f} / DB {pd:.0f}')
    print(f'availability incoherente : {len(malos_stock)}')
    for s, a, st, e in malos_stock[:10]:
        print(f'  ✗ {s}: feed "{a}" pero stock={st} (esperado "{e}")')
    if sin_fila:
        print(f'compuestos sin fila en stock_compuestos: {len(sin_fila)} -> {sin_fila[:5]}')
    print()
    ok = not malos_precio and not malos_stock
    print('RESULTADO:', 'precio y disponibilidad coinciden con la base'
          if ok else 'HAY DESFASAJES')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
