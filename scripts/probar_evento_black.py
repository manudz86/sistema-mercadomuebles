#!/usr/bin/env python3
"""Prueba el Black Friday SIN escribir en la base: la configuración del evento se simula
en memoria (get_db falso solo dentro de get_hot_event) y la tienda se renderiza con el
test client. Nada de esto llama a pasarelas ni escribe.

1. Banner, textos y promos por día (24/11 al 1/12).
2. Render de la home y el carrito con el tema Black.
3. Cupón del evento rechazado con el evento apagado.
4. Vista previa: link firmado → cookie → la tienda muestra el evento solo a ese navegador.
5. Panel: validación de banners (solo casos que se rechazan, no guarda nada).
Uso: venv/bin/python scripts/probar_evento_black.py
"""
import os
import sys
from datetime import date

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

B = '/static/img/banners/black2026_'
CFG = {
    'hot_event_activo': 'auto', 'hot_event_fecha_inicio': '2026-11-25 00:00:00',
    'hot_event_fecha_fin': '2026-11-30 23:59:00', 'evento_fecha_corte': '2026-11-27 23:59:00',
    'evento_titulo': 'BLACK FRIDAY', 'evento_fechas': '25 AL 27 DE NOVIEMBRE',
    'evento_fechas_ext': 'HASTA EL 30 DE NOVIEMBRE', 'evento_descuento_max': '15',
    'evento_cupon': 'BLACK2026', 'evento_cupon_pct': '5', 'evento_tema': 'black',
    'evento_extra_catalogo': '0', 'evento_extra_oferta': '0',
    'promo_2x1_almohadas': 'auto', 'evento_envio_gratis_caba': 'auto',
    'promo_3sin_activo': 'auto', 'promo_3sin_dias': '2,4,5',
    'evento_banners': '\n'.join([
        f'2026-11-25,2026-11-27 | {B}desktop_25-27.jpg | {B}mobile_25-27.jpg',
        f'2026-11-26 | {B}desktop_26.jpg | {B}mobile_26.jpg',
        f'2026-11-28 | {B}desktop_28.jpg | {B}mobile_28.jpg',
        f'2026-11-29..2026-11-30 | {B}desktop_29-30.jpg | {B}mobile_29-30.jpg']),
}


class _Cur:
    def execute(self, *a):
        pass

    def fetchall(self):
        return [{'clave': k, 'valor': v} for k, v in CFG.items()]

    def close(self):
        pass


class _Db:
    def cursor(self):
        return _Cur()

    def close(self):
        pass


_real_get_db, _real_he = T.get_db, T.get_hot_event


def he_simulado(simular=None):
    T.get_db = lambda: _Db()
    try:
        return _real_he(simular)
    finally:
        T.get_db = _real_get_db


fallas = 0


def chequear(ok, txt):
    global fallas
    fallas += not ok
    print(('OK    ' if ok else 'FALLA ') + txt)


print('== 1. Por día ==')
ESPERA = {  # día: (sufijo banner, 3 cuotas sin interés, fechas)
    25: ('25-27', True, '25 AL 27'), 26: ('26', False, '25 AL 27'), 27: ('25-27', True, '25 AL 27'),
    28: ('28', True, 'HASTA EL 30'), 29: ('29-30', False, 'HASTA EL 30'), 30: ('29-30', False, 'HASTA EL 30'),
}
with A.app.test_request_context('/tienda/'):
    for dia, (suf, c3, fechas) in ESPERA.items():
        h = he_simulado(date(2026, 11, dia))
        ok = (h['activo'] and h['banner_desktop'] == f'{B}desktop_{suf}.jpg' and h['banner_mobile'] == f'{B}mobile_{suf}.jpg'
              and h['cuotas_3sin'] == c3 and fechas in h['fechas'] and h['tema'] == 'black'
              and 'Envío sin cargo en CABA' in h['promos'] and '2x1 en almohadas' in h['promos'])
        chequear(ok, f"{dia}/11 banner {h['banner_desktop'].rsplit('/', 1)[-1]:<28} 3 sin interés={h['cuotas_3sin']!s:<5} "
                     f"fechas='{h['fechas']}' cuenta hasta {h['fecha_fin_iso'][:16]} promos={h['promos']}")
    fin = he_simulado(date(2026, 11, 25))['fecha_fin_iso'][:16]
    chequear(fin == '2026-11-27T23:59', f'25/11: la cuenta regresiva va al corte ({fin})')
    fin = he_simulado(date(2026, 11, 29))['fecha_fin_iso'][:16]
    chequear(fin == '2026-11-30T23:59', f'29/11: la cuenta regresiva va al cierre ({fin})')
    chequear(T._banner_programado(CFG['evento_banners'], date(2026, 12, 1)) is None, '1/12 sin banner programado')
    for ruta in ('desktop_25-27', 'mobile_29-30'):
        chequear(os.path.isfile(f'/home/cannon/app{B}{ruta}.jpg'), f'existe {ruta}.jpg')

