#!/usr/bin/env python3
"""Regenera las fotos premium desde los originales del catalogo, SIN deformar.

Solo redimensiona proporcionalmente (nada de estirar ni agregar lienzo). El
encuadre se resuelve por CSS: la card usa una relacion de aspecto parecida a la
de la foto, asi el recorte es minimo.

Opcionalmente recorta un margen superior (--top N) en las fotos con mucha pared
vacia arriba, para que el conjunto quede mejor centrado.

Uso:
    venv/bin/python3 scripts/premium_regenerar_fotos.py
    venv/bin/python3 scripts/premium_regenerar_fotos.py --top renovation=0.10
"""
import os
import sys

from PIL import Image

ORIG = '/tmp/cat_imgs'
DEST = 'static/img/premium'
ALTO = 1250

PARES = [
    ('pag15_Image323.jpg', 'doral-pillow.jpg',            'doral'),
    ('pag16_Image347.jpg', 'sublime-europillow.jpg',      'sublime'),
    ('pag7_Image126.jpg',  'exclusive-pillow.jpg',        'exclusive'),
    ('pag10_Image199.jpg', 'renovation-europillow.jpg',   'renovation'),
]


def main():
    tops = {}
    if '--top' in sys.argv:
        for par in sys.argv[sys.argv.index('--top') + 1].split(','):
            k, v = par.split('=')
            tops[k.strip()] = float(v)

    os.makedirs(DEST, exist_ok=True)
    for orig, dest, clave in PARES:
        ruta = os.path.join(ORIG, orig)
        if not os.path.isfile(ruta):
            print(f'  FALTA el original {ruta}')
            continue
        im = Image.open(ruta).convert('RGB')
        antes = f'{im.size[0]}x{im.size[1]} ({im.size[0]/im.size[1]:.2f})'

        # recorte superior opcional (pared vacia), sin deformar nada
        top = tops.get(clave, 0)
        if top:
            w, h = im.size
            im = im.crop((0, int(h * top), w, h))

        nw = int(round(im.size[0] * ALTO / im.size[1]))
        im = im.resize((nw, ALTO), Image.LANCZOS)
        salida = os.path.join(DEST, dest)
        im.save(salida, 'JPEG', quality=87, optimize=True)
        kb = os.path.getsize(salida) // 1024
        extra = f'  (recorte sup. {int(top*100)}%)' if top else ''
        print(f'  {dest:<28} {antes} -> {im.size[0]}x{im.size[1]} '
              f'({im.size[0]/im.size[1]:.2f})  {kb} KB{extra}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
