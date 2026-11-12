#!/usr/bin/env python3
"""Prueba la atribución multi-contacto y los cambios de Meta SIN efectos externos:
- no escribe en la base (las funciones de escritura se reemplazan por capturas en memoria);
- no manda nada a Meta (http_requests.post se reemplaza);
- no levanta tareas programadas (CANNON_SIN_SCHEDULER=1).

Uso: venv/bin/python scripts/probar_atribucion.py
"""
import os
import sys
import time

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
import whatsapp_bp as W  # noqa: E402

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    if not cond:
        fallas += 1


# 1) Clasificación de canal
C = T.clasificar_canal
casos = [
    ({'utm_source': 'ig', 'utm_medium': 'paid', 'utm_campaign': '120249451187060330', 'fbclid': 'x'}, 'Meta Ads'),
    ({'utm_source': 'an', 'utm_medium': 'paid'}, 'Meta Ads'),
    ({'utm_source': 'fb', 'utm_campaign': '120249451187060330'}, 'Meta Ads'),
    ({'fbclid': 'x', 'referrer': 'https://l.instagram.com/'}, 'Meta orgánico'),
    ({'referrer': 'https://m.facebook.com/'}, 'Meta orgánico'),
    ({'gclid': 'x', 'referrer': 'https://www.google.com/'}, 'Google Ads'),
    ({'gbraid': 'x'}, 'Google Ads'),
    ({'wbraid': 'x'}, 'Google Ads'),
    ({'utm_source': 'google', 'utm_medium': 'cpc'}, 'Google Ads'),
    ({'referrer': 'https://www.google.com/'}, 'Google orgánico'),
    ({'referrer': 'https://www.google.com.ar/'}, 'Google orgánico'),
    ({'referrer': 'https://googleads.g.doubleclick.net/'}, 'Google Ads'),
    ({'referrer': 'https://www.mercadolibre.com.ar/'}, 'Otros referidos'),
    ({'utm_source': 'whatsapp', 'utm_medium': 'bot'}, 'WhatsApp'),
    ({'utm_source': 'whatsapp', 'utm_medium': 'bot', 'wa': 'abc'}, 'WhatsApp'),
    ({'utm_source': 'email', 'utm_medium': 'recupero_carrito'}, 'Email'),
    ({'utm_source': 'chatgpt.com'}, 'IA (ChatGPT, etc.)'),
    ({'referrer': 'https://www.bing.com/'}, 'Otros buscadores'),
    ({}, 'Directo'),
]
for d, esperado in casos:
    check(C(d) == esperado, f'canal {d} → {C(d)} (esperado {esperado})')
check(T.clasificar_origen_json('{"utm_source":"ig","utm_medium":"paid","utm_campaign":"1"}') == 'Meta Ads', 'origen JSON del navegador')
check(T.clasificar_origen_json('%7B%22referrer%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%7D') == 'Google orgánico', 'origen JSON url-encoded')
check(T.clasificar_origen_json(None) == 'Directo' and T.clasificar_origen_json('basura') == 'Directo', 'origen vacío/malformado')

# 2) Hash de teléfono/email y marca de WhatsApp
check(T.tel_hash('5491155230940') == T.tel_hash('11 5523-0940') and T.tel_hash('5491155230940'), 'mismo HMAC para WhatsApp y checkout')
check(len(T.wa_ref_de_tel('5491155230940')) == 16, 'marca wa de 16 hex')
check(T.email_hash('A@B.com ') == T.email_hash('a@b.com') and T.email_hash('sin-arroba') is None, 'HMAC email normalizado')
txt = 'Mirá: https://www.mercadomuebles.com.ar/tienda/producto/X?utm_source=whatsapp&utm_medium=bot y la tienda https://www.mercadomuebles.com.ar/tienda/?utm_source=whatsapp&utm_medium=bot'
m = W._marcar_links_wa(txt, '5491155230940')
ref = T.wa_ref_de_tel('5491155230940')
check(m.count('&wa=' + ref) == 2 and W._marcar_links_wa(m, '5491155230940') == m, 'links del bot marcados una sola vez')