print('\n== 2. Render ==')
A.app.config['TESTING'] = True
c = A.app.test_client()
for dia, (suf, c3, _) in ((25, ESPERA[25]), (26, ESPERA[26])):
    he = he_simulado(date(2026, 11, dia))
    T.get_hot_event = lambda simular=None, _h=he: _h
    html = c.get('/tienda/').get_data(as_text=True)
    chequear(f'black2026_desktop_{suf}.jpg' in html and f'black2026_mobile_{suf}.jpg' in html, f'{dia}/11 home: banners del día')
    chequear('#e8122e' in html and 'hpb-tag' in html and '🔥' not in html.split('<!-- HEADER -->')[0][-6000:],
             f'{dia}/11 home: tema Black (sin fueguito en la barra)')
    chequear(('3 cuotas sin interés</span>' in html) == c3, f'{dia}/11 barra: "3 cuotas sin interés" = {c3}')
    chequear('BLACK2026' in html and 'Hasta 15% OFF' in html, f'{dia}/11 barra: cupón y hasta 15% OFF')
    chequear('2x1 en almohadas' in html and 'Envío sin cargo en CABA' in html, f'{dia}/11 popup: promos del día')
T.get_hot_event = _real_he

print('\n== 3. Cupón del evento con el evento apagado ==')
apagado = dict(he_simulado(date(2026, 11, 25)), activo=False, cupon='CYBERSALE')
T.get_hot_event = lambda simular=None: apagado
r = c.post('/tienda/carrito/validar-cupon', json={'codigo': 'CYBERSALE'}).get_json()
chequear(not r['ok'] and 'vale solo durante' in r['error'], f"CYBERSALE con evento apagado → {r}")
T.get_hot_event = _real_he

print('\n== 4. Vista previa ==')
with A.app.test_request_context('/'):
    tok = T.evento_preview_token('2026-11-25')
r = c.get('/tienda/evento-preview?t=' + tok)
chequear(r.status_code == 302 and 'ev_preview=' in r.headers.get('Set-Cookie', ''), 'link firmado deja la cookie')
html = c.get('/tienda/').get_data(as_text=True)
chequear('Vista previa del evento' in html and 'hot-promo-bar' in html, 'con la cookie: la tienda muestra el evento')
c2 = A.app.test_client()
html2 = c2.get('/tienda/').get_data(as_text=True)
chequear('Vista previa del evento' not in html2, 'otro navegador no ve la vista previa')
r = c2.get('/tienda/evento-preview?t=falso')
chequear('ev_preview=' not in r.headers.get('Set-Cookie', ''), 'token falso: no deja cookie')
with A.app.test_request_context('/'):
    chequear(T.get_hot_event().get('simulado') is False, 'get_hot_event real no se ve afectado')
c.get('/tienda/evento-preview?salir=1')
html = c.get('/tienda/').get_data(as_text=True)
chequear('Vista previa del evento' not in html, 'salir borra la vista previa')

print('\n== 5. Panel (solo rechazos) ==')
A.login_manager.request_loader(
    lambda req: A.load_user(req.headers['X-Test-User']) if req.headers.get('X-Test-User') else None)
base = {'modo': 'auto', 'inicio': '2026-11-25T00:00', 'fin': '2026-11-30T23:59', 'corte': '2026-11-27T23:59',
        'titulo': 'BLACK FRIDAY', 'fechas': 'x', 'desc_max': '15', 'cupon': 'BLACK2026', 'cupon_pct': '5',
        'promo_2x1': 'auto', 'envio_caba': 'auto', 'tema': 'black', 'fechas_ext': 'y'}
for banners, txt in ((f'2026-11-25 | {B}desktop_25-27.jpg', 'falta una parte'),
                     (f'2026-11-25 | {B}no_existe.jpg | {B}mobile_25-27.jpg', 'archivo inexistente'),
                     (f'2026-13-25 | {B}desktop_25-27.jpg | {B}mobile_25-27.jpg', 'fecha inválida')):
    r = c.post('/productos/evento-guardar', data=dict(base, banners=banners), headers={'X-Test-User': '1'}).get_json()
    chequear(r and not r['ok'], f'rechaza {txt}: {r and r["msg"]}')
r = c.post('/productos/evento-guardar', data=dict(base, tema='rosa'), headers={'X-Test-User': '1'}).get_json()
chequear(r and not r['ok'], f'rechaza tema inválido: {r and r["msg"]}')
r = c.get('/productos/evento-preview?fecha=2026-11-25', headers={'X-Test-User': '1'})
chequear(r.status_code == 302 and '/tienda/evento-preview?t=' in r.headers.get('Location', ''), 'admin genera el link de vista previa')
r = c.get('/productos/evento-preview?fecha=2026-11-25', headers={'X-Test-User': '2'})
chequear(r.status_code in (302, 403) and 'evento-preview?t=' not in r.headers.get('Location', ''), 'vendedor no puede generarlo')
print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
