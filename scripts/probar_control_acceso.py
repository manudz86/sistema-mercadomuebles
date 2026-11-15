#!/usr/bin/env python3
"""Prueba el control de acceso por permisos (permisos.py) con el test client de Flask.

1. Cobertura: cada ruta registrada tiene una regla (o es pública a propósito).
2. Matriz de permisos por defecto: qué puede cada rol en rutas representativas.
3. HTTP: peticiones que el control debe CORTAR antes de la vista (401/403/302) —
   nunca se manda una escritura a un rol que la tenga permitida.
4. Menú: qué ítems ve cada rol (render de base.html sin llamar a APIs externas).
5. `next` del login: no redirige a otros sitios.

No llama a ML ni escribe en la base. Uso: venv/bin/python scripts/probar_control_acceso.py
"""
import os
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
import permisos as P  # noqa: E402
from flask import render_template  # noqa: E402
from flask_login import login_user  # noqa: E402

A.app.config['TESTING'] = True
# Solo en este proceso: el usuario sale de un header (session_transaction no anda acá).
A.login_manager.request_loader(
    lambda req: A.load_user(req.headers['X-Test-User']) if req.headers.get('X-Test-User') else None)
ID = {'admin': 1, 'vendedor': 2, 'viewer': 3, 'agencia': 4}
fallas = 0


def chequear(ok, texto):
    global fallas
    fallas += not ok
    print(('OK    ' if ok else 'FALLA ') + texto)


# ── 1. Cobertura de rutas ──
print('== 1. Cobertura ==')
sin_regla = []
for r in A.app.url_map.iter_rules():
    ejemplo = r.rule.replace('<int:', '<').split('<')[0] + ('1' if '<' in r.rule else '')
    for m in r.methods - {'HEAD', 'OPTIONS'}:
        mod, _ = P.regla_de(ejemplo, m)
        if mod is None:
            sin_regla.append(f'{m} {r.rule}')
chequear(not sin_regla, f'todas las rutas tienen regla ({len(sin_regla)} sin regla: {sin_regla[:10]})')

# ── 2. Matriz por defecto ──
print('\n== 2. Matriz de permisos por defecto ==')
MATRIZ = [
    # (método, ruta, {rol: esperado})
    ('GET', '/ventas/activas', {'vendedor': True, 'viewer': True, 'agencia': False}),
    ('POST', '/ventas/activas/1/entregada', {'vendedor': True, 'viewer': False, 'agencia': False}),
    ('GET', '/ventas/editar/1', {'vendedor': True, 'viewer': False, 'agencia': False}),
    ('GET', '/nueva-venta', {'vendedor': True, 'viewer': False}),
    ('POST', '/ventas/guardar-trid', {'vendedor': True, 'viewer': False}),
    ('GET', '/stock', {'vendedor': True, 'viewer': True, 'agencia': False}),
    ('GET', '/cargar-stock', {'vendedor': True, 'viewer': False}),
    ('POST', '/transferir-stock/guardar', {'vendedor': True, 'viewer': False}),
    ('GET', '/cargar-stock-ml', {'vendedor': True, 'viewer': True}),
    ('POST', '/buscar-sku-ml', {'vendedor': True, 'viewer': True}),
    ('POST', '/cargar-stock-mla', {'vendedor': True, 'viewer': False}),
    ('POST', '/cambiar-precio-mla', {'vendedor': True, 'viewer': False, 'agencia': False}),
    ('GET', '/promociones-ml', {'vendedor': False, 'viewer': False}),
    ('GET', '/costos', {'vendedor': False, 'viewer': False, 'agencia': False}),
    ('GET', '/rentabilidad', {'vendedor': False}),
    ('GET', '/configuracion', {'vendedor': False}),
    ('GET', '/configuracion/permisos', {'vendedor': False, 'viewer': False, 'agencia': False}),
    ('GET', '/admin/logs', {'vendedor': False}),
    ('GET', '/tienda-admin/cupones', {'vendedor': False}),
    ('GET', '/tienda-admin/precios', {'vendedor': False}),
    ('GET', '/agencia', {'vendedor': True, 'viewer': True, 'agencia': True}),
    ('GET', '/', {'vendedor': True, 'viewer': True, 'agencia': False}),
    ('GET', '/estadisticas', {'vendedor': True, 'viewer': True, 'agencia': False}),
    ('GET', '/tienda/admin/atribucion', {'vendedor': False, 'agencia': False}),
    ('GET', '/zipnova', {'vendedor': True, 'viewer': True, 'agencia': False}),
    ('POST', '/viajes/guardar', {'vendedor': True, 'viewer': False}),
    ('POST', '/preguntas/1/responder', {'vendedor': True, 'viewer': False}),
    ('GET', '/intentos-pago', {'vendedor': False}),
    ('POST', '/admin/bot-precios/confirmar', {'vendedor': False, 'viewer': False, 'agencia': False}),
    ('GET', '/auditoria-ml', {'vendedor': False}),
    ('GET', '/ventas/historicas/facturar-multiple', {'vendedor': True, 'viewer': False}),
    ('POST', '/configuracion/porcentajes-ml', {'vendedor': True, 'viewer': False}),
]
for metodo, ruta, esp in MATRIZ:
    for rol, e in esp.items():
        chequear(P.ruta_permitida(rol, ruta, metodo) == e, f'{rol:<9} {metodo:4} {ruta:<40} → {e}')
    chequear(P.ruta_permitida('admin', ruta, metodo), f'admin     {metodo:4} {ruta:<40} → True')

