#!/usr/bin/env python3
"""Renderiza /rentabilidad sin pasar por el login y verifica el form de recalculo.

Comprueba que el campo "desde" venga precargado con la vigencia de la ultima
lista y que exista el "hasta". Solo lectura.

Uso:  venv/bin/python3 scripts/check_rentabilidad_form.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import render_template  # noqa: E402

from app import app, _ultima_vigencia_lista  # noqa: E402


def main():
    with app.app_context():
        vig = _ultima_vigencia_lista()
    print(f'ultima vigencia de la lista: {vig or "(ninguna)"}')

    with app.test_request_context('/rentabilidad'):
        html = render_template(
            'rentabilidad.html', ventas=[], desde='', hasta='', totales={},
            sku_filter='', envio_filter='', canal_filter='',
            config_envio={'flete_propio': 0, 'delega': 0},
            ultima_vigencia=vig)

    # La pagina tiene varios campos "desde" (los filtros): hay que mirar SOLO
    # dentro del form de recalculo.
    m = re.search(r'action="[^"]*recalcular-costos".*?</form>', html, re.S)
    if not m:
        print('  NO encontre el form de recalculo')
        return 1
    form = m.group(0)
    desde = re.findall(r'name="desde"[^>]*value="([^"]*)"', form)
    tiene_hasta = 'name="hasta"' in form
    print(f'HTML: {len(html):,} chars')
    print(f'  form de recalculo encontrado ({len(form)} chars)')
    print(f'  campo "desde" precargado : {desde}')
    print(f'  campo "hasta" presente   : {"si" if tiene_hasta else "NO"}')
    ok = bool(desde) and desde[0] == vig and tiene_hasta
    print(f'\n{"TODO OK" if ok else "REVISAR"}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
