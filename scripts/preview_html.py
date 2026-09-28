#!/usr/bin/env python3
"""Captura un HTML local resolviendo /static/ contra el sitio en vivo.

Sirve para previsualizar una pagina renderizada con el test client ANTES de
reiniciar el servicio.

Uso:  venv/bin/python3 scripts/preview_html.py /tmp/premium.html /tmp/premium.png [ancho]
"""
import sys

from playwright.sync_api import sync_playwright

BASE_VIVO = 'https://www.mercadomuebles.com.ar'


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    origen, salida = sys.argv[1], sys.argv[2]
    ancho = int(sys.argv[3]) if len(sys.argv) > 3 else 1280

    with open(origen, encoding='utf-8') as fh:
        html = fh.read()
    # las rutas absolutas /static/... no existen en file://: apuntarlas al sitio vivo
    html = html.replace('src="/static/', f'src="{BASE_VIVO}/static/')
    html = html.replace('href="/static/', f'href="{BASE_VIVO}/static/')

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': ancho, 'height': 1000})
        pg.set_content(html, wait_until='networkidle')
        pg.wait_for_timeout(2500)
        pg.screenshot(path=salida, full_page=True)
        b.close()
    print(f'OK -> {salida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
