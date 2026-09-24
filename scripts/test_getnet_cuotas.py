#!/usr/bin/env python3
"""Crea un payment-intent en el SANDBOX (UAT) de GetNet y devuelve la URL del
checkout, para ver si el comprador puede elegir la cantidad de cuotas.

SIEMPRE usa UAT (force_uat=True): no mueve plata real ni registra ventas.

Uso:  venv/bin/python3 scripts/test_getnet_cuotas.py [monto]
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests as req_lib  # noqa: E402
from app import app  # noqa: E402
from tienda_bp import _getnet_get_token  # noqa: E402


def main():
    monto = int(sys.argv[1]) if len(sys.argv) > 1 else 1000000

    with app.app_context():
        base_url = os.getenv('GETNET_BASE_URL_UAT')
        token = _getnet_get_token(force_uat=True)
        ref = f"TEST-CUOTAS-{int(time.time())}"
        body = {
            "order_id": ref,
            "redirect_urls": {
                "success": "https://www.mercadomuebles.com.ar/tienda/pago/exito-getnet/" + ref,
                "failed": "https://www.mercadomuebles.com.ar/tienda/pago/error?canal=getnet",
            },
            # igual que produccion: NO se manda ningun campo de cuotas
            "payment": {"amount": monto * 100, "currency": "ARS"},
            "product": [{"title": "Prueba cuotas", "value": monto * 100, "quantity": 1}],
            "customer": {
                "customer_id": "test-admin", "first_name": "Admin", "last_name": "Test",
                "name": "Admin Test", "email": "admin@mercadomuebles.com.ar",
                "document_type": "dni", "document_number": "00000000",
                "phone_number": "5491100000000",
            },
        }
        print(f'ENTORNO : {base_url}  (sandbox UAT)')
        print(f'MONTO   : ${monto:,}')
        print(f'PAYLOAD : payment={json.dumps(body["payment"])}')
        print('          (sin campo installments — igual que el checkout real)\n')

        r = req_lib.post(f"{base_url}/digital-checkout/v1/payment-intent", json=body,
                         headers={'Authorization': f'Bearer {token}',
                                  'Content-Type': 'application/json'}, timeout=20)
        print(f'HTTP {r.status_code}')
        if r.status_code >= 300:
            print(r.text[:800])
            return 1
        d = r.json()
        print(f'payment_intent_id: {d.get("payment_intent_id")}')
        print(f'URL_CHECKOUT: {d.get("redirect_url")}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
