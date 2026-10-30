#!/usr/bin/env python3
"""Genera las imágenes del feed de Meta a partir de las fotos de la tienda.

Meta exige 500x500 como mínimo para anuncios de catálogo y acepta hasta 8 MB.
Las fotos de la tienda van de 708x360 (por debajo del mínimo) a 8688x5792
(demasiado pesadas), así que acá se normalizan todas a un cuadrado de 1024x1024:

  - Se reduce solo si la foto excede 1024 en algún lado (nunca se amplía, para
    no inventar pixeles).
  - Se centra sobre un lienzo blanco cuadrado.

NO deforma (mantiene el aspecto) y NO recorta (agrega fondo, no quita imagen).
Escribe en static/img/catalogo/ y es idempotente: saltea las que ya están al día.

Uso:
    venv/bin/python3 scripts/generar_imagenes_catalogo.py          # genera
    venv/bin/python3 scripts/generar_imagenes_catalogo.py --forzar # regenera todo
"""
import os
import re
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv('/home/cannon/app/config/.env')

RAIZ    = '/home/cannon/app'
ORIGEN  = os.path.join(RAIZ, 'static', 'img', 'productos')
DESTINO = os.path.join(RAIZ, 'static', 'img', 'catalogo')

LADO     = 1024    # lado del cuadrado final
CALIDAD  = 88      # JPEG
MAX_EXTRA = 3      # cuántas additional_image_link generar por producto

# Mismos criterios de publicación que usa la tienda en su home
CONSULTAS = (
    """SELECT sku FROM productos_base
       WHERE tipo='colchon' AND COALESCE(activo,1)=1
         AND medida IS NOT NULL AND sku NOT LIKE '%%_FULL%%'""",
    """SELECT sku FROM productos_base
       WHERE activo=1 AND tipo='almohada' AND precio_base>0""",
    """SELECT sku FROM productos_base
       WHERE activo=1 AND tipo='base' AND precio_base>0""",
    """SELECT sku FROM productos_compuestos WHERE activo=1""",
)


def conectar():
    return pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME'),
        cursorclass=pymysql.cursors.DictCursor,
    )


def nombre_archivo(sku):
    """SKU -> nombre de archivo seguro para URL. 'SEX140+2' -> 'SEX140_2'."""
    return re.sub(r'[^A-Za-z0-9_-]', '_', sku)


def skus_a_probar(sku):
    """Misma tolerancia de sufijos que get_fotos_producto() en la tienda."""
    out = [sku]
    for suf in ('_DEP', '_FULL'):
        if sku.endswith(suf):
            out.append(sku[:-len(suf)])
            break
    return out


def fotos_de(cur, sku):
    """Fotos del SKU en orden, con la misma lógica que la tienda."""
    rutas = []
    for s in skus_a_probar(sku):
        cur.execute(
            'SELECT filename FROM productos_fotos WHERE sku=%s ORDER BY orden, id', (s,))
        for r in cur.fetchall():
            p = os.path.join(ORIGEN, s, r['filename'])
            if os.path.exists(p) and p not in rutas:
                rutas.append(p)
        if rutas:
            break
        for n in range(1, 10):
            for ext in ('png', 'jpg', 'jpeg', 'webp'):
                p = os.path.join(ORIGEN, s, f'{n}.{ext}')
                if os.path.exists(p) and p not in rutas:
                    rutas.append(p)
        if rutas:
            break
    return rutas


def cuadrar(origen, destino):
    """Normaliza una foto a LADO x LADO sobre blanco. Sin deformar ni recortar."""
    from PIL import Image

    with Image.open(origen) as im:
        # Transparencia -> blanco (el JPEG no tiene alfa)
        if im.mode in ('RGBA', 'LA', 'P'):
            im = im.convert('RGBA')
            fondo = Image.new('RGBA', im.size, (255, 255, 255, 255))
            fondo.paste(im, mask=im.split()[-1])
            im = fondo.convert('RGB')
        else:
            im = im.convert('RGB')

        # Reducir solo si hace falta; nunca ampliar
        w, h = im.size
        if max(w, h) > LADO:
            escala = LADO / float(max(w, h))
            im = im.resize((max(1, int(w * escala)), max(1, int(h * escala))),
                           Image.LANCZOS)

        lienzo = Image.new('RGB', (LADO, LADO), (255, 255, 255))
        lienzo.paste(im, ((LADO - im.size[0]) // 2, (LADO - im.size[1]) // 2))
        lienzo.save(destino, 'JPEG', quality=CALIDAD, optimize=True, progressive=True)


def main():
    forzar = '--forzar' in sys.argv
    try:
        import PIL  # noqa: F401
    except ImportError:
        print('Falta Pillow: venv/bin/pip install Pillow'); return 1

    os.makedirs(DESTINO, exist_ok=True)
    cn = conectar(); cur = cn.cursor()

    skus = []
    for sql in CONSULTAS:
        cur.execute(sql)
        for r in cur.fetchall():
            if r['sku'] not in skus:
                skus.append(r['sku'])

    # Colisiones de nombre de archivo (SKUs distintos que sanitizan igual)
    vistos = {}
    for s in skus:
        vistos.setdefault(nombre_archivo(s), []).append(s)
    colisiones = {k: v for k, v in vistos.items() if len(v) > 1}
    if colisiones:
        print('ATENCION, colisión de nombres de archivo:')
        for k, v in colisiones.items():
            print(f'  {k}.jpg <- {v}')
        print()

    generadas = salteadas = sin_foto = fallidas = 0
    faltantes = []

    for sku in skus:
        rutas = fotos_de(cur, sku)
        if not rutas:
            sin_foto += 1
            faltantes.append(sku)
            continue
        base = nombre_archivo(sku)
        for i, origen in enumerate(rutas[:1 + MAX_EXTRA]):
            destino = os.path.join(DESTINO, f'{base}.jpg' if i == 0 else f'{base}_{i+1}.jpg')
            if (not forzar and os.path.exists(destino)
                    and os.path.getmtime(destino) >= os.path.getmtime(origen)):
                salteadas += 1
                continue
            try:
                cuadrar(origen, destino)
                generadas += 1
            except Exception as e:
                fallidas += 1
                print(f'  FALLO {sku} ({os.path.basename(origen)}): {e}')

    cur.close(); cn.close()

    print(f'SKU publicados       : {len(skus)}')
    print(f'imagenes generadas   : {generadas}')
    print(f'ya estaban al dia    : {salteadas}')
    print(f'fallidas             : {fallidas}')
    print(f'SKU sin ninguna foto : {sin_foto}  (quedan FUERA del feed)')
    if faltantes:
        print()
        print('Sin foto (hay que cargarles una en el catálogo para que entren al feed):')
        for s in faltantes:
            print(f'  {s}')
    print()
    print(f'destino: {DESTINO}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
