#!/usr/bin/env python3
"""Prueba en navegador (Chromium, pantalla de celular) el cartel de 'Entregada' con fecha
en las páginas reales de Proceso de Envío y Ventas Activas. Solo lectura:
renderiza con el test client de Flask (datos reales) y NO envía ningún formulario
(se intercepta form.submit). Sin CDN: se simula bootstrap.Modal.

Uso: venv/bin/python scripts/probar_entregada_fecha_paginas.py
"""
import os
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import app as A  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    fallas += 0 if cond else 1


import werkzeug  # noqa: E402
if not hasattr(werkzeug, '__version__'):   # Flask viejo + Werkzeug 3: el test client lo pide
    werkzeug.__version__ = '3'
A.app.config['LOGIN_DISABLED'] = True      # solo en esta prueba (proceso aparte, no toca el servicio)
cli = A.app.test_client()

STUB = ('<script>window.bootstrap={Modal:function(){return {show(){document.getElementById("modalConfirmacion")'
        '.dataset.abierto="1"},hide(){}}}};window.bootstrap.Modal.getOrCreateInstance=function(){return new window.bootstrap.Modal()};'
        'window.bootstrap.Tooltip=function(){};window.bootstrap.Offcanvas=function(){return {show(){},hide(){}}};'
        'window._enviado=null;HTMLFormElement.prototype.submit=function(){window._enviado={action:this.getAttribute("action"),'
        'campos:[...new FormData(this).entries()]}};</script>')

paginas = [('/ventas/proceso', '/ventas/proceso/marcar-entregadas-multiple', '/ventas/proceso/'),
           ('/ventas/activas', '/ventas/activas/marcar-entregadas-multiple', '/ventas/activas/')]
with sync_playwright() as pw:
    nav = pw.chromium.launch(args=['--no-sandbox'])
    for url, url_lote, pref in paginas:
        r = cli.get(url)
        check(r.status_code == 200, f'{url} responde 200')
        html = r.get_data(as_text=True).replace('<head>', '<head>' + STUB, 1)
        pag = nav.new_page(viewport={'width': 390, 'height': 844})
        errores = []
        pag.on('pageerror', lambda e: errores.append(str(e)))
        pag.route('**/*', lambda route: route.abort() if not route.request.url.startswith('http://sistema.test') else route.continue_())
        pag.route('http://sistema.test/', lambda route: route.fulfill(status=200, content_type='text/html', body=html))
        pag.goto('http://sistema.test/')
        pag.wait_for_timeout(300)
        errores_propios = [e for e in errores if 'htmlFechaEntrega' in e or 'abrirEntregaMultiple' in e
                           or 'agregarFechaEntregaAlForm' in e or 'SyntaxError' in e]
        check(not errores_propios, f'{url}: sin errores de JS propios {errores_propios[:2]}')
        check(pag.evaluate('typeof htmlFechaEntrega === "function" && typeof abrirEntregaMultiple === "function"'),
              f'{url}: selector de fecha cargado')
        # Individual: tocar 'Entregada' de la primera venta visible
        ids = pag.evaluate("[...document.querySelectorAll('[onclick*=\"entregada\"]')].map(b => b.getAttribute('onclick'))")
        if not ids:
            print(f'      ({url}: sin ventas para probar el botón)')
            pag.close()
            continue
        pag.evaluate(f"(function(){{ {ids[0]} }})()")
        check('¿Cuándo se entregó?' in pag.locator('#modalMensaje').inner_text(), f'{url}: el cartel pregunta la fecha')
        pag.evaluate("document.querySelector('#fe-bloque [data-fecha]:nth-child(2)').click()")   # Ayer
        ayer = pag.eval_on_selector('#fe-fecha', 'e => e.value')
        pag.evaluate("document.getElementById('btnConfirmar').click()")
        env = pag.evaluate('window._enviado')
        check(env and env['action'].startswith(pref) and env['action'].endswith('/entregada')
              and ['fecha_entrega', ayer] in env['campos'], f'{url}: individual con Ayer → {env}')
        # Lote: seleccionar las dos primeras y 'Marcar entregadas'
        pag.evaluate('window._enviado=null')
        sel = pag.evaluate("(function(){const c=[...document.querySelectorAll('.venta-checkbox, .venta-checkbox-desktop')].slice(0,2);"
                           "c.forEach(x=>x.checked=true); return c.map(x=>x.value)})()")
        pag.evaluate('marcarEntregadasMultiple()')
        check('¿Cuándo se entregó?' in pag.locator('#modalMensaje').inner_text(), f'{url}: lote pregunta la fecha')
        pag.evaluate("document.getElementById('btnConfirmar').click()")
        env = pag.evaluate('window._enviado')
        hoy = pag.evaluate("(()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')})()")
        check(env and env['action'] == url_lote and ['fecha_entrega', hoy] in env['campos']
              and sum(1 for k, _ in env['campos'] if k == 'venta_ids') >= 1,
              f'{url}: lote con Hoy → {len([1 for k, _ in (env or {}).get("campos", []) if k == "venta_ids"])} ventas, {sel}')
        pag.close()
    nav.close()

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
