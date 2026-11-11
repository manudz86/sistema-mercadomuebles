#!/usr/bin/env python3
"""Prueba el purchase/refund de GA4 desde el servidor (Measurement Protocol) SIN registrar nada:
- los eventos se validan contra /debug/mp/collect de GA4 (endpoint de validación, no cuenta en la propiedad);
- no escribe en la base (log_evento se reemplaza por una función que solo anota);
- el flag ga4_mp_enabled se simula prendido en memoria.

Uso: venv/bin/python scripts/probar_ga4_measurement_protocol.py
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
import app as A  # noqa: E402,F401
import tienda_bp as T  # noqa: E402

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    if not cond:
        fallas += 1


def una(sql, args=()):
    db = T.get_db(); cur = db.cursor()
    cur.execute(sql, args)
    r = cur.fetchone()
    cur.close(); db.close()
    return r


# 1) Cookies → client_id / session_id
mid = os.getenv('GA4_MEASUREMENT_ID', '')
check(mid == 'G-L445MK2QMW' and bool(os.getenv('GA4_API_SECRET')), 'credenciales GA4 en config/.env')
sfx = '_ga_' + mid[2:]
check(T._ga4_ids_desde_cookies({'_ga': 'GA1.1.123456789.1700000000', sfx: 'GS2.1.s1747323152$o1$g1$t1747323153$j0$l0$h0'})
      == ('123456789.1700000000', '1747323152'), 'cookies formato GS2')
check(T._ga4_ids_desde_cookies({'_ga': 'GA1.2.987.1600000000', sfx: 'GS1.1.1747000000.3.1.1747000100.0.0.0'})
      == ('987.1600000000', '1747000000'), 'cookies formato GS1')
check(T._ga4_ids_desde_cookies({}) == (None, None), 'sin cookies → (None, None)')

# 2) Validación real de formato contra GA4 (debug: no registra)
v = una("SELECT numero_venta, importe_abonado FROM ventas WHERE canal='tienda_web' AND numero_venta LIKE 'PW-%%' "
        "AND importe_abonado > 0 ORDER BY id DESC LIMIT 1")
items = T._ga_items_venta(v['numero_venta'])
check(len(items) > 0, f'items de una venta real ({len(items)})')
ev = T.ga4_evento_purchase('PRUEBA-VALIDACION', float(v['importe_abonado']), items, '1747323152')
ok, det = T._ga4_post(ev, '123456789.1700000000', validar=True)
check(ok, f'GA4 valida el purchase (debug): {det}')
ok, det = T._ga4_post({'name': 'refund', 'params': {'transaction_id': 'PRUEBA-VALIDACION', 'currency': 'ARS',
                                                     'value': 1000.0, 'origen_envio': 'servidor'}},
                      T._ga4_client_id_respaldo('PRUEBA-VALIDACION'), validar=True)
check(ok, f'GA4 valida el refund (debug): {det}')

# 3) Reglas de envío (sin mandar nada: _ga4_post se reemplaza y valida contra debug)
enviados = []


def fake_post(evento, client_id, validar=False):
    enviados.append((evento, client_id))
    return T.__dict__['_ga4_post_real'](evento, client_id, validar=True)


T._ga4_post_real = T._ga4_post
T._ga4_post = fake_post
T._flag_activo = lambda clave: clave == 'ga4_mp_enabled'
logs = []
T.log_evento = lambda *a, **k: logs.append((a, k))

cli = {'_ga_cid': '123456789.1700000000', '_ga_sid': '1747323152'}
T.enviar_ga4_purchase(numero_venta=v['numero_venta'], total=float(v['importe_abonado']), cli=cli)
T.enviar_ga4_purchase(numero_venta='PW-x', total=1000, cli={'cupon': {'codigo': 'DESCMMD90'}})
T.enviar_ga4_purchase(numero_venta='VEN-1', total=1000, cli=cli)
T.enviar_ga4_purchase(numero_venta='MP-1', total=0, cli=cli)
T.enviar_ga4_purchase(numero_venta='MP-2', total=500, cli={})
time.sleep(5)
nombres = [(e['params']['transaction_id'], c) for e, c in enviados]
check((v['numero_venta'], '123456789.1700000000') in nombres, 'purchase real: sale con el client_id de la cookie')
e0 = next(e for e, c in enviados if e['params']['transaction_id'] == v['numero_venta'])
check(e0['params'].get('session_id') == '1747323152' and len(e0['params']['items']) == len(items),
      'purchase real: con session_id e items')
check(not any(t == 'PW-x' for t, _ in nombres), 'prueba interna (DESCMMD) no sale')
check(not any(t in ('VEN-1', 'MP-1') for t, _ in nombres), 'venta no-tienda o sin importe no sale')
check(any(t == 'MP-2' and c and c != '123456789.1700000000' for t, c in nombres),
      'sin cookie _ga: sale igual con client_id de respaldo')

# 4) Refund: solo canceladas de la tienda, no pruebas, una vez
enviados.clear()
canc = una("SELECT v.id, v.numero_venta FROM ventas v WHERE v.canal='tienda_web' AND v.estado_entrega='cancelada' "
           "AND v.numero_venta LIKE 'MP-%%' AND NOT EXISTS (SELECT 1 FROM cupones_uso cu JOIN cupones c ON c.id=cu.cupon_id "
           "WHERE cu.venta_numero=v.numero_venta AND c.codigo LIKE 'DESCMMD%%') ORDER BY v.id DESC LIMIT 1")
activa = una("SELECT id FROM ventas WHERE canal='tienda_web' AND estado_entrega<>'cancelada' ORDER BY id DESC LIMIT 1")
ml = una("SELECT id FROM ventas WHERE canal LIKE 'Mercado%%' AND estado_entrega='cancelada' ORDER BY id DESC LIMIT 1")
ids = [canc['id'], activa['id']] + ([ml['id']] if ml else [])
T.ga4_refund_ventas(ids)
time.sleep(4)
check([e['params']['transaction_id'] for e, _ in enviados] == [canc['numero_venta']],
      'refund: solo la cancelada de la tienda (no la activa ni la de ML)')
check(enviados and enviados[0][0]['name'] == 'refund' and enviados[0][0]['params']['value'] > 0, 'refund con importe')
check(len(logs) == 1 and logs[0][0][1:3] == ('ga4', 'refund'), 'refund: queda anotado (en la prueba, sin escribir la base)')

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
