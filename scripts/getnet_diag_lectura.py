#!/usr/bin/env python3
"""Diagnostico de SOLO LECTURA contra la API de GetNet de produccion.

A diferencia de getnet_consultar_pago.py, imprime el CUERPO de la respuesta
tambien cuando falla (403/404/etc). Sirve para saber por que se rechaza la
consulta y poder citarlo al pedirle a GetNet que habilite el scope de lectura.

Uso:  venv/bin/python3 scripts/getnet_diag_lectura.py <id> [<id> ...]

Solo hace GET. No modifica nada. Nunca imprime el token ni las credenciales.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests as req_lib  # noqa: E402
from app import app  # noqa: E402
from tienda_bp import _getnet_get_token  # noqa: E402

RUTAS = [
    '/digital-checkout/v1/payment-intent/{pid}',
    '/digital-checkout/v1/payment-intent/{pid}/status',
    '/digital-checkout/v1/payment/{pid}',
    '/v1/payments/{pid}',
]

# Cabeceras que ayudan a entender el rechazo (nunca mostramos Authorization).
HDRS_INTERES = ('www-authenticate', 'x-request-id', 'x-correlation-id',
                'content-type', 'date')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    with app.app_context():
        base = os.getenv('GETNET_BASE_URL')
        try:
            token = _getnet_get_token()
        except Exception as e:
            print(f'No se pudo obtener el token: {type(e).__name__}: {e}')
            return 2
        print(f'ENTORNO: {base} (produccion, solo GET)')
        print(f'TOKEN: obtenido OK ({len(token)} chars, no se muestra)\n')

        for pid in sys.argv[1:]:
            print(f'═══ id {pid} ═══')
            for ruta in RUTAS:
                url = base + ruta.format(pid=pid)
                try:
                    r = req_lib.get(
                        url,
                        headers={'Authorization': f'Bearer {token}',
                                 'Accept': 'application/json'},
                        timeout=20,
                    )
                except Exception as e:
                    print(f'  {ruta:<52} EXC {type(e).__name__}: {e}')
                    continue

                print(f'  {ruta:<52} HTTP {r.status_code}')
                for h in HDRS_INTERES:
                    if h in r.headers:
                        print(f'      {h}: {r.headers[h]}')
                cuerpo = (r.text or '').strip()
                if cuerpo:
                    print(f'      body: {cuerpo[:1200]}')
                else:
                    print('      body: (vacio)')
                print()
            print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
