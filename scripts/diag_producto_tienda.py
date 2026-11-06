#!/usr/bin/env python3
"""Lee páginas públicas de producto de la tienda y muestra título, precio, imagen
y si sale con stock / demora / sin stock. Solo GET a la tienda propia.

Uso: venv/bin/python scripts/diag_producto_tienda.py <slug> [<slug> ...]
"""
import re
import sys

import requests

BASE = 'https://www.mercadomuebles.com.ar/tienda/producto/'
for slug in sys.argv[1:]:
    r = requests.get(BASE + slug, timeout=30)
    h = r.text
    t = re.search(r'<title>([^<]+)', h)
    og = re.search(r'og:image" content="([^"]+)', h)
    img = og.group(1) if og else (re.search(r'src="(/static/img/productos/[^"]+)"', h) or [None, None])[1]
    precios = re.findall(r'\$\s?[\d\.]{6,}', h)[:4]
    estado = sorted(set(m.lower() for m in re.findall(
        r'(sin stock|en stock|disponible desde[^<]{0,30}|demora[^<]{0,40}|entrega inmediata|últimas \d+ unidades)', h, re.I)))
    print(f'{slug} [{r.status_code}]\n  {t.group(1).strip() if t else ""}\n  img={img}\n  precios={precios}\n  estado={estado}')
