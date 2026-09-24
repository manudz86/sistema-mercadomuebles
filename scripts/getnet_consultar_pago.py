#!/usr/bin/env python3
"""Consulta (GET, solo lectura) un payment-intent en la API de GetNet de PRODUCCION
para ver que cuotas quedaron registradas.

Uso:  venv/bin/python3 scripts/getnet_consultar_pago.py <payment_intent_id> [...]
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests as req_lib  # noqa: E402
from app import app  # noqa: E402
from tienda_bp import _getnet_get_token  # noqa: E402

RUTAS = [
    '/digital-checkout/v1/payment-intent/{pid}',
    '/digital-checkout/v1/payment-intent/{pid}/status',
    '/v1/payments/{pid}',
]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    with app.app_context():
        base = os.getenv('GETNET_BASE_URL')
        token = _getnet_get_token()
        print(f'ENTORNO: {base} (produccion, solo GET)\n')
        for pid in sys.argv[1:]:
            print(f'=== payment_intent {pid} ===')
            for ruta in RUTAS:
                url = base + ruta.format(pid=pid)
                try:
                    r = req_lib.get(url, headers={'Authorization': f'Bearer {token}'}, timeout=20)
                except Exception as e:
                    print(f'  {ruta:<52} EXC {type(e).__name__}')
                    continue
                print(f'  {ruta:<52} HTTP {r.status_code}')
                if r.status_code == 200:
                    try:
                        d = r.json()
                    except Exception:
                        print(f'    (respuesta no JSON): {r.text[:200]}')
                        continue
                    print(json.dumps(d, indent=2, ensure_ascii=False)[:2500])
                    pay = d.get('payment') or {}
                    inst = pay.get('installment') or pay.get('installments')
                    print(f'\n    >>> CUOTAS: {inst if inst else "el campo no viene en la respuesta"}')
                    break
            print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
