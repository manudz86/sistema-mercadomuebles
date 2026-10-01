#!/usr/bin/env python3
"""Top N productos de CATALOGO mas vendidos en Real Trends, por categoria.

Toma los JSON acumulados de Real Trends, descarta las publicaciones que NO son
de catalogo, agrupa por catalog_product_id y suma unidades y facturacion.
Trae el nombre oficial del catalogo desde la API de ML (GET, solo lectura).

Uso:
    venv/bin/python3 scripts/rt_top_catalogo.py 2026-09
    venv/bin/python3 scripts/rt_top_catalogo.py 2026-09 --top 20
    venv/bin/python3 scripts/rt_top_catalogo.py 2026-09 --csv /tmp/top.csv
"""
import os
import sys
import csv
import json
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE, 'config/.env'))

from competencia_v2_bp import DATA_DIR  # noqa: E402

CATEGORIAS = [
    ('colchones.json', 'COLCHONES'),
    ('sommiers.json', 'JUEGOS DE SOMMIER Y COLCHON'),
]


def nombres_catalogo(ids):
    """{catalog_id: nombre oficial} desde la API de ML. Si falla, queda vacio."""
    out = {}
    try:
        from app import app, cargar_ml_token, ml_request
    except Exception:
        return out
    with app.app_context():
        tok = cargar_ml_token()
        if not tok:
            return out
        for cid in ids:
            mla = cid if str(cid).startswith('MLA') else f'MLA{cid}'
            try:
                r = ml_request('get', f'https://api.mercadolibre.com/products/{mla}', tok)
                if r.status_code == 200:
                    d = r.json() or {}
                    # 'name' trae la medida ("... 80 X 190 X 13"); 'family_name' no,
                    # y sin ella varias medidas del mismo modelo se ven identicas.
                    out[cid] = (d.get('name') or d.get('family_name') or '').strip()
            except Exception:
                pass
    return out


def main():
    periodo = next((a for a in sys.argv[1:] if len(a) == 7 and a[:4].isdigit()), None)
    if not periodo:
        print(__doc__)
        return 1
    top = int(sys.argv[sys.argv.index('--top') + 1]) if '--top' in sys.argv else 15
    csv_out = sys.argv[sys.argv.index('--csv') + 1] if '--csv' in sys.argv else None

    filas_csv = []
    for fname, titulo in CATEGORIAS:
        path = os.path.join(DATA_DIR, periodo, fname)
        if not os.path.exists(path):
            print(f'{titulo}: no hay datos para {periodo}')
            continue
        rows = json.load(open(path, encoding='utf-8'))

        total_u = total_f = 0
        agg = defaultdict(lambda: {'u': 0, 'f': 0.0, 'titulos': Counter(),
                                   'publis': set(), 'vendedores': set()})
        sin_cat_u = sin_cat_f = 0
        for r in rows:
            try:
                q = int(round(float(r.get('sold_quantity') or 0)))
                p = float(r.get('price') or 0)
            except (TypeError, ValueError):
                continue
            total_u += q
            total_f += p * q
            es_cat = str(r.get('is_catalog_product') or '').lower() == 'yes'
            cid = str(r.get('catalog_product_id') or '').strip()
            if not es_cat or not cid:
                sin_cat_u += q
                sin_cat_f += p * q
                continue
            a = agg[cid]
            a['u'] += q
            a['f'] += p * q
            if r.get('title'):
                a['titulos'][r['title']] += q
            if r.get('item_id'):
                a['publis'].add(r['item_id'])
            if r.get('nickname'):
                a['vendedores'].add(r['nickname'])

        orden = sorted(agg.items(), key=lambda kv: -kv[1]['u'])[:top]
        nombres = nombres_catalogo([cid for cid, _ in orden])

        cat_u = sum(v['u'] for v in agg.values())
        cat_f = sum(v['f'] for v in agg.values())
        print(f'\n{"="*104}')
        print(f'{titulo}  —  {periodo}')
        print(f'{"="*104}')
        print(f'  total del mes      : {total_u:>6} u   ${total_f:>16,.0f}')
        print(f'  de catalogo        : {cat_u:>6} u   ${cat_f:>16,.0f}   '
              f'({cat_u/total_u*100:.0f}% de las unidades)')
        print(f'  sin catalogo (fuera): {sin_cat_u:>5} u   ${sin_cat_f:>16,.0f}')
        print(f'  productos de catalogo distintos: {len(agg)}\n')

        print(f'  {"#":<3} {"catalogo":<14} {"u":>5} {"facturacion":>16} {"publis":>7} {"vend":>5}  producto')
        print('  ' + '-' * 100)
        for i, (cid, v) in enumerate(orden, 1):
            nom = nombres.get(cid) or (v['titulos'].most_common(1)[0][0] if v['titulos'] else '')
            print(f'  {i:<3} MLA{cid:<11} {v["u"]:>5} ${v["f"]:>15,.0f} '
                  f'{len(v["publis"]):>7} {len(v["vendedores"]):>5}  {nom[:66]}')
            filas_csv.append({
                'categoria': titulo, 'puesto': i, 'catalogo': f'MLA{cid}',
                'producto': nom, 'unidades': v['u'], 'facturacion': round(v['f']),
                'publicaciones': len(v['publis']), 'vendedores': len(v['vendedores']),
            })

    if csv_out and filas_csv:
        with open(csv_out, 'w', newline='', encoding='utf-8-sig') as fh:
            w = csv.DictWriter(fh, fieldnames=list(filas_csv[0].keys()), delimiter=';')
            w.writeheader()
            w.writerows(filas_csv)
        print(f'\nCSV: {csv_out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
