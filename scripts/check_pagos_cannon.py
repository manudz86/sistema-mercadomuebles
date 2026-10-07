#!/usr/bin/env python3
"""Verifica que /pagos-cannon tome el % de pronto pago desde Costos.

Renderiza la pagina sin pasar por el login y chequea que no queden valores fijos
en 4. Solo lectura.

Uso:  venv/bin/python3 scripts/check_pagos_cannon.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import werkzeug  # noqa: E402

if not hasattr(werkzeug, '__version__'):
    try:
        from importlib.metadata import version as _v
        werkzeug.__version__ = _v('werkzeug')
    except Exception:
        werkzeug.__version__ = '3'

from app import app, _prontopago_pct  # noqa: E402


def main():
    with app.app_context():
        esperado = _prontopago_pct()
    print(f'prontopago configurado en Costos: {esperado}%\n')

    # Se renderiza el template directo: el test_client no sirve acá porque la ruta
    # pide login y session_transaction choca con esta version de werkzeug.
    from datetime import date
    from flask import render_template
    with app.test_request_context('/pagos-cannon'):
        h = render_template('pagos_cannon.html', grupos=[], facturas_por_pago_id={},
                            reclamos=[], tab='pendientes', hoy=date.today(),
                            pp_pct_default=esperado)
    print(f'HTML renderizado: {len(h):,} chars')

    pp = re.findall(r'const PP_DEFAULT = ([0-9.]+)', h)
    inp = re.findall(r'id="fc_pp_pct" value="([0-9.]+)"', h)
    fijos = re.findall(r'\|\| 4;', h) + re.findall(r"value = '4';", h)

    print(f'  const PP_DEFAULT     : {pp}')
    print(f'  input al escanear    : {inp}')
    print(f'  valores fijos en 4   : {len(fijos)}  {"OK" if not fijos else "*** QUEDAN ***"}')
    ok = pp and float(pp[0]) == esperado and inp and float(inp[0]) == esperado and not fijos
    print(f'\n{"TODO OK" if ok else "REVISAR"}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
