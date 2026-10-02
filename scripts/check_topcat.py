#!/usr/bin/env python3
"""Renderiza la pagina de Top catalogo sin pasar por el login, para validarla.

Solo lectura: no toca datos. Deja el HTML en /tmp/topcat.html.

Uso:  venv/bin/python3 scripts/check_topcat.py [periodo]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import render_template  # noqa: E402

from app import app  # noqa: E402
from competencia_v2_bp import topcat_datos, _periodo_lbl, PERIODOS  # noqa: E402

SALIDA = '/tmp/topcat.html'


def main():
    periodo = sys.argv[1] if len(sys.argv) > 1 else '2026-09'
    with app.test_request_context('/admin/competencia-v2/top-catalogo'):
        pers = sorted(PERIODOS().keys(), reverse=True)
        secciones = topcat_datos(periodo, 15)
        html = render_template('competencia_top_catalogo.html',
                               periodo=periodo, periodos=pers,
                               periodo_lbl={p: _periodo_lbl(p) for p in pers},
                               top=15, secciones=secciones)
    with open(SALIDA, 'w', encoding='utf-8') as fh:
        fh.write(html)

    print(f'HTML generado      : {len(html):,} chars -> {SALIDA}')
    print(f'secciones          : {len(secciones)}')
    print(f'filas de tabla     : {html.count("<tr data-producto")}')
    print(f'columnas ordenables: {html.count("data-k=")}')
    print(f'links a catalogo ML: {len(re.findall(r"mercadolibre.com.ar/p/MLA", html))}')
    for s in secciones:
        print(f'  - {s["titulo"]}: {len(s["items"])} items, '
              f'{s["cat_u"]}u de catalogo ({s["pct_cat"]}%)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
