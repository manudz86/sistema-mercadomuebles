#!/usr/bin/env python3
"""Prueba el campo Día/Mes/Año de "Fecha de nacimiento del titular" del checkout
(templates/tienda/checkout_bricks.html) en Chromium headless, con el HTML y JS reales
extraídos de la plantilla. Verifica que el hidden #pw-nacimiento (lo que se manda al
pagar) quede en AAAA-MM-DD solo si la fecha es válida, y que la plantilla parsee.

Uso: venv/bin/python scripts/probar_fecha_nacimiento_checkout.py
"""
import datetime
import os
import sys

os.chdir('/home/cannon/app')
from jinja2 import Environment, FileSystemLoader  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    fallas += 0 if cond else 1


env = Environment(loader=FileSystemLoader('templates'))
env.parse(open('templates/tienda/checkout_bricks.html', encoding='utf-8').read())
check(True, 'la plantilla checkout_bricks.html parsea (Jinja2)')

src = open('templates/tienda/checkout_bricks.html', encoding='utf-8').read()
ini = src.index('<!-- Fecha de nacimiento del titular -->')
fin = src.index('</script>', ini) + len('</script>')
bloque = src[ini:fin]
check('{{' not in bloque and '{%' not in bloque, 'el bloque del campo no depende de variables Jinja')

hoy = datetime.date.today()
anio18 = hoy.year - 18

casos = [
    # (dia, mes, anio, esperado_hidden, fragmento_error)
    ('5', '08', '1985', '1985-08-05', ''),
    ('31', '12', '1950', '1950-12-31', ''),
    ('29', '02', '2000', '2000-02-29', ''),
    ('29', '02', '2001', '', 'no existe'),
    ('31', '04', '1990', '', 'no existe'),
    ('0', '01', '1990', '', 'no existe'),
    ('10', '05', str(hoy.year - 10), '', 'mayor de 18'),
    ('10', '05', '1900', '', 'Revisá el año.'),
    ('10', '05', '85', '', '4 dígitos'),
    ('1a5', '03', '19x80', '1980-03-15', ''),  # letras se descartan
    ('15', '', '1980', '', ''),                # falta el mes: vacío, sin error
]

with sync_playwright() as pw:
    nav = pw.chromium.launch(args=['--no-sandbox'])
    pag = nav.new_page()
    pag.route('**/*', lambda r: r.abort())
    pag.set_content('<html><body>' + bloque + '<button id="otro">x</button></body></html>')
    for d, m, a, esp, frag in casos:
        pag.fill('#pw-nac-dia', '')
        pag.fill('#pw-nac-anio', '')
        pag.select_option('#pw-nac-mes', '')
        pag.type('#pw-nac-dia', d)
        if m:
            pag.select_option('#pw-nac-mes', m)
        pag.type('#pw-nac-anio', a)
        pag.click('#otro')  # blur
        val = pag.input_value('#pw-nacimiento')
        err = pag.inner_text('#pw-nac-error') if pag.is_visible('#pw-nac-error') else ''
        ok = val == esp and (frag in err if frag else err == '')
        check(ok, f'{d!r}/{m or "--"}/{a!r} → hidden={val!r} error={err!r}')
    # Límite exacto de 18 años: cumple hoy → válido; cumple mañana → no
    man = hoy + datetime.timedelta(days=1)
    for f, esp in [(hoy.replace(year=anio18), True), (man.replace(year=man.year - 18), False)]:
        pag.fill('#pw-nac-dia', str(f.day)); pag.select_option('#pw-nac-mes', f'{f.month:02d}')
        pag.fill('#pw-nac-anio', str(f.year)); pag.click('#otro')
        check(bool(pag.input_value('#pw-nacimiento')) == esp, f'límite 18 años {f} → {"válido" if esp else "rechazado"}')
    # Lo que lee el pago (misma expresión que checkout_bricks.html)
    pag.fill('#pw-nac-dia', '7'); pag.select_option('#pw-nac-mes', '11'); pag.fill('#pw-nac-anio', '1979')
    leido = pag.evaluate("(document.getElementById('pw-nacimiento') || {}).value || ''")
    check(leido == '1979-11-07', f'el pago lee birth_date={leido!r}')
    nav.close()

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
