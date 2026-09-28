#!/usr/bin/env python3
"""Renderiza /tienda/premium con el test client de Flask (proceso aparte).

No toca el servidor que esta corriendo: sirve para validar la pagina ANTES de
reiniciar. Guarda el HTML en /tmp/premium.html.

Uso:  venv/bin/python3 scripts/check_premium.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import werkzeug  # noqa: E402

# werkzeug 3.x saco __version__ y el test_client de este flask todavia lo pide
if not hasattr(werkzeug, '__version__'):
    try:
        from importlib.metadata import version as _v
        werkzeug.__version__ = _v('werkzeug')
    except Exception:
        werkzeug.__version__ = '3'

from app import app  # noqa: E402

SALIDA = '/tmp/premium.html'


def main():
    app.config['TESTING'] = True
    with app.test_client() as c:
        r = c.get('/tienda/premium')
        print(f'HTTP {r.status_code}')
        if r.status_code != 200:
            print(r.data.decode('utf-8', 'replace')[:1500])
            return 1
        html = r.data.decode('utf-8', 'replace')

    with open(SALIDA, 'w', encoding='utf-8') as fh:
        fh.write(html)

    print(f'HTML: {len(html):,} chars -> {SALIDA}\n')
    for modelo in ('Doral Pillow Top', 'Sublime Euro Pillow',
                   'Exclusive Pillow Top', 'Renovation Euro Pillow'):
        print(f'  {"OK " if modelo in html else "FALTA"}  {modelo}')

    print(f'\n  secciones     : {html.count("pr-seccion-hdr")}')
    print(f'  cards modelo  : {html.count("pr-card")-1}')  # -1 por la regla CSS
    medidas = re.findall(r'class="pr-medida" href="([^"]+)"', html)
    print(f'  medidas/links : {len(medidas)}')
    fotos = re.findall(r'<img src="([^"]+)" alt="Colch', html)
    print(f'  fotos         : {len(fotos)}')
    print(f'  link en menu  : {"SI" if "/tienda/premium" in html else "NO"}')

    print('\n  primeros links de medida:')
    for u in medidas[:4]:
        print(f'    {u}')
    if fotos:
        print('\n  primera foto:', fotos[0])
    return 0


if __name__ == '__main__':
    sys.exit(main())
