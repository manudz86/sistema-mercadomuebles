#!/usr/bin/env python3
"""Redimensiona y comprime banners para web, sin deformar.

Los originales de diseno vienen enormes (9000px, ~9 MB): a ese tamanio el
navegador descarga de mas y la home tarda. Esto los lleva a un ancho usable
manteniendo la proporcion.

Guarda los originales en backups/banners_originales_<fecha>/ antes de tocar.

Uso:
    venv/bin/python3 scripts/optimizar_banners.py Banners-01.jpg Banners-02.jpg
    venv/bin/python3 scripts/optimizar_banners.py --todos --ancho 2400
"""
import os
import sys
import glob
import shutil
from datetime import datetime

from PIL import Image

DIR = 'static/img/banners'
ANCHO = 2400
CALIDAD = 85


def main():
    ancho = int(sys.argv[sys.argv.index('--ancho') + 1]) if '--ancho' in sys.argv else ANCHO
    cal = int(sys.argv[sys.argv.index('--calidad') + 1]) if '--calidad' in sys.argv else CALIDAD

    if '--todos' in sys.argv:
        archivos = sorted(glob.glob(os.path.join(DIR, 'Banners-*.jpg')))
    else:
        archivos = [os.path.join(DIR, a) for a in sys.argv[1:] if not a.startswith('--')]
    archivos = [a for a in archivos if os.path.isfile(a)]
    if not archivos:
        print(__doc__)
        return 1

    resp = os.path.join('backups', f'banners_originales_{datetime.now():%Y%m%d_%H%M%S}')
    os.makedirs(resp, exist_ok=True)

    print(f'ancho destino {ancho}px, calidad {cal}')
    print(f'originales -> {resp}\n')
    total_antes = total_despues = 0
    for ruta in archivos:
        nombre = os.path.basename(ruta)
        antes = os.path.getsize(ruta)
        shutil.copy2(ruta, os.path.join(resp, nombre))

        im = Image.open(ruta).convert('RGB')
        w0, h0 = im.size
        if w0 > ancho:
            h = int(round(h0 * ancho / w0))
            im = im.resize((ancho, h), Image.LANCZOS)
        im.save(ruta, 'JPEG', quality=cal, optimize=True, progressive=True)

        despues = os.path.getsize(ruta)
        total_antes += antes
        total_despues += despues
        print(f'  {nombre:<18} {w0}x{h0} {antes//1024:>6} KB  ->  '
              f'{im.size[0]}x{im.size[1]} {despues//1024:>5} KB   '
              f'(-{(1 - despues / antes) * 100:.0f}%)')

    print(f'\n  TOTAL {total_antes//1024//1024} MB -> {total_despues//1024} KB '
          f'(-{(1 - total_despues / total_antes) * 100:.0f}%)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
