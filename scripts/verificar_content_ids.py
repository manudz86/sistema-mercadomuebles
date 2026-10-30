#!/usr/bin/env python3
"""Verifica que los content_id que manda el píxel/CAPI existan en el feed.

El píxel (AddToCart / InitiateCheckout / Purchase) y la CAPI usan el SKU como
content_id, y el feed usa el SKU como <g:id>. Si algún SKU vendido no está en
el feed, Meta recibe eventos de un producto que no tiene en el catálogo y no
puede atribuirlos ni usarlos para retargeting.

Compara los SKU realmente vendidos por la tienda web contra los IDs del feed.
Solo lectura. Guarda el XML del feed en el directorio que se le pase (o /tmp).
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')

G = '{http://base.google.com/ns/1.0}'
DIAS = 180


def construir_feed():
    from flask import Flask
    import tienda_bp as tb
    app = Flask(__name__, root_path='/home/cannon/app',
                static_folder='/home/cannon/app/static',
                template_folder='/home/cannon/app/templates')
    app.secret_key = 'verificador'
    app.register_blueprint(tb.tienda_bp, url_prefix='/tienda')
    with app.test_request_context('/tienda/feed/meta.xml?nocache=1'):
        return app.ensure_sync(tb.feed_meta)().get_data(as_text=True)


def main():
    salida = sys.argv[1] if len(sys.argv) > 1 else '/tmp/feed_meta.xml'
    xml = construir_feed()
    with open(salida, 'w', encoding='utf-8') as f:
        f.write(xml)

    raiz = ET.fromstring(xml)
    ids = set()
    for it in raiz.findall('./channel/item'):
        e = it.find(G + 'id')
        if e is not None and e.text:
            ids.add(e.text)

    cn = pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER'), password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME'), cursorclass=pymysql.cursors.DictCursor)
    cur = cn.cursor()
    cur.execute(f"""
        SELECT iv.sku, COUNT(*) veces, MAX(v.fecha_venta) ultima
        FROM items_venta iv
        JOIN ventas v ON v.id = iv.venta_id
        WHERE v.canal = 'tienda_web'
          AND v.fecha_venta >= NOW() - INTERVAL {DIAS} DAY
        GROUP BY iv.sku
        ORDER BY veces DESC
    """)
    vendidos = cur.fetchall()
    cur.close(); cn.close()

    en_feed = [r for r in vendidos if r['sku'] in ids]
    faltan  = [r for r in vendidos if r['sku'] not in ids]

    print(f'feed guardado en      : {salida}')
    print(f'IDs en el feed        : {len(ids)}')
    print(f'SKU vendidos ({DIAS}d)   : {len(vendidos)}')
    print(f'  presentes en el feed: {len(en_feed)}')
    print(f'  AUSENTES del feed   : {len(faltan)}')
    if vendidos:
        cob = 100.0 * len(en_feed) / len(vendidos)
        print(f'  cobertura           : {cob:.0f}%')
    if faltan:
        print()
        print('SKU vendidos que NO estan en el feed:')
        for r in faltan:
            print(f'  {r["sku"]:<18} {r["veces"]:>3} ventas   ultima {r["ultima"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
