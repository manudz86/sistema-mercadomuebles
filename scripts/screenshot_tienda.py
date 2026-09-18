#!/usr/bin/env python3
"""Captura de pantalla de paginas de la tienda (solo lectura, no toca nada).

Uso:
    venv/bin/python3 scripts/screenshot_tienda.py <url> <salida.png> [--full] [--selector CSS]

Ejemplos:
    venv/bin/python3 scripts/screenshot_tienda.py https://www.mercadomuebles.com.ar/tienda/ /tmp/home.png
    venv/bin/python3 scripts/screenshot_tienda.py <url> /tmp/cuotas.png --selector ".precio-grande"
"""
import sys

from playwright.sync_api import sync_playwright


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        return 1
    url, salida = args[0], args[1]
    full = '--full' in args
    selector = None
    if '--selector' in args:
        selector = args[args.index('--selector') + 1]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        page.goto(url, wait_until='networkidle', timeout=45000)
        page.wait_for_timeout(1200)
        if selector:
            el = page.query_selector(selector)
            if el is None:
                print(f'No se encontro el selector {selector!r}; capturo la pagina entera')
                page.screenshot(path=salida, full_page=full)
            else:
                el.screenshot(path=salida)
        else:
            page.screenshot(path=salida, full_page=full)
        browser.close()
    print(f'OK -> {salida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
