#!/usr/bin/env python3
"""Inconsistencias entre SKUs y catálogos de ML (SOLO LECTURA).

Cruza sku_mla_mapeo (publi -> SKU) con mla_catalogo (publi -> catálogo) y
sku_catalog_map (SKU -> catálogo que usa el monitor de competencia):

  A) Catálogos cuyas publis están mapeadas a SKUs distintos. Si un catálogo
     tiene 5 publis como SEXEP140 y 1 como SREP140, esa 1 es sospechosa.
  B) SKUs cuyas publis caen en catálogos distintos.
  C) sku_catalog_map que no coincide con el catálogo mayoritario de las
     publis de ese SKU, o el mismo catálogo asignado a 2 SKUs.

Las variantes de un mismo producto (_DEP / _FULL) se agrupan como un solo SKU.

Uso: venv/bin/python3 scripts/auditar_sku_catalogo.py [--incluir-inactivas]
"""
import os
import re
import sys
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import conectar_db  # noqa: E402


def conectar():
    return conectar_db(solo_lectura=True)  # usuario cannon_ro, sin permiso de escritura


def base(sku):
    """Agrupa variantes del mismo producto: _DEP/_FULL y la Z final de las
    publis con demora (ver GLOSSARY.md, igual que normalizar_sku_ml)."""
    s = re.sub(r'_(DEP|FULL)$', '', (sku or '').strip().upper())
    return re.sub(r'Z$', '', s)


def main():
    incluir_inactivas = '--incluir-inactivas' in sys.argv
    db = conectar()
    cur = db.cursor()
    filtro = '' if incluir_inactivas else 'WHERE m.activo = 1'
    cur.execute(f"""
        SELECT m.sku, m.mla_id, m.titulo_ml, m.activo, c.catalog_product_id AS cat, c.status
        FROM sku_mla_mapeo m
        JOIN mla_catalogo c ON c.mla_id = m.mla_id
        {filtro}""")
    filas = [r for r in cur.fetchall() if r['cat']]
    cur.execute("SELECT sku, catalog_product_id AS cat, manual FROM sku_catalog_map")
    scm = cur.fetchall()
    cur.close()
    db.close()

    por_cat = defaultdict(list)
    por_sku = defaultdict(list)
    for r in filas:
        por_cat[r['cat']].append(r)
        por_sku[base(r['sku'])].append(r)

    # A) catálogo -> varios SKUs
    print('=' * 100)
    print('A) CATÁLOGOS CON PUBLIS MAPEADAS A SKUs DISTINTOS')
    print('=' * 100)
    n_a = 0
    for cat, rs in sorted(por_cat.items()):
        cnt = Counter(base(r['sku']) for r in rs)
        if len(cnt) < 2:
            continue
        n_a += 1
        mayor = cnt.most_common(1)[0][0]
        print(f'\n{cat}  ->  ' + ', '.join(f'{s} x{n}' for s, n in cnt.most_common()))
        for r in sorted(rs, key=lambda x: (base(x['sku']) == mayor, x['sku'])):
            marca = '   ' if base(r['sku']) == mayor else '>> '
            print(f"  {marca}{r['mla_id']:<15} {r['sku']:<14} {r['status'] or '':<12} "
                  f"{(r['titulo_ml'] or '')[:60]}")
    print(f'\nTotal A: {n_a} catálogos')

    # B) SKU -> varios catálogos
    print('\n' + '=' * 100)
    print('B) SKUs CON PUBLIS EN CATÁLOGOS DISTINTOS')
    print('=' * 100)
    mayor_cat = {}
    n_b = 0
    for sku, rs in sorted(por_sku.items()):
        cnt = Counter(r['cat'] for r in rs)
        mayor_cat[sku] = cnt.most_common(1)[0][0]
        if len(cnt) < 2:
            continue
        n_b += 1
        print(f'\n{sku}  ->  ' + ', '.join(f'{c} x{n}' for c, n in cnt.most_common()))
        for r in rs:
            if r['cat'] != mayor_cat[sku]:
                print(f"   >> {r['mla_id']:<15} {r['cat']:<14} {(r['titulo_ml'] or '')[:60]}")
    print(f'\nTotal B: {n_b} SKUs')

    # C) sku_catalog_map vs mayoría
    print('\n' + '=' * 100)
    print('C) sku_catalog_map (monitor de competencia) vs CATÁLOGO DE LAS PUBLIS')
    print('=' * 100)
    n_c = 0
    cats_scm = defaultdict(list)
    for r in scm:
        cats_scm[r['cat']].append(r['sku'])
        sb = base(r['sku'])
        if sb in mayor_cat and r['cat'] and r['cat'] != mayor_cat[sb]:
            otros = sorted({base(x['sku']) for x in por_cat.get(r['cat'], [])})
            n_c += 1
            print(f"  {r['sku']:<14} map={r['cat']:<14} publis={mayor_cat[sb]:<14} "
                  f"manual={r['manual']}  publis del cat del map: {', '.join(otros) or '-'}")
    for cat, skus in cats_scm.items():
        if cat and len(skus) > 1:
            n_c += 1
            print(f"  catálogo {cat} asignado a varios SKUs: {', '.join(skus)}")
    print(f'\nTotal C: {n_c}')


if __name__ == '__main__':
    sys.exit(main())
