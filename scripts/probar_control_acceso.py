#!/usr/bin/env python3
"""Prueba el control de acceso central (_control_acceso_rutas) con el test client de Flask,
simulando cada rol. Solo hace peticiones que el control debe CORTAR antes de la vista,
más algunos GET inocuos para admin. No llama a ML ni escribe en la base.

Uso: venv/bin/python scripts/probar_control_acceso.py
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

A.app.config['TESTING'] = True
# Solo en este proceso de prueba: el usuario sale de un header (session_transaction
# no anda con esta combinación de Flask/werkzeug).
A.login_manager.request_loader(
    lambda req: A.load_user(req.headers['X-Test-User']) if req.headers.get('X-Test-User') else None)
ROLES = {'anon': None, 'admin': 1, 'vendedor': 2, 'viewer': 3, 'agencia': 4}

# (método, ruta, roles a probar, código esperado por rol)
CASOS = [
    # Escrituras peligrosas: todos menos admin deben ser rechazados (admin no se prueba)
    ('POST', '/admin/bot-precios/confirmar', ['anon', 'vendedor', 'viewer', 'agencia'], {'anon': 401, '*': 403}),
    ('POST', '/admin/bot-precios/chat', ['anon', 'vendedor'], {'anon': 401, '*': 403}),
    ('POST', '/admin/competencia/actualizar-precio', ['anon', 'vendedor', 'viewer'], {'anon': 401, '*': 403}),
    ('POST', '/admin/competencia/correr', ['anon', 'agencia'], {'anon': 401, '*': 403}),
    ('POST', '/admin/competencia-v2/upload', ['anon', 'vendedor'], {'anon': 401, '*': 403}),
    ('POST', '/admin/whatsapp/limpiar', ['anon', 'viewer'], {'anon': 401, '*': 403}),
    ('POST', '/configuracion/resetear/ejecutar', ['anon', 'vendedor', 'viewer', 'agencia'], {'anon': 401, '*': 403}),
    ('POST', '/tienda/test-payway/pagar', ['anon', 'vendedor'], {'anon': 401, '*': 403}),
    ('POST', '/test/manufacturing-time/poner', ['anon', 'vendedor'], {'anon': 401, '*': 403}),
    ('POST', '/push/test', ['anon', 'vendedor'], {'anon': 401, '*': 403}),
    ('POST', '/push/subscribe', ['anon'], {'anon': 401}),
    # Lecturas con datos sensibles
    ('GET', '/admin/whatsapp/chats', ['anon', 'vendedor', 'viewer', 'agencia'], {'anon': 302, '*': 302}),
    ('GET', '/admin/whatsapp/conversaciones', ['anon'], {'anon': 302}),
    ('GET', '/push/stats', ['anon', 'viewer'], {'anon': 302, '*': 302}),
    ('GET', '/debug/ml/123', ['anon', 'vendedor'], {'anon': 302, '*': 302}),
    ('GET', '/debug-mla', ['viewer'], {'*': 302}),
    ('GET', '/admin/competencia/datos', ['anon', 'agencia'], {'anon': 302, '*': 302}),
    ('GET', '/admin/bot-precios', ['vendedor'], {'*': 302}),
    # Ruta borrada
    ('GET', '/debug-token-temp', ['admin'], {'*': 404}),
    # Admin entra a páginas inocuas
    ('GET', '/admin/whatsapp', ['admin'], {'*': 200}),
    ('GET', '/admin/logs', ['admin'], {'*': 200}),
    # Exentos: el scraper sigue usando su token (sin token → 401 de su propia validación)
    ('POST', '/admin/competencia-scraper/upload', ['anon'], {'anon': 401}),
    # Fuera del control: no cambia nada
    ('GET', '/push/public-key', ['anon'], {'anon': 200}),
    ('GET', '/login', ['anon'], {'anon': 200}),
]

fallas = 0
for metodo, ruta, roles, esperado in CASOS:
    for rol in roles:
        c = A.app.test_client()
        h = {'X-Test-User': str(ROLES[rol])} if ROLES[rol] else {}
        r = c.open(ruta, method=metodo, json={} if metodo == 'POST' else None, headers=h)
        exp = esperado.get(rol, esperado.get('*'))
        ok = r.status_code == exp
        destino = r.headers.get('Location', '')
        fallas += not ok
        print(f"{'OK ' if ok else 'FALLA'} {metodo:4} {ruta:<42} {rol:<9} → {r.status_code} (esperado {exp}) {destino}")
print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
