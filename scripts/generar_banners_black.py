#!/usr/bin/env python3
"""Convierte los banners de Black Friday 2026 (PNG ~2 MB) a JPG livianos para la tienda.
No toca los originales. Uso: venv/bin/python scripts/generar_banners_black.py
"""
import os

from PIL import Image

D = '/home/cannon/app/static/img/banners/'
PIEZAS = {'25 y 27': '25-27', '26': '26', '28': '28', '29 y 30': '29-30'}

for formato in ('desktop', 'mobile'):
    for orig, dias in PIEZAS.items():
        src = f'{D}black26 {formato} {orig}.png'
        dst = f'{D}black2026_{formato}_{dias}.jpg'
        im = Image.open(src).convert('RGB')
        im.save(dst, 'JPEG', quality=84, optimize=True, progressive=True)
        print(f'{os.path.basename(dst):<32} {im.size[0]}x{im.size[1]}  '
              f'{os.path.getsize(src) // 1024:>5} KB → {os.path.getsize(dst) // 1024:>4} KB')
