#!/usr/bin/env python3
"""Convierte un banner de diseño (PNG pesado) a JPG progresivo para la web, sin deformar.
No toca el original. Si el ancho supera --ancho, lo reduce manteniendo la proporción.

Uso: venv/bin/python scripts/generar_banner_web.py <origen.png> <destino.jpg> [--ancho 2400] [--calidad 85]
"""
import os
import sys

from PIL import Image

if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)
origen, destino = sys.argv[1], sys.argv[2]
ancho = int(sys.argv[sys.argv.index('--ancho') + 1]) if '--ancho' in sys.argv else 2400
calidad = int(sys.argv[sys.argv.index('--calidad') + 1]) if '--calidad' in sys.argv else 85
if os.path.exists(destino):
    print(f'Ya existe {destino}: no se sobrescribe')
    sys.exit(1)
im = Image.open(origen).convert('RGB')
if im.width > ancho:
    im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
im.save(destino, 'JPEG', quality=calidad, optimize=True, progressive=True)
print(f'{origen} ({os.path.getsize(origen) / 1024:.0f} KB) → {destino} {im.width}x{im.height} '
      f'({os.path.getsize(destino) / 1024:.0f} KB)')
