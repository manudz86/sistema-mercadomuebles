#!/usr/bin/env python3
"""Normaliza a mano las imágenes del feed de Meta.

En régimen normal NO hace falta correrlo: job_imagenes_catalogo (scheduler,
cada 10 min) procesa las fotos nuevas y las modificadas, y el feed además
verifica cada imagen al publicar. Este script sirve para forzar el trabajo en
el momento, por ejemplo después de cargar muchas fotos de golpe.

La lógica vive en tienda_bp.py (feed_regenerar_todas), para que el script, el
job y el feed usen exactamente las mismas reglas de nombres y de vencimiento.

Uso:
    venv/bin/python3 scripts/generar_imagenes_catalogo.py
    venv/bin/python3 scripts/generar_imagenes_catalogo.py --forzar
"""
import sys

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')


def main():
    forzar = '--forzar' in sys.argv
    try:
        import PIL  # noqa: F401
    except ImportError:
        print('Falta Pillow: venv/bin/pip install Pillow'); return 1

    import tienda_bp as tb

    st = tb.feed_regenerar_todas(forzar=forzar)

    print(f'SKU publicados       : {st["skus"]}')
    print(f'imagenes generadas   : {st["generadas"]}')
    print(f'ya estaban al dia    : {st["al_dia"]}')
    print(f'fallidas             : {st["fallidas"]}')
    print(f'SKU sin ninguna foto : {st["sin_foto"]}  (quedan FUERA del feed)')

    if st['sin_foto']:
        # Detalle de cuáles, para saber a qué producto cargarle foto
        db = tb.get_db(); cur = db.cursor()
        try:
            faltantes = [s for s in tb.feed_skus_publicados(cur)
                         if not tb.feed_fotos_origen(s)]
        finally:
            cur.close(); db.close()
        print()
        print('Sin foto (cargales una para que entren al feed):')
        for s in faltantes:
            print(f'  {s}')

    print()
    print(f'destino: {tb.FEED_IMG_DIR}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
