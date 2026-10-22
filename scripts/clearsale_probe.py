#!/usr/bin/env python3
"""Sonda contra el SANDBOX de ClearSale. Sirve para contestar empiricamente las
dudas del manual (que tiene contradicciones entre tablas y ejemplos) sin
esperar a que las conteste el equipo de integraciones.

Uso:
    venv/bin/python3 scripts/clearsale_probe.py login
    venv/bin/python3 scripts/clearsale_probe.py location        # prueba ARG / USA / BRA
    venv/bin/python3 scripts/clearsale_probe.py items           # tabla vs ejemplo
    venv/bin/python3 scripts/clearsale_probe.py state           # provincia larga vs 2 letras
    venv/bin/python3 scripts/clearsale_probe.py get <ORDER_ID> [...]
    venv/bin/python3 scripts/clearsale_probe.py todo            # login + las tres pruebas

SOLO toca el sandbox (CLEARSALE_SANDBOX_URL). Nunca imprime el ClientSecret ni
el token completo. Las ordenes que crea son de prueba y quedan en el panel de
sandbox, que es exactamente lo que el proceso de integracion pide.
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests as req_lib  # noqa: E402
from _common import cargar_env  # noqa: E402

ENV = cargar_env()
BASE = (ENV.get('CLEARSALE_SANDBOX_URL') or 'https://sandbox.clear.sale').rstrip('/')
API_KEY = ENV.get('CLEARSALE_API_KEY', '')
CLIENT_ID = ENV.get('CLEARSALE_CLIENT_ID', '')
CLIENT_SECRET = ENV.get('CLEARSALE_CLIENT_SECRET', '')

# El sandbox decide por monto: <=50 aprueba, 50-100 reprueba, >100 analisis manual.
MONTO_APRUEBA = 30.0


def _print_resp(etiqueta, r):
    print(f'  {etiqueta:<34} HTTP {r.status_code}')
    cuerpo = (r.text or '').strip()
    if cuerpo:
        try:
            print('      ' + json.dumps(r.json(), ensure_ascii=False)[:1400])
        except Exception:
            print('      ' + cuerpo[:800])
    else:
        print('      (cuerpo vacio)')


def login():
    """Devuelve el token o None. Imprime el diagnostico."""
    url = f'{BASE}/api/auth/login'
    body = {'Login': {'ApiKey': API_KEY, 'ClientId': CLIENT_ID, 'ClientSecret': CLIENT_SECRET}}
    print(f'LOGIN  {url}')
    try:
        r = req_lib.post(url, json=body, headers={'Content-Type': 'application/json'}, timeout=25)
    except Exception as e:
        print(f'  EXC {type(e).__name__}: {e}')
        return None
    print(f'  HTTP {r.status_code}')
    if r.status_code != 200:
        print('      ' + (r.text or '')[:800])
        return None
    try:
        tok = (r.json().get('Token') or {})
    except Exception:
        print('      respuesta no JSON: ' + (r.text or '')[:400])
        return None
    val = tok.get('Value') or ''
    print(f'  token OK ({len(val)} chars, no se muestra) · vence {tok.get("ExpirationDate")}')
    return val or None


def _persona(state):
    return {
        'ID': 'CLI-41540186',
        'Type': 1,                       # 1 = Persona fisica
        'Name': 'Juan Perez',
        'Email': 'prueba@mercadomuebles.com.ar',
        'LegalDocument': '20123456',     # DNI
        'Address': {
            'AddressLine1': 'Avenida Rivadavia',
            'AddressLine2': '1229',
            'City': 'Lomas de Zamora',
            'State': state,
            'ZipCode': '1832',
            'Country': 'Argentina',
        },
        'Phones': [{'Type': 6, 'AreaCode': '11', 'Number': '30242091'}],
    }


def _orden(order_id, items, state='Buenos Aires', total=MONTO_APRUEBA):
    ahora = datetime.now(timezone(timedelta(hours=-3))).strftime('%Y-%m-%dT%H:%M:%S%z')
    ahora = ahora[:-2] + ':' + ahora[-2:]          # +0000 -> +00:00
    return {
        'ID': order_id,
        'Date': ahora,
        'Email': 'prueba@mercadomuebles.com.ar',
        'TotalItems': total,
        'TotalOrder': total,
        'TotalShipping': 0.0,
        'Currency': 'ARS',
        'IP': '181.47.1.1',
        'Origin': 'Web',
        'Payments': [{
            'Date': ahora[:10],
            'Type': 1,                   # CREDIT CARD
            'Amount': total,
            'CardType': 2,               # MasterCard
            'CardBin': '516585',
            'CardEndNumber': '7711',
            'CardHolderName': 'JUAN PEREZ',
            'CardExpirationDate': '12/2030',
            'QtyInstallments': 3,
        }],
        'BillingData': _persona(state),
        'ShippingData': _persona(state),
        'Items': items,
        'SessionID': 'probe-' + uuid.uuid4().hex,
        'Reanalysis': False,
    }


def enviar(token, orden, location='ARG', etiqueta=''):
    url = f'{BASE}/api/order/send'
    body = {
        'ApiKey': API_KEY,
        'LoginToken': token,
        'AnalysisLocation': location,
        'Orders': [orden],
    }
    try:
        r = req_lib.post(url, json=body,
                         headers={'Content-Type': 'application/json',
                                  'analysisLocation': location},
                         timeout=30)
    except Exception as e:
        print(f'  {etiqueta:<34} EXC {type(e).__name__}: {e}')
        return None
    _print_resp(etiqueta, r)
    return r


# ── pruebas ─────────────────────────────────────────────────────────────────
ITEMS_TABLA   = [{'ID': 'SEX200', 'Name': 'Sommier Exclusive', 'ItemValue': MONTO_APRUEBA,
                  'Qty': 1, 'CategoryName': 'Sommiers'}]
ITEMS_EJEMPLO = [{'ProductId': 'SEX200', 'ProductTitle': 'Sommier Exclusive',
                  'Price': str(MONTO_APRUEBA), 'Quantity': 1, 'Category': 'Sommiers'}]


def probar_location(token):
    print('\n=== AnalysisLocation: que acepta para Argentina? ===')
    for loc in ('ARG', 'USA', 'BRA', 'AR'):
        enviar(token, _orden('PROBE-LOC-' + loc + '-' + uuid.uuid4().hex[:6], ITEMS_EJEMPLO),
               location=loc, etiqueta=f'AnalysisLocation={loc}')


def probar_items(token, location='ARG'):
    print('\n=== Items: nombres de la tabla vs nombres del ejemplo ===')
    enviar(token, _orden('PROBE-ITEM-EJ-' + uuid.uuid4().hex[:6], ITEMS_EJEMPLO),
           location=location, etiqueta='Items estilo EJEMPLO')
    enviar(token, _orden('PROBE-ITEM-TB-' + uuid.uuid4().hex[:6], ITEMS_TABLA),
           location=location, etiqueta='Items estilo TABLA')


def probar_state(token, location='ARG'):
    print('\n=== Address.State: provincia larga vs codigo de 2 letras ===')
    enviar(token, _orden('PROBE-ST-LARGO-' + uuid.uuid4().hex[:6], ITEMS_EJEMPLO,
                         state='Buenos Aires'),
           location=location, etiqueta='State="Buenos Aires"')
    enviar(token, _orden('PROBE-ST-CORTO-' + uuid.uuid4().hex[:6], ITEMS_EJEMPLO,
                         state='BA'),
           location=location, etiqueta='State="BA"')


def probar_montos(token, location='ARG'):
    """El sandbox decide por monto. Creamos una de cada tipo; la de AMA es la
    que despues sirve para probar el webhook con 'Change Order Status'."""
    print('\n=== Umbrales por monto: APA / RPA / AMA ===')
    casos = [
        (30.0,  'APA esperado  (<= 50)'),
        (75.0,  'RPA esperado  (50 < x <= 100)'),
        (150.0, 'AMA esperado  (> 100)'),
    ]
    creadas = []
    for monto, etiqueta in casos:
        oid = f'PROBE-MONTO-{int(monto)}-{uuid.uuid4().hex[:6]}'
        orden = _orden(oid, ITEMS_EJEMPLO, total=monto)
        if enviar(token, orden, location=location, etiqueta=etiqueta):
            creadas.append(oid)
    if creadas:
        print('\n  IDs creados: ' + '  '.join(creadas))
    return creadas


def probar_variantes(token, location='ARG'):
    """Parte del payload que SI funciona y cambia una sola cosa por vez, para
    encontrar por que una orden armada desde una venta real se acepta con 200
    pero despues no existe."""
    print('\n=== Variantes sobre el payload conocido-bueno ===')
    suf = uuid.uuid4().hex[:6]
    casos = []

    # A: control puro — identico a lo que ya sabemos que anda
    casos.append(('PROBE-CTRL-' + suf, _orden('PROBE-CTRL-' + suf, ITEMS_EJEMPLO),
                  'control (deberia existir)'))

    # B: mismo payload pero con el prefijo TEST- en el ID
    casos.append(('TEST-CTRL-' + suf, _orden('TEST-CTRL-' + suf, ITEMS_EJEMPLO),
                  'solo cambia el prefijo del ID'))

    # C: mismo payload con un monto grande, como una venta real
    o_big = _orden('PROBE-BIG-' + suf, ITEMS_EJEMPLO, total=683319.0)
    casos.append(('PROBE-BIG-' + suf, o_big, 'monto grande (683319)'))

    # D: sin CardHolderName ni CardExpirationDate (lo que falta en las ventas reales)
    o_nc = _orden('PROBE-NOCARD-' + suf, ITEMS_EJEMPLO)
    o_nc['Payments'][0].pop('CardHolderName', None)
    o_nc['Payments'][0].pop('CardExpirationDate', None)
    casos.append(('PROBE-NOCARD-' + suf, o_nc, 'sin titular ni vencimiento'))

    r = req_lib.post(f'{BASE}/api/order/send',
                     json={'ApiKey': API_KEY, 'LoginToken': token,
                           'AnalysisLocation': location,
                           'Orders': [o for _, o, _ in casos]},
                     headers={'Content-Type': 'application/json',
                              'analysisLocation': location}, timeout=60)
    print(f'  envio HTTP {r.status_code}')
    for oid, _, desc in casos:
        print(f'    {oid:<26} {desc}')
    print('\n  Consultalas con:')
    print('  venv/bin/python3 scripts/clearsale_probe.py get ' +
          ' '.join(i for i, _, _ in casos))


def consultar(token, ids, location='ARG'):
    url = f'{BASE}/api/order/get'
    body = {'ApiKey': API_KEY, 'LoginToken': token,
            'Orders': ids, 'AnalysisLocation': location}
    print(f'\n=== GET {len(ids)} orden(es) ===')
    try:
        r = req_lib.post(url, json=body,
                         headers={'Content-Type': 'application/json',
                                  'analysisLocation': location}, timeout=25)
    except Exception as e:
        print(f'  EXC {type(e).__name__}: {e}')
        return
    _print_resp('order/get', r)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    if not (API_KEY and CLIENT_ID and CLIENT_SECRET):
        print('Faltan CLEARSALE_API_KEY / CLIENT_ID / CLIENT_SECRET en config/.env')
        return 2

    cmd = sys.argv[1]
    print(f'ENTORNO: {BASE} (sandbox)\n')

    token = login()
    if not token:
        print('\nSin token no se puede seguir.')
        return 3
    if cmd == 'login':
        return 0

    if cmd == 'location':
        probar_location(token)
    elif cmd == 'items':
        probar_items(token)
    elif cmd == 'state':
        probar_state(token)
    elif cmd == 'montos':
        probar_montos(token)
    elif cmd == 'variantes':
        probar_variantes(token)
    elif cmd == 'get':
        consultar(token, sys.argv[2:])
    elif cmd == 'todo':
        probar_location(token)
        probar_items(token)
        probar_state(token)
    else:
        print(f'Comando desconocido: {cmd}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
