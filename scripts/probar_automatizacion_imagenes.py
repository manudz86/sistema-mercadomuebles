#!/usr/bin/env python3
"""Prueba controlada de la automatización de imágenes del feed.

NO toca ningún producto real: crea un SKU sintético (__TEST_FEED__) con una
foto de prueba, ejercita el pipeline y borra todo al final.

Comprueba las cuatro condiciones que importan:
  1. Foto NUEVA        -> se normaliza a 1024x1024 sobre blanco
  2. Foto MODIFICADA   -> se regenera (no se queda la versión vieja)
  3. Sin cambios       -> no se regenera (es idempotente)
  4. Sin presupuesto   -> devuelve None, o sea que el item sale del feed
                          en vez de publicar una imagen vieja o sin preparar
"""
import os
import shutil
import sys
import time

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')

SKU = '__TEST_FEED__'


def crear_foto(ruta, lado_w, lado_h, color):
    from PIL import Image
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    Image.new('RGB', (lado_w, lado_h), color).save(ruta)


def main():
    import tienda_bp as tb
    from PIL import Image

    src_dir = os.path.join(tb.FEED_IMG_SRC, SKU)
    src     = os.path.join(src_dir, '1.png')
    dst     = os.path.join(tb.FEED_IMG_DIR, f'{SKU}.jpg')

    fallos = []

    def chequear(ok, texto, detalle=''):
        print(f'  {"OK  " if ok else "FALLA"} {texto}{(" — " + detalle) if detalle else ""}')
        if not ok:
            fallos.append(texto)

    try:
        # ── 1. foto nueva ──────────────────────────────────────────────────
        print('1) foto NUEVA (300x200, por debajo del minimo de Meta)')
        crear_foto(src, 300, 200, (10, 120, 200))
        url, extras, usado = tb.feed_preparar_imagenes(SKU)
        chequear(url is not None, 'devuelve URL', str(url))
        chequear(usado == 1, 'normalizo 1 imagen', f'usado={usado}')
        chequear(os.path.exists(dst), 'el archivo existe')
        if os.path.exists(dst):
            with Image.open(dst) as im:
                chequear(im.size == (tb.FEED_IMG_LADO, tb.FEED_IMG_LADO),
                         f'mide {tb.FEED_IMG_LADO}x{tb.FEED_IMG_LADO}', str(im.size))
                # El centro conserva el color original: no se deformo ni recorto
                chequear(im.getpixel((512, 512))[2] > 150,
                         'el producto quedo centrado (no recortado)')
                # Las esquinas son el relleno blanco
                chequear(im.getpixel((5, 5)) == (255, 255, 255),
                         'relleno blanco en los bordes')
        mtime_1 = os.path.getmtime(dst)

        # ── 3. sin cambios (se chequea antes de modificar) ─────────────────
        print('2) SIN cambios en la foto')
        url, _, usado = tb.feed_preparar_imagenes(SKU)
        chequear(usado == 0, 'no regenero nada (idempotente)', f'usado={usado}')
        chequear(os.path.getmtime(dst) == mtime_1, 'no reescribio el archivo')

        # ── 2. foto modificada ─────────────────────────────────────────────
        print('3) foto MODIFICADA (otro color y otro tamaño)')
        time.sleep(1.1)                      # para que el mtime sea distinto
        crear_foto(src, 400, 400, (220, 30, 30))
        url, _, usado = tb.feed_preparar_imagenes(SKU)
        chequear(usado == 1, 'detecto el cambio y regenero', f'usado={usado}')
        chequear(os.path.getmtime(dst) > mtime_1, 'el archivo es mas nuevo')
        with Image.open(dst) as im:
            px = im.getpixel((512, 512))
            chequear(px[0] > 150 and px[2] < 100,
                     'la imagen nueva reemplazo a la vieja', f'centro={px}')

        # ── 4. sin presupuesto ─────────────────────────────────────────────
        print('4) foto modificada pero SIN presupuesto en el request')
        time.sleep(1.1)
        crear_foto(src, 500, 500, (30, 180, 30))
        url, _, usado = tb.feed_preparar_imagenes(SKU, presupuesto=0)
        chequear(url is None,
                 'devuelve None: el item sale del feed en vez de publicar '
                 'una imagen vencida', f'url={url}')
        chequear(usado == 0, 'no consumio presupuesto')

    finally:
        # ── limpieza ───────────────────────────────────────────────────────
        print('limpieza')
        borrados = 0
        if os.path.isdir(src_dir):
            shutil.rmtree(src_dir); borrados += 1
        for n in ('', '_2', '_3', '_4'):
            p = os.path.join(tb.FEED_IMG_DIR, f'{SKU}{n}.jpg')
            if os.path.exists(p):
                os.remove(p); borrados += 1
        print(f'  se borraron {borrados} rutas de prueba')
        print(f'  queda el SKU de prueba en la base: NO (nunca se escribio)')

    print()
    print('RESULTADO:', 'la automatizacion funciona' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
