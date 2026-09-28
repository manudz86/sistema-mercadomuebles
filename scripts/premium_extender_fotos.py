#!/usr/bin/env python3
"""Extiende verticalmente las fotos premium para que no se recorten a lo ancho.

Las cards son mas altas que anchas (ratio ~0.6) y las fotos del catalogo son mas
panoramicas (~0.84): con object-fit:cover CSS recorta los costados y corta el
sommier. Agregando lienzo arriba y abajo (estirando las filas de borde, que son
pared y piso) la foto queda mas vertical y entra completa a lo ancho.

Trabaja sobre los ORIGINALES en /tmp/cat_imgs y reescribe static/img/premium/.

Uso:  venv/bin/python3 scripts/premium_extender_fotos.py [ratio]   (default 0.62)
"""
import os
import sys

from PIL import Image

ORIG = '/tmp/cat_imgs'
DEST = 'static/img/premium'
PARES = [
    ('pag15_Image323.jpg', 'doral-pillow.jpg'),
    ('pag16_Image347.jpg', 'sublime-europillow.jpg'),
    ('pag7_Image126.jpg',  'exclusive-pillow.jpg'),
    ('pag10_Image199.jpg', 'renovation-europillow.jpg'),
]
BORDE = 6          # filas de pixeles del borde que se estiran
ALTO_FINAL = 1400  # alto de salida


def extender(im, ratio_obj):
    """Agrega lienzo arriba/abajo estirando las filas de borde."""
    w, h = im.size
    h_obj = int(round(w / ratio_obj))
    if h_obj <= h:
        return im
    extra = h_obj - h
    # el producto esta en la mitad inferior: damos mas aire arriba que abajo
    arriba = int(extra * 0.72)
    abajo = extra - arriba

    out = Image.new('RGB', (w, h_obj))
    if arriba:
        tira = im.crop((0, 0, w, BORDE)).resize((w, arriba), Image.LANCZOS)
        out.paste(tira, (0, 0))
    out.paste(im, (0, arriba))
    if abajo:
        tira = im.crop((0, h - BORDE, w, h)).resize((w, abajo), Image.LANCZOS)
        out.paste(tira, (0, arriba + h))
    return out


def main():
    ratio = float(sys.argv[1]) if len(sys.argv) > 1 else 0.62
    os.makedirs(DEST, exist_ok=True)
    for orig, dest in PARES:
        ruta = os.path.join(ORIG, orig)
        if not os.path.isfile(ruta):
            print(f'  FALTA el original {ruta}')
            continue
        im = Image.open(ruta).convert('RGB')
        antes = f'{im.size[0]}x{im.size[1]} ({im.size[0]/im.size[1]:.2f})'
        im = extender(im, ratio)
        # normalizar alto de salida
        if im.size[1] != ALTO_FINAL:
            nw = int(round(im.size[0] * ALTO_FINAL / im.size[1]))
            im = im.resize((nw, ALTO_FINAL), Image.LANCZOS)
        salida = os.path.join(DEST, dest)
        im.save(salida, 'JPEG', quality=86, optimize=True)
        kb = os.path.getsize(salida) // 1024
        print(f'  {dest:<28} {antes} -> {im.size[0]}x{im.size[1]} '
              f'({im.size[0]/im.size[1]:.2f})  {kb} KB')
    return 0


if __name__ == '__main__':
    sys.exit(main())
