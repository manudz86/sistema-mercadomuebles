#!/usr/bin/env python3
"""Prueba (sin escribir en la base ni mandar nada a GA4/Meta) la medición de compra en las páginas de éxito:
1) tienda_bp._es_prueba_interna: cupón DESCMMD* por sesión o por cupones_uso → prueba; venta normal → no.
2) pago_exito.html (MP/Payway): gtag purchase con event_callback que graba ga4_purchase_*; la marca de GA4
   no se graba antes de enviar; en prueba interna no hay gtag purchase; Meta sigue igual.
3) pago_exito_getnet.html: ahora tiene gtag purchase con items; se mide en la ventana principal (o a los
   2,5 s si el escape del iframe no ocurrió); sin GA4 si es prueba o si todavía no hay importe.

Uso: venv/bin/python scripts/probar_medicion_compra_ga4.py
"""
import os
import re
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import werkzeug  # noqa: E402
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3'
import app as A  # noqa: E402
import tienda_bp as T  # noqa: E402
from flask import render_template, session  # noqa: E402

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    if not cond:
        fallas += 1


def script_medicion(html):
    """Solo los <script> de la página (sin el base) que tienen la medición de compra."""
    return '\n'.join(s for s in re.findall(r'<script>(.*?)</script>', html, re.S)
                     if 'purchase' in s or 'Purchase' in s)


ITEMS = [{'item_id': 'CPR8020', 'item_name': "Colchón Princess 80x190 \"20cm\" l'x", 'price': 175750.0, 'quantity': 1}]

with A.app.test_request_context('/tienda/pago/exito'):
    # 1) Detección de prueba interna
    check(T._es_prueba_interna('PW-1032770455') is True, 'venta con DESCMMD90 en cupones_uso → prueba')
    check(T._es_prueba_interna('MP-187509648543') is False, 'venta real sin cupón interno → no es prueba')
    check(T._es_prueba_interna('') is False, 'sin número de venta y sin cupón → no es prueba')
    session['cupon'] = {'codigo': 'descmmd80'}
    check(T._es_prueba_interna('MP-999') is True, 'cupón DESCMMD en la sesión (minúsculas) → prueba')
    session['cupon'] = {'codigo': 'BIENVENIDA10'}
    check(T._es_prueba_interna('MP-999') is False, 'otro cupón → no es prueba')
    session.pop('cupon', None)

    base = dict(payment_id='123', carrito_count=0, ga_value=175750, ga_items=ITEMS, importe_abonado=175750,
                numero_venta='MP-123', pago_en_proceso=False)

    # 2) MP / Payway
    js = script_medicion(render_template('tienda/pago_exito.html', es_prueba=False, **base))
    check("gtag('event', 'purchase'" in js, 'MP: manda purchase a GA4')
    check("event_callback: function() { try { localStorage.setItem(kGa, '1')" in js,
          'MP: la marca de GA4 se graba en event_callback')
    check(js.count('localStorage.setItem(kGa') == 1, 'MP: la marca de GA4 no se graba en otro lado (antes de enviar)')
    check(js.index("gtag('event', 'purchase'") < js.index("var k = 'fb_purchase_'"),
          'MP: GA4 va antes y no depende de la marca de Meta')
    check("fbq('track', 'Purchase'" in js and 'dataLayer.push' in js, 'MP: Meta (fbq + dataLayer) sigue igual')
    js_p = script_medicion(render_template('tienda/pago_exito.html', es_prueba=True, **base))
    check("gtag('event', 'purchase'" not in js_p, 'MP prueba interna: NO manda purchase a GA4')
    check("fbq('track', 'Purchase'" in js_p, 'MP prueba interna: Meta sin cambios')

    # 3) GetNet
    gn = dict(payment_id='abc', numero_pedido='GN-abc', importe_abonado=175750)
    js_g = script_medicion(render_template('tienda/pago_exito_getnet.html', ga_value=175750, ga_items=ITEMS,
                                           es_prueba=False, **gn))
    html_g = render_template('tienda/pago_exito_getnet.html', ga_value=175750, ga_items=ITEMS, es_prueba=False, **gn)
    check("gtag('event', 'purchase'" in js_g, 'GetNet: ahora manda purchase a GA4')
    check('"transaction_id": "GN-abc"' in js_g or 'transaction_id: "GN-abc"' in js_g, 'GetNet: transaction_id GN-…')
    check('item_id:   "CPR8020"' in js_g and '\\"20cm\\"' in js_g, 'GetNet: items con nombre escapado (tojson)')
    check("event_callback: function() { try { localStorage.setItem(kGa, '1')" in js_g,
          'GetNet: marca de GA4 en event_callback')
    check('if (window.__getnetEscapando) { setTimeout(__medirCompraGetnet, 2500); }' in html_g
          and 'else { __medirCompraGetnet(); }' in html_g,
          'GetNet: en el iframe espera al escape; si no escapa, mide igual a los 2,5 s')
    js_gp = script_medicion(render_template('tienda/pago_exito_getnet.html', ga_value=175750, ga_items=ITEMS,
                                            es_prueba=True, **gn))
    check("gtag('event', 'purchase'" not in js_gp, 'GetNet prueba interna: NO manda purchase a GA4')
    js_g0 = script_medicion(render_template('tienda/pago_exito_getnet.html', ga_value=0, ga_items=[],
                                            es_prueba=False, **gn))
    check("gtag('event', 'purchase'" not in js_g0, 'GetNet sin importe todavía: no manda purchase con valor 0')
    check("fbq('track', 'Purchase'" in js_g and "fbq('track', 'Purchase'" in js_gp, 'GetNet: Meta sin cambios')

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
