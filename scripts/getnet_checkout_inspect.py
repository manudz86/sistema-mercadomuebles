#!/usr/bin/env python3
"""Abre el checkout hosteado de GetNet (sandbox) y reporta si deja elegir cuotas.

Espera a que cargue, completa la tarjeta de prueba si hace falta y busca
selectores/textos de cuotas. Saca capturas en cada paso.

Uso:  venv/bin/python3 scripts/getnet_checkout_inspect.py <url_checkout> [prefijo_salida]
"""
import sys
import re

from playwright.sync_api import sync_playwright

TARJETA_TEST = '5555666677778884'   # Master de prueba GetNet UAT
VENC = '12/30'
CVV = '123'
TITULAR = 'ADMIN TEST'
DNI = '00000000'


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    url = sys.argv[1]
    pref = sys.argv[2] if len(sys.argv) > 2 else '/tmp/gn'

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1280, 'height': 1000})
        pg.goto(url, wait_until='networkidle', timeout=60000)
        # el checkout muestra "Processing" unos segundos antes del formulario
        for _ in range(12):
            pg.wait_for_timeout(2500)
            txt = pg.inner_text('body')
            if 'Processing' not in txt and len(txt.strip()) > 40:
                break
        pg.screenshot(path=f'{pref}_1_inicio.png', full_page=True)
        # el checkout de GetNet renderiza dentro de un iframe: buscar en TODOS
        # los frames y quedarse con el que tenga contenido real
        txt = pg.inner_text('body')
        ctx = pg
        print(f'=== frames: {len(pg.frames)} ===')
        for fr in pg.frames:
            try:
                t = fr.inner_text('body')
            except Exception:
                continue
            print(f'  frame {fr.url[:70]!r} -> {len(t.strip())} chars')
            if len(t.strip()) > len(txt.strip()):
                txt, ctx = t, fr
        print('\n=== TEXTO DE LA PAGINA (inicio) ===')
        print(txt[:1500])

        pistas = re.findall(r'(?i)(cuota\w*|installment\w*|pagos?\s+en|interes\w*)', txt)
        print(f'\n=== pistas de cuotas en el paso 1: {sorted(set(p.lower() for p in pistas))}')

        # inputs y selects presentes
        print('\n=== campos del formulario ===')
        for sel in ctx.query_selector_all("select"):
            nom = sel.get_attribute('name') or sel.get_attribute('id') or '?'
            ops = [o.inner_text().strip() for o in sel.query_selector_all('option')]
            print(f'  SELECT {nom}: {ops[:15]}')
        for inp in ctx.query_selector_all("input"):
            nom = (inp.get_attribute('name') or inp.get_attribute('id')
                   or inp.get_attribute('placeholder') or '?')
            print(f'  INPUT  {nom}')

        # intentar completar la tarjeta para llegar al paso de cuotas
        try:
            print('\n=== completando tarjeta de prueba ===')
            # los inputs no tienen name/id utiles (:r3:, :r4:...): van por posicion
            campos = ctx.query_selector_all('input')
            valores = [TARJETA_TEST, TITULAR, VENC, CVV]
            for el, val in zip(campos, valores):
                try:
                    el.click()
                    el.type(val, delay=60)
                except Exception:
                    pass
            print(f'  completados {min(len(campos), len(valores))} campos')
            pg.wait_for_timeout(5000)
            pg.screenshot(path=f'{pref}_2_tarjeta.png', full_page=True)
            txt2 = ctx.inner_text("body")
            pistas2 = re.findall(r'(?i)(cuota\w*|installment\w*|sin\s+inter\w*)', txt2)
            print(f'  pistas tras cargar tarjeta: {sorted(set(x.lower() for x in pistas2))}')
            for sel in ctx.query_selector_all("select"):
                nom = sel.get_attribute('name') or sel.get_attribute('id') or '?'
                ops = [o.inner_text().strip() for o in sel.query_selector_all('option')]
                print(f'  SELECT {nom}: {ops[:15]}')
        except Exception as e:
            print(f'  no se pudo completar: {type(e).__name__}: {e}')

        b.close()
    print(f'\ncapturas: {pref}_1_inicio.png / {pref}_2_tarjeta.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
