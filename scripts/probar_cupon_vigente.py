#!/usr/bin/env python3
"""Prueba que un cupón vencido/desactivado no siga aplicándose desde la sesión ni desde un
checkout viejo. Solo lecturas en la base; no cobra ni crea pedidos.

Uso: venv/bin/python scripts/probar_cupon_vigente.py
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
from flask import session  # noqa: E402

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    if not cond:
        fallas += 1


vencido = A.query_one("SELECT codigo FROM cupones WHERE fecha_vencimiento < CURDATE() AND activo=1 ORDER BY id DESC LIMIT 1")
vigente = A.query_one("SELECT codigo, minimo_compra FROM cupones WHERE activo=1 AND (fecha_vencimiento IS NULL OR fecha_vencimiento >= CURDATE()) "
                      "AND (usos_maximos IS NULL OR usos_maximos=0 OR usos_actuales < usos_maximos) AND COALESCE(minimo_compra,0)=0 "
                      "AND tipo='pct' ORDER BY id DESC LIMIT 1")
print('cupón vencido de prueba:', vencido and vencido['codigo'], '| vigente:', vigente and vigente['codigo'])
carrito = [{'sku': 'SSUP140', 'nombre': 'x', 'precio': 1000000, 'cantidad': 1}]

with A.app.test_request_context('/tienda/carrito'):
    if vencido:
        session['cupon'] = {'id': 0, 'codigo': vencido['codigo'], 'tipo': 'pct', 'valor': 5, 'label': '-5%'}
        session['carrito'] = carrito
        check(T._cupon_sesion_vigente(carrito) is None and 'cupon' not in session,
              f"{vencido['codigo']} vencido: se quita de la sesión")
    if vigente:
        session['cupon'] = {'id': 0, 'codigo': vigente['codigo'], 'tipo': 'pct', 'valor': 5, 'label': '-5%'}
        check(T._cupon_sesion_vigente(carrito) is not None and 'cupon' in session,
              f"{vigente['codigo']} vigente: se mantiene")
    session['cupon'] = {'id': 0, 'codigo': 'NO-EXISTE-XYZ', 'tipo': 'pct', 'valor': 5, 'label': '-5%'}
    check(T._cupon_sesion_vigente(carrito) is None, 'cupón inexistente: se quita')
    session.pop('cupon', None)
    check(T._cupon_sesion_vigente(carrito) is None, 'sin cupón: nada que hacer')

if vencido:
    check(T._cupon_pendiente_vencido({'cupon': {'codigo': vencido['codigo']}}), 'checkout viejo con cupón vencido: se frena el cobro')
if vigente:
    check(not T._cupon_pendiente_vencido({'cupon': {'codigo': vigente['codigo']}}), 'checkout con cupón vigente: sigue')
check(not T._cupon_pendiente_vencido({}), 'checkout sin cupón: sigue')

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
