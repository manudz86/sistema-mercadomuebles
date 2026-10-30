#!/usr/bin/env python3
"""Audita las fotos de los productos que van al feed de Meta.

Para cada SKU publicado en la tienda busca su primera foto con la MISMA lógica
que get_fotos_producto() (tabla productos_fotos, con fallback a archivos
numerados y a los SKU sin sufijo _DEP/_FULL) y reporta si existe y qué tamaño
tiene. Meta exige 500x500 como mínimo para anuncios de catálogo.

Solo lectura: no escribe ni convierte nada.
"""
import os
import sys
from collections import Counter

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')

RAIZ = '/home/cannon/app'
IMGDIR = os.path.join(RAIZ, 'static', 'img', 'productos')
MIN_META = 500

# Mismos criterios que usa la tienda para decidir qué publica
CONSULTAS = {
    'colchon': """SELECT sku, nombre FROM productos_base
                  WHERE tipo='colchon' AND COALESCE(activo,1)=1
                    AND medida IS NOT NULL AND sku NOT LIKE '%%_FULL%%'""",
    'almohada': """SELECT sku, nombre FROM productos_base
                   WHERE activo=1 AND tipo='almohada' AND precio_base>0""",
    'base': """SELECT sku, nombre FROM productos_base
               WHERE activo=1 AND tipo='base' AND precio_base>0""",
    'compuesto': """SELECT sku, nombre FROM productos_compuestos WHERE activo=1""",
}


def conectar():
    return pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME'),
        cursorclass=pymysql.cursors.DictCursor,
    )


def skus_a_probar(sku):
    """Igual que get_fotos_producto: prueba el SKU y su variante sin sufijo."""
    out = [sku]
    for suf in ('_DEP', '_FULL'):
        if sku.endswith(suf):
            out.append(sku[:-len(suf)])
            break
    return out


def primera_foto(cur, sku):
    """Devuelve la ruta absoluta de la primera foto, o None."""
    for s in skus_a_probar(sku):
        cur.execute(
            'SELECT filename FROM productos_fotos WHERE sku=%s ORDER BY orden, id', (s,))
        for r in cur.fetchall():
            p = os.path.join(IMGDIR, s, r['filename'])
            if os.path.exists(p):
                return p
        # Fallback: archivos numerados
        for n in range(1, 10):
            for ext in ('png', 'jpg', 'jpeg', 'webp'):
                p = os.path.join(IMGDIR, s, f'{n}.{ext}')
                if os.path.exists(p):
                    return p
    return None


def main():
    try:
        from PIL import Image
    except ImportError:
        print('Falta Pillow (venv/bin/pip install Pillow)'); return 1

    cn = conectar()
    cur = cn.cursor()

    sin_foto, chicas, ok = [], [], []
    tamanos = Counter()
    total = 0

    for cat, sql in CONSULTAS.items():
        cur.execute(sql)
        for row in cur.fetchall():
            total += 1
            sku = row['sku']
            ruta = primera_foto(cur, sku)
            if not ruta:
                sin_foto.append((cat, sku, row['nombre']))
                continue
            try:
                with Image.open(ruta) as im:
                    w, h = im.size
            except Exception as e:
                sin_foto.append((cat, sku, f'ILEGIBLE: {e}'))
                continue
            tamanos[f'{w}x{h}'] += 1
            if min(w, h) < MIN_META:
                chicas.append((cat, sku, w, h))
            else:
                ok.append((cat, sku, w, h))

    cur.close(); cn.close()

    print(f'Productos publicados       : {total}')
    print(f'  con foto >= {MIN_META}px      : {len(ok)}')
    print(f'  con foto por debajo del min: {len(chicas)}')
    print(f'  SIN foto                   : {len(sin_foto)}')
    print()
    print('Tamaños mas comunes:')
    for t, n in tamanos.most_common(12):
        w, h = (int(x) for x in t.split('x'))
        marca = '' if min(w, h) >= MIN_META else '  <-- insuficiente'
        print(f'  {t:>12}  x{n}{marca}')
    if sin_foto:
        print()
        print(f'SIN foto ({len(sin_foto)}):')
        for cat, sku, nom in sin_foto[:25]:
            print(f'  [{cat}] {sku} — {str(nom)[:55]}')
        if len(sin_foto) > 25:
            print(f'  ... y {len(sin_foto)-25} mas')
    return 0


if __name__ == '__main__':
    sys.exit(main())
