#!/usr/bin/env python3
"""Compara cotizaciones Zipnova (SOLO cotiza, no crea envíos) para un sommier a un CP,
con distintas variantes de bultos, para entender diferencias contra la web de Zipnova.
Uso: venv/bin/python scripts/diag_zipnova_cotizador.py [SKU] [CP] [CIUDAD] [PROVINCIA] [DECLARADO]
"""
import copy
import json
import os
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import requests  # noqa: E402
import werkzeug  # noqa: E402
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3'
import app as A  # noqa: E402

sku = sys.argv[1] if len(sys.argv) > 1 else 'SREP160'
cp = sys.argv[2] if len(sys.argv) > 2 else '9000'
ciudad = sys.argv[3] if len(sys.argv) > 3 else 'Comodoro Rivadavia'
prov = sys.argv[4] if len(sys.argv) > 4 else 'Chubut'
declarado = int(sys.argv[5]) if len(sys.argv) > 5 else 1000000


def cotizar(items, extra=None):
    payload = {'account_id': A.ZIPNOVA_ACCOUNT_ID_ADM, 'origin_id': A.ZIPNOVA_ORIGIN_ID_ADM,
               'declared_value': declarado,
               'destination': {'zipcode': cp, 'city': ciudad, 'state': prov}, 'items': items}
    payload.update(extra or {})
    r = requests.post(f'{A.ZIPNOVA_BASE_URL_ADM}/shipments/quote', json=payload,
                      auth=A._zipnova_auth_adm(), timeout=20)
    return r.status_code, r.json() if r.headers.get('content-type', '').startswith('application/json') else r.text


def mostrar(titulo, items, extra=None, detalle=False):
    st, d = cotizar(items, extra)
    print(f'\n== {titulo} (HTTP {st}) ==')
    for b in items:
        print(f"   bulto {b['sku']:<16} {b['weight']/1000:>5.1f} kg  {b['length']}x{b['width']}x{b['height']}")
    if not isinstance(d, dict):
        print('  ', str(d)[:300])
        return
    if detalle:
        print('   claves respuesta:', list(d.keys()))
    for clave in ('all_results',):
        res = d.get(clave) or []
        print(f'   [{clave}] {len(res)}')
        for r in res:
            a = r.get('amounts') or {}
            print(f"   {(r.get('carrier') or {}).get('name', '?'):<14} {(r.get('service_type') or {}).get('code', '?'):<20} "
                  f"price={a.get('price')} incl_tax={a.get('price_incl_tax')} "
                  f"dias={(r.get('delivery_time') or {}).get('max')}")
    if detalle:
        res = d.get('all_results') or []
        if res:
            r0 = {k: v for k, v in res[0].items() if k not in ('carrier',)}
            print('   ejemplo resultado:', json.dumps(r0, ensure_ascii=False)[:1500])
        for k, v in d.items():
            if k not in ('all_results',):
                print(f'   {k}: {json.dumps(v, ensure_ascii=False)[:600]}')


with A.app.app_context():
    nuestros = A._armar_bultos_cotizador([{'sku': sku, 'cantidad': 1}])
mostrar('Como cotiza el sistema hoy', nuestros, detalle=True)

alto22 = copy.deepcopy(nuestros)
for b in alto22:
    if not b['sku'].startswith(('BASE_', 'PATAS')):
        b['height'] = 22
mostrar('Colchón con 22 cm de alto (como en la web)', alto22)

web = [
    {'sku': 'PATAX12', 'description': 'PATAX12', 'weight': 1000, 'height': 20, 'width': 16, 'length': 30},
    {'sku': 'crep160', 'description': 'crep160', 'weight': 33000, 'height': 22, 'width': 160, 'length': 200},
    {'sku': 'BASE_GRIS80200', 'description': 'BASE_GRIS80200', 'weight': 20000, 'height': 21, 'width': 80, 'length': 200},
    {'sku': 'BASE_GRIS80200', 'description': 'BASE_GRIS80200', 'weight': 20000, 'height': 21, 'width': 80, 'length': 200},
]
mostrar('Exactamente los bultos de la web', web)
