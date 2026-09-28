#!/usr/bin/env python3
"""Mide como queda recortada cada foto de /tienda/premium.

Compara el alto/ancho del contenedor contra el tamano natural de la imagen y
calcula que porcentaje de la foto original queda visible con object-fit:cover.

Uso:  venv/bin/python3 scripts/medir_fotos_premium.py [url]
"""
import sys

from playwright.sync_api import sync_playwright

URL = 'https://www.mercadomuebles.com.ar/tienda/premium'


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else URL
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1440, 'height': 1000})
        pg.goto(url, wait_until='networkidle', timeout=60000)
        # las fotos son loading="lazy": hay que recorrer la pagina para que carguen
        for y in range(0, 12000, 700):
            pg.evaluate(f'window.scrollTo(0, {y})')
            pg.wait_for_timeout(180)
        pg.evaluate('window.scrollTo(0, 0)')
        pg.wait_for_timeout(2500)
        datos = pg.evaluate("""() => {
            return Array.from(document.querySelectorAll('.pr-fila')).map(f => {
                const img = f.querySelector('.pr-foto img');
                const box = f.querySelector('.pr-foto').getBoundingClientRect();
                const t   = f.querySelector('h3');
                return {
                    modelo: t ? t.textContent.trim() : '?',
                    cw: Math.round(box.width), ch: Math.round(box.height),
                    nw: img ? img.naturalWidth : 0, nh: img ? img.naturalHeight : 0,
                    src: img ? img.getAttribute('src') : '',
                };
            });
        }""")
        b.close()

    print(f'{"modelo":<24} {"contenedor":<13} {"imagen":<12} {"ratio c/i":<10} visible')
    print('-' * 78)
    for d in datos:
        if not d['nw']:
            print(f"{d['modelo']:<24} (sin imagen)")
            continue
        ar_c = d['cw'] / d['ch']
        ar_i = d['nw'] / d['nh']
        if ar_c > ar_i:
            # el contenedor es mas ancho: la imagen se recorta ARRIBA y ABAJO
            visible = ar_i / ar_c * 100
            corte = f'recorta alto: queda {visible:.0f}% del alto'
        else:
            visible = ar_c / ar_i * 100
            corte = f'recorta ancho: queda {visible:.0f}% del ancho'
        print(f"{d['modelo']:<24} {d['cw']}x{d['ch']:<8} {d['nw']}x{d['nh']:<6} "
              f"{ar_c:.2f}/{ar_i:.2f}   {corte}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
