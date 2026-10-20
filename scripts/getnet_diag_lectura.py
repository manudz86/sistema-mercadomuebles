#!/usr/bin/env python3
"""Diagnostico de SOLO LECTURA contra la API de GetNet de produccion.

A diferencia de getnet_consultar_pago.py, imprime el CUERPO de la respuesta
tambien cuando falla (403/404/etc). Sirve para saber por que se rechaza la
consulta y poder citarlo al pedirle a GetNet que habilite el scope de lectura.

Uso:  venv/bin/python3 scripts/getnet_diag_lectura.py <id> [<id> ...]
      venv/bin/python3 scripts/getnet_diag_lectura.py /ruta/completa [...]

Un argumento que empieza con "/" se consulta tal cual contra GETNET_BASE_URL;
cualquier otro se interpreta como id y se prueba contra las RUTAS conocidas.

Solo hace GET. No modifica nada. Nunca imprime el token ni las credenciales.
"""
import base64
import json
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


def mostrar_scopes(token):
    """Imprime SOLO los claims de alcance del JWT. Nunca el token ni la firma."""
    try:
        payload_b64 = token.split('.')[1]
        payload_b64 += '=' * (-len(payload_b64) % 4)   # padding base64url
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as e:
        print(f'  (no se pudo decodificar el JWT: {type(e).__name__})')
        return
    for k in ('scope', 'scopes', 'authorities', 'aud', 'iss', 'exp', 'resource_access'):
        if k in claims:
            v = claims[k]
            if isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False)
            print(f'  {k}: {v}')
    otros = [k for k in claims if k not in
             ('scope', 'scopes', 'authorities', 'aud', 'iss', 'exp', 'resource_access')]
    if otros:
        print(f'  (otros claims presentes, no mostrados: {", ".join(sorted(otros))})')


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
        print(f'TOKEN: obtenido OK ({len(token)} chars, no se muestra)')
        print('ALCANCES DEL TOKEN:')
        mostrar_scopes(token)
        print()

        for arg in sys.argv[1:]:
            if arg.startswith('/'):
                print(f'═══ ruta {arg} ═══')
                rutas, pid = [arg], ''
            else:
                print(f'═══ id {arg} ═══')
                rutas, pid = RUTAS, arg
            for ruta in rutas:
                url = base + (ruta.format(pid=pid) if pid else ruta)
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
