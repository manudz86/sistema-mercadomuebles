#!/usr/bin/env python3
"""Prueba la página Configuraciones, la promo de 3 cuotas sin interés configurable y el banner nuevo.
No escribe en la base (execute_db se reemplaza) ni levanta tareas programadas.

Uso: venv/bin/python scripts/probar_configuracion.py
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
import tienda_bp as T  # noqa: E402
import whatsapp_bp as W  # noqa: E402

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    if not cond:
        fallas += 1


check(T.promo_3sin_dias_texto([2, 4, 5]) == 'Miércoles, viernes y sábados', 'texto mié/vie/sáb')
check(T.promo_3sin_dias_texto([2, 5]) == 'Miércoles y sábados', 'texto mié/sáb')
check(T.promo_3sin_dias_texto([]) == '', 'sin días: vacío')

escrituras = []
A.execute_db = lambda sql, params=None: escrituras.append((sql, params))
A.log_evento = lambda *a, **k: None
from flask_login import login_user  # noqa: E402


def vista(path, fn, method='GET', data=None):
    """Ejecuta una vista del panel con el usuario admin logueado (sin pasar por el login)."""
    with A.app.test_request_context(path, method=method, data=data):
        login_user(A.load_user('1'))
        rv = A.app.make_response(fn())
        return rv


r = vista('/configuracion', A.configuracion_tienda)
h = r.get_data(as_text=True)
check(r.status_code == 200, f'/configuracion responde ({r.status_code})')
for txt in ('3 cuotas sin interés (Payway)', 'Demora sin stock', 'Cupón Newsletter', 'Evento promocional',
            'Recargo por cuotas', 'Flete de almohadas', 'Medios de pago en cuotas', 'btn-nl-guardar', 'toggle-payway'):
    check(txt in h, f'Configuraciones contiene "{txt}"')
r = vista('/productos', A.productos_lista)
h2 = r.get_data(as_text=True)
check(r.status_code == 200 and 'tbody-productos' in h2 and 'Demora sin stock' not in h2 and '/configuracion' in h2,
      'Catálogo sin las secciones de configuración y con link')
check(vista('/productos?json=1', A.productos_lista).status_code == 200, 'búsqueda del catálogo (json) sigue andando')

j = vista('/configuracion/promo-3sin', A.configuracion_promo_3sin, 'POST', {'modo': 'auto', 'dias': ['2', '4', '5']}).get_json()
check(j and j['ok'] and any(p == ('2,4,5', '2,4,5') for _, p in escrituras), f'guardar días mié/vie/sáb ({j and j["msg"]})')
j = vista('/configuracion/promo-3sin', A.configuracion_promo_3sin, 'POST', {'modo': 'auto'}).get_json()
check(not j['ok'], 'automático sin días: rechazado')
j = vista('/configuracion/promo-3sin', A.configuracion_promo_3sin, 'POST', {'modo': 'x', 'dias': ['2']}).get_json()
check(not j['ok'], 'modo inválido: rechazado')

c = A.app.test_client()
home = c.get('/tienda/').get_data(as_text=True)
check('Banners-05' in home and 'Banners-03' not in home, 'home usa el banner nuevo (Banners-05)')
print('     días hoy:', T.promo_3sin_dias(), '| texto:', T.promo_3sin_dias_texto(), '| corre hoy:', T.promo_3sin_activa())
ctx = W.get_promos_context()
check(T.promo_3sin_dias_texto().lower() in ctx, 'el bot de WhatsApp usa los días configurados')

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
