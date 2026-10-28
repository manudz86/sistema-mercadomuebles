#!/usr/bin/env python3
"""Manda los tres avisos de estado de pago (en proceso / confirmado /
rechazado) usando EL MISMO codigo que usa la tienda, para poder ver como
llegan antes de activar el modo '1'.

Uso:
    venv/bin/python3 scripts/probar_avisos_pago.py <email> [--wa <telefono>]
    venv/bin/python3 scripts/probar_avisos_pago.py <email> --solo en_proceso

Sin --wa no manda WhatsApp, solo mail. No toca la base ni ClearSale.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _common import cargar_env  # noqa: E402

for _k, _v in (cargar_env() or {}).items():
    os.environ.setdefault(_k, _v)

import tienda_bp as T  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        return 1
    email = args[0]
    tel = None
    if '--wa' in sys.argv:
        i = sys.argv.index('--wa')
        tel = sys.argv[i + 1] if len(sys.argv) > i + 1 else None
    solo = None
    if '--solo' in sys.argv:
        i = sys.argv.index('--solo')
        solo = sys.argv[i + 1] if len(sys.argv) > i + 1 else None

    tipos = [solo] if solo else ['en_proceso', 'confirmado', 'rechazado']
    for tipo in tipos:
        cfg = T.AVISOS_PAGO.get(tipo)
        if not cfg:
            print(f'  tipo desconocido: {tipo}')
            continue
        numero = f'PW-PRUEBA-{tipo.upper()}'
        print(f'\n{tipo}')
        print(f'  asunto ... {cfg["asunto"].format(numero=numero)}')
        print(f'  plantilla WA ... {cfg["wa"]}')
        T.avisar_estado_pago(tipo, 'Matias', numero,
                             email_cliente=email, telefono_cliente=tel)
    print('\nListo. Revisá la casilla.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