# 3) Captura en la tienda (sin escribir en la base)
touches, idents = [], []
T._registrar_touch = lambda vid, sig, path, ua: touches.append((vid, sig, path))
T.registrar_identidad = lambda *a, **k: idents.append(a)
cli = A.app.test_client()
ua = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)'}
r = cli.get('/tienda/?utm_source=ig&utm_medium=paid&utm_campaign=120249451187060330&utm_content=999&utm_term=888&fbclid=PRUEBA',
            headers=ua)
ck = r.headers.getlist('Set-Cookie')
vid_ck = [c for c in ck if c.startswith('mm_vid=')]
check(r.status_code in (200, 301, 302) and vid_ck and 'HttpOnly' in vid_ck[0] and 'Secure' in vid_ck[0], f'cookie mm_vid creada ({r.status_code})')
check(touches and touches[-1][1].get('utm_content') == '999' and touches[-1][1].get('utm_term') == '888', 'contacto Meta con anuncio y conjunto')
n = len(touches)
cli.get('/tienda/', headers={**ua, 'Referer': 'https://www.google.com/'})
check(len(touches) == n + 1 and T.clasificar_canal(touches[-1][1]) == 'Google orgánico', 'búsqueda de Google = Google orgánico')
vid_misma = touches[-1][0] == touches[n - 1][0]
check(vid_misma, 'mismo navegador conserva el mismo vid entre visitas')
n = len(touches)
cli.get('/tienda/', headers=ua)
check(len(touches) == n, 'visita directa no registra contacto')
cli.get('/tienda/', headers={'User-Agent': 'facebookexternalhit/1.1', 'Referer': 'https://www.google.com/'})
check(len(touches) == n, 'bots ignorados')

# 4) Pixel en la página de éxito: solo con venta confirmada y no prueba
with A.app.test_request_context('/tienda/pago/exito'):
    from flask import render_template
    base = dict(payment_id='1', carrito_count=0, ga_value=1000, ga_items=[{'item_id': 'S', 'item_name': 'n', 'price': 1000, 'quantity': 1}],
                importe_abonado=1000, numero_venta='PW-1', pago_en_proceso=False)
    h1 = render_template('tienda/pago_exito.html', **base, es_prueba=False, venta_confirmada=True)
    h2 = render_template('tienda/pago_exito.html', **base, es_prueba=False, venta_confirmada=False)
    h3 = render_template('tienda/pago_exito.html', **base, es_prueba=True, venta_confirmada=True)
    check("fbq('track', 'Purchase'" in h1 and "order_id: 'PW-1'" in h1 and "eventID: 'PW-1'" in h1, 'Pixel Purchase con order_id y event_id')
    check(h1.index("fbq('track', 'Purchase'") < h1.index("localStorage.setItem(k, '1')"), 'marca local DESPUÉS de enviar')
    venta_real = A.query_one("SELECT numero_venta FROM ventas WHERE canal='tienda_web' AND email_cliente LIKE '%%@%%' "
                             "AND importe_abonado > 0 ORDER BY id DESC LIMIT 1")
    ud = T._fb_user_data(venta_real['numero_venta'])
    import re as _re
    check(ud and all(_re.fullmatch(r'[0-9a-f]{64}', str(v)) for v in ud.values()) and 'em' in ud and 'ph' in ud,
          f'coincidencia avanzada: solo hashes SHA-256 ({sorted(ud or {})})')
    h4 = render_template('tienda/pago_exito.html', **base, es_prueba=False, venta_confirmada=True, fb_user_data=ud)
    check(f"fbq('init', '5994867780529728', {{\"" in h4 and ud['em'] in h4 and '@' not in h4.split("fbq('init'")[1][:400],
          'Pixel init con datos cifrados, sin email en texto plano')
    check("fbq('init', '5994867780529728');" in h1, 'sin datos del comprador el init queda igual que antes')
    check(ud['em'] == T._capi_sha256(A.query_one("SELECT email_cliente FROM ventas WHERE numero_venta=%s",
                                                 (venta_real['numero_venta'],))['email_cliente']), 'mismo hash que la CAPI')
    check("fbq('track', 'Purchase'" not in h2, 'sin venta confirmada no hay Pixel Purchase')
    check("fbq('track', 'Purchase'" not in h3, 'prueba interna no dispara Pixel Purchase')
    g1 = render_template('tienda/pago_exito_getnet.html', payment_id='r', numero_pedido='GN-r', ga_value=500, ga_items=[], es_prueba=False, importe_abonado=500)
    g2 = render_template('tienda/pago_exito_getnet.html', payment_id='r', numero_pedido='GN-r', ga_value=0, ga_items=[], es_prueba=False, importe_abonado=0)
    check("order_id: 'GN-r'" in g1 and "fbq('track', 'Purchase'" not in g2, 'GetNet: Pixel solo con importe cobrado')

