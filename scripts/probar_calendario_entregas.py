#!/usr/bin/env python3
"""Prueba /ventas/calendario-entregas con datos reales (solo lectura) en Chromium, escritorio y celular.
Verifica que cada venta abierta con promesa aparezca en su día, el filtro por método, y el panel
(dirección + productos) al tocar un envío. Guarda capturas en el directorio indicado.

Uso: venv/bin/python scripts/probar_calendario_entregas.py [dir_capturas]
"""
import os
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import app as A  # noqa: E402
import werkzeug  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3'
salida = sys.argv[1] if len(sys.argv) > 1 else None
fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    fallas += 0 if cond else 1


A.app.config['LOGIN_DISABLED'] = True          # solo en este proceso de prueba
cli = A.app.test_client()
r = cli.get('/ventas/calendario-entregas')
check(r.status_code == 200, 'responde 200')
html = r.get_data(as_text=True)
check(cli.get('/ventas/calendario-entregas?mes=2026-12').status_code == 200, 'mes siguiente responde 200')
check(cli.get('/ventas/calendario-entregas?mes=basura').status_code == 200, 'mes inválido → mes actual')

# Lo que debería verse en el mes actual (Flete Propio + Retiro, por defecto)
from datetime import datetime, timedelta  # noqa: E402
hoy = (datetime.utcnow() - timedelta(hours=3)).date()
esperadas = A.query_db("SELECT id, numero_venta, fecha_entrega_estimada f, metodo_envio, tipo_entrega FROM ventas "
                       "WHERE estado_entrega IN ('pendiente','en_proceso') AND fecha_entrega_estimada IS NOT NULL "
                       "AND (metodo_envio='Flete Propio' OR tipo_entrega='retiro') "
                       "AND YEAR(fecha_entrega_estimada)=%s AND MONTH(fecha_entrega_estimada)=%s", (hoy.year, hoy.month))

with sync_playwright() as pw:
    nav = pw.chromium.launch(args=['--no-sandbox'])
    for nombre, vp in (('escritorio', {'width': 1366, 'height': 900}), ('celular', {'width': 390, 'height': 844})):
        pag = nav.new_page(viewport=vp)
        errores = []
        pag.on('pageerror', lambda e: errores.append(str(e)))
        pag.route('http://sistema.test/**', lambda route: route.fulfill(status=200, content_type='text/html', body=html)
                  if route.request.url.rstrip('/') == 'http://sistema.test' else route.abort())
        pag.add_init_script("try{localStorage.clear()}catch(e){}")
        pag.goto('http://sistema.test/', wait_until='load')
        pag.wait_for_timeout(1500)
        propios = [e for e in errores if 'ENVIOS' in e or 'pintar' in e or 'localidad' in e or 'SyntaxError' in e]
        check(not propios, f'{nombre}: sin errores de JS {propios[:2]}')
        ok_dias = True
        for v in esperadas:
            n = pag.locator(f'.cal-dia[data-fecha="{v["f"].isoformat()}"] .chip[data-id="{v["id"]}"]').count()
            ok_dias = ok_dias and n == 1
        check(ok_dias, f'{nombre}: las {len(esperadas)} ventas Flete Propio/Retiro del mes están en su día')
        if salida:
            pag.screenshot(path=os.path.join(salida, f'calendario_{nombre}.png'), full_page=(nombre == 'celular'))
        if esperadas:
            pag.locator(f'.chip[data-id="{esperadas[0]["id"]}"]').first.click()
            pag.wait_for_timeout(600)
            txt = pag.locator('#p-cuerpo').inner_text()
            check('Dirección' in txt and 'Productos' in txt and esperadas[0]['numero_venta'] in pag.locator('#p-titulo').inner_text(),
                  f'{nombre}: panel con dirección y productos de {esperadas[0]["numero_venta"]}')
            if salida:
                pag.screenshot(path=os.path.join(salida, f'calendario_{nombre}_panel.png'))
        # Filtro: activar Flex suma chips
        antes = pag.locator('.cal-envios .chip').count()
        if pag.locator('#filtro button[data-m="Flex"]').count():
            pag.evaluate("document.querySelector('#filtro button[data-m=\"Flex\"]').click()")
            check(pag.locator('.cal-envios .chip').count() > antes, f'{nombre}: filtro Flex agrega envíos')
        pag.close()
    nav.close()

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
