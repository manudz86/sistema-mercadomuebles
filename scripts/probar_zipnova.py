#!/usr/bin/env python3
"""Prueba la integración Zipnova / mensajes ML en el panel, sin escribir en la base:
- las 3 pantallas de ventas y /zipnova responden 200 (con o sin las tablas nuevas);
- con datos simulados aparecen los íconos (📍, Z, 💬 y el puntito rojo) en Activas, Proceso e Históricas;
- con las tablas creadas, la página /zipnova muestra las recolecciones.

Uso: venv/bin/python scripts/probar_zipnova.py
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
import zipnova_bp as Z  # noqa: E402
from flask import g  # noqa: E402
from flask_login import login_user  # noqa: E402

fallas = 0
A.execute_db = lambda sql, params=None: None


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    if not cond:
        fallas += 1


def vista(path, fn, simular=None):
    with A.app.test_request_context(path):
        login_user(A.load_user('1'))
        if simular:
            g.zn_mapa, g.ml_nl_mapa = simular
        rv = A.app.make_response(fn())
        return rv.status_code, rv.get_data(as_text=True)


# 1) Sin simular: responden
for path, fn in (('/ventas/activas', A.ventas_activas), ('/ventas/proceso', A.ventas_proceso),
                 ('/ventas/historicas', A.ventas_historicas), ('/zipnova', Z.zipnova_recolecciones)):
    st, html = vista(path, fn)
    check(st == 200, f'{path} responde 200')

# 2) Simulado: cada pantalla con una venta ML que se esté mostrando
q1 = A.query_one
casos = (
    ('/ventas/activas', A.ventas_activas, "estado_entrega='pendiente'"),
    ('/ventas/proceso', A.ventas_proceso, "estado_entrega='en_proceso'"),
    ('/ventas/historicas', A.ventas_historicas, "estado_entrega='entregada'"),
)
for path, fn, cond in casos:
    v = q1(f"SELECT numero_venta FROM ventas WHERE canal='Mercado Libre' AND {cond} "
           "AND numero_venta LIKE 'ML-%%' ORDER BY id DESC LIMIT 1")
    if not v:
        print('SIN DATOS', path)
        continue
    nv = v['numero_venta']
    oid = int(nv[3:])
    fake_zn = {nv: {'zipnova_id': 999001, 'numero_venta': nv, 'guia': '0999-1', 'status': 'shipped',
                    'status_name': 'Despachado', 'carrier': 'Prueba', 'tracking_url': 'https://app.zipnova.com.ar/track/XYZ',
                    'tracking_ext_url': None, 'last_status_at': None}}
    st, html = vista(path, fn, ({**fake_zn}, {oid: 3}))
    check(st == 200, f'{path} con datos simulados responde 200')
    check('https://app.zipnova.com.ar/track/XYZ' in html, f'{path}: link de seguimiento Zipnova ({nv})')
    check('shipments/999001' in html, f'{path}: botón Z al panel de Zipnova')
    check(f'/ventas/{oid}/detalle' in html, f'{path}: 💬 a la venta en ML')
    check('3 mensaje(s) nuevo(s)' in html, f'{path}: puntito rojo con 3 mensajes')

# 2b) Filtro "solo con mensajes sin leer" con los datos reales de ml_mensajes_no_leidos
try:
    import re as _re
    nl = [f"ML-{r['order_id']}" for r in A.query_db("SELECT order_id FROM ml_mensajes_no_leidos")]
    for path, fn, cond in casos:
        esperadas = q1("SELECT COUNT(*) AS c FROM ventas WHERE " + cond.replace("estado_entrega='entregada'",
                       "estado_entrega IN ('entregada','cancelada')") + Z.SQL_CON_MENSAJES)['c']
        st, html = vista(path, fn)
        hay_banner = 'mensajes del comprador sin leer' in html
        check(st == 200 and hay_banner == bool(esperadas), f'{path}: cartel de mensajes ({esperadas} ventas)')
        st, html = vista(path + '?solo_mensajes=1', fn)
        mostradas = [n for n in nl if n in html]
        check(st == 200 and 'Ver todas' in html and len(set(mostradas)) == esperadas,
              f'{path}?solo_mensajes=1 muestra solo esas ({len(set(mostradas))}/{esperadas})')
except Exception as e:
    check(False, f'filtro de mensajes: {e}')

# 3) Con tablas: la página muestra recolecciones
try:
    n = q1("SELECT COUNT(*) AS c FROM zipnova_recolecciones")['c']
    st, html = vista('/zipnova', Z.zipnova_recolecciones)
    ok = st == 200 and ('Retiro del' in html or n == 0)
    check(ok, f'/zipnova con tablas ({n} recolecciones)')
    if not ok:
        print('   status', st, '| falta migración' if 'Falta crear' in html else '')
        _, _, _, gc = Z._db()
        with A.app.test_request_context('/zipnova'):
            try:
                A.query_db("SELECT re.*, ze.zipnova_id FROM zipnova_recoleccion_envios re LEFT JOIN zipnova_envios ze "
                           "ON ze.zipnova_id = (SELECT MAX(z2.zipnova_id) FROM zipnova_envios z2 "
                           "WHERE z2.external_id = re.external_id OR z2.guia = re.guia) LIMIT 1")
                print('   consulta de envíos OK')
            except Exception as e:
                print('   consulta de envíos:', e)
except Exception as e:
    print('INFO tablas nuevas todavía no creadas:', str(e)[:80])

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