# 5) CAPI: fbc reconstruido, registro y pruebas internas (sin enviar a Meta)
enviados, logs, atribs = [], [], []


class _R:
    status_code = 200
    text = '{"events_received":1,"fbtrace_id":"TRACE"}'

    def json(self):
        return {'events_received': 1, 'fbtrace_id': 'TRACE'}


T.http_requests.post = lambda url, json=None, timeout=None: (enviados.append(json), _R())[1]
T._log_capi = lambda *a, **k: logs.append((a, k))
T._guardar_venta_atribucion = lambda *a: atribs.append(a)
T._fbc_desde_touch = lambda vid, eh, th: 'fb.1.1762000000000.FBCLIDREG' if vid == 'v1' else None
T._es_prueba_interna = lambda nv: nv == 'PW-PRUEBA'
os.environ.setdefault('CAPI', 'x')
T.enviar_capi_purchase(numero_venta='PW-A', email='a@b.com', telefono='1155230940', total=1000, items=[], vid='v1')
T.enviar_capi_purchase(numero_venta='PW-B', email='a@b.com', total=500, items=[], fbc='fb.1.1.COOKIE', vid='v1')
T.enviar_capi_purchase(numero_venta='PW-PRUEBA', email='a@b.com', total=1, items=[], vid='v2')
time.sleep(4.5)
ev = {e['data'][0]['event_id']: e['data'][0] for e in enviados}
check(set(ev) == {'PW-A', 'PW-B'}, f'se enviaron solo las ventas reales ({sorted(ev)})')
check(ev.get('PW-A', {}).get('user_data', {}).get('fbc') == 'fb.1.1762000000000.FBCLIDREG', 'fbc armado con el fbclid registrado')
check(ev.get('PW-B', {}).get('user_data', {}).get('fbc') == 'fb.1.1.COOKIE', 'fbc de la cookie tiene prioridad')
check(ev.get('PW-A', {}).get('custom_data', {}).get('order_id') == 'PW-A', 'CAPI con order_id = event_id')
check(any(a[0][0] == 'PW-A' and a[0][2] == 200 and a[0][3] == 1 and a[0][4] == 'TRACE' for a in logs), 'respuesta de Meta registrada')
check(any(a[0][0] == 'PW-PRUEBA' and a[1].get('es_prueba') == 1 for a in logs), 'prueba interna registrada y no enviada')
check({a[0] for a in atribs} == {'PW-A', 'PW-B', 'PW-PRUEBA'} and any(a[0] == 'PW-A' and a[5] == 'fbclid_registrado' for a in atribs),
      'venta_atribucion para cada venta')

# 6) Página de atribución sin tablas (debe degradar, no romper) — solo lecturas
filas, por_ad, ok = T._atribucion_datos(__import__('datetime').date(2026, 11, 2), __import__('datetime').date(2026, 11, 8))
check(len(filas) == 55, f'reporte 02–08/11: {len(filas)} ventas')
check(sum(f['importe'] for f in filas) == 33274970, 'total del reporte = 33.274.970')
dist = {}
for f in filas:
    dist[f['canal_ultimo']] = dist.get(f['canal_ultimo'], 0) + 1
print('     último contacto 02–08/11:', dist, '| tablas:', ok)

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