# ── 3. HTTP: cortes antes de la vista ──
print('\n== 3. HTTP ==')
CASOS = [
    ('POST', '/admin/bot-precios/confirmar', 'anon', 401),
    ('POST', '/admin/bot-precios/confirmar', 'vendedor', 403),
    ('POST', '/admin/competencia/actualizar-precio', 'viewer', 403),
    ('POST', '/configuracion/resetear/ejecutar', 'vendedor', 403),
    ('POST', '/tienda/test-payway/pagar', 'vendedor', 403),
    ('POST', '/push/test', 'vendedor', 403),
    ('POST', '/push/subscribe', 'anon', 401),
    ('POST', '/ventas/activas/1/cancelar', 'viewer', 403),
    ('POST', '/ventas/activas/1/cancelar', 'agencia', 403),
    ('POST', '/cambiar-precio-mla', 'viewer', 403),
    ('POST', '/costos/aplicar', 'vendedor', 403),
    ('POST', '/configuracion/permisos', 'vendedor', 403),
    ('GET', '/costos', 'vendedor', 302),
    ('GET', '/ventas/activas', 'agencia', 302),
    ('GET', '/', 'agencia', 302),
    ('GET', '/ventas/activas', 'anon', 302),
    ('GET', '/admin/whatsapp/chats', 'vendedor', 302),
    ('GET', '/auditoria-ml', 'admin', 404),
    ('GET', '/debug-token-temp', 'admin', 404),
    ('GET', '/admin/logs', 'admin', 200),
    ('GET', '/configuracion/permisos', 'admin', 200),
    ('GET', '/stock', 'viewer', 200),
    ('GET', '/stock', 'vendedor', 200),
    ('POST', '/admin/competencia-scraper/upload', 'anon', 401),
    ('GET', '/push/public-key', 'anon', 200),
    ('GET', '/login', 'anon', 200),
    ('GET', '/tienda/', 'anon', 200),
]
for metodo, ruta, rol, exp in CASOS:
    c = A.app.test_client()
    h = {'X-Test-User': str(ID[rol])} if rol in ID else {}
    r = c.open(ruta, method=metodo, json={} if metodo == 'POST' else None, headers=h)
    chequear(r.status_code == exp, f'{metodo:4} {ruta:<40} {rol:<9} → {r.status_code} (esperado {exp}) {r.headers.get("Location", "")}')
c = A.app.test_client()
r = c.post('/ventas/activas/1/cancelar', data={'x': '1'}, headers={'X-Test-User': '3', 'Referer': 'http://localhost/ventas/activas'})
chequear(r.status_code == 302 and r.headers.get('Location', '').endswith('/ventas/activas'),
         f'formulario HTML de viewer → aviso y vuelve a la página ({r.status_code} {r.headers.get("Location")})')
r = c.get('/', headers={'X-Test-User': '4'})
chequear(r.headers.get('Location', '').endswith('/agencia'), f'agencia en / va a /agencia ({r.headers.get("Location")})')

# ── 4. Menú por rol ──
print('\n== 4. Menú ==')
ESPERA_MENU = {
    'admin': (['/costos"', '/configuracion/permisos"', '/admin/bot-precios"', '/ventas/activas"'], ['/auditoria-ml"']),
    'vendedor': (['/ventas/activas"', '/nueva-venta"', '/cargar-stock"', '/cargar-stock-ml"', '/zipnova"', '/estadisticas"'],
                 ['/costos"', '/configuracion"', '/admin/bot-precios"', '/configuracion/permisos"', '/promociones-ml"', '/auditoria-ml"']),
    'viewer': (['/ventas/activas"', '/stock"', '/cargar-stock-ml"'],
               ['/nueva-venta"', '/cargar-stock"', '/bajar-stock"', '/costos"', '/configuracion/permisos"']),
    'agencia': (['/agencia"'], ['/ventas/activas"', '/stock"', '/"', '/cargar-stock-ml"', '/estadisticas"']),
}
for rol, (si, no) in ESPERA_MENU.items():
    with A.app.test_request_context('/stock'):
        login_user(A.load_user(ID[rol]))
        html = render_template('sin_permisos.html')
    falta = [x for x in si if f'href="{x}' not in html]
    sobra = [x for x in no if f'href="{x}' in html]
    chequear(not falta and not sobra, f'menú {rol:<9} falta={falta} sobra={sobra}')

# ── 5. next del login ──
print('\n== 5. next ==')
for nxt, rol, esperado in [('/costos', 'vendedor', False), ('/ventas/activas', 'vendedor', True),
                           ('//evil.com', 'admin', False), ('https://evil.com', 'admin', False)]:
    ok = (nxt.startswith('/') and not nxt.startswith('//') and P.ruta_permitida(rol, nxt))
    chequear(ok == esperado, f'next={nxt:<18} {rol:<9} → {ok}')
print(f"\nCookies: SESSION_COOKIE_SECURE={A.app.config['SESSION_COOKIE_SECURE']} "
      f"REMEMBER_COOKIE_DURATION={A.app.config['REMEMBER_COOKIE_DURATION']}")
print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
