#!/usr/bin/env python3
"""Revisa si sku_catalog_map monitorea un catalogo donde realmente publicamos.

sku_catalog_map es la lista de catalogos que scrapea el monitor de competencia:
una fila por SKU (sku es UNIQUE) con el catalog_product_id a vigilar. Si ese
catalogo no es el que nuestras publicaciones ocupan, el monitor compara precios
contra competidores de otro producto.

El criterio NO es "el mapa coincide con todas las publis del SKU": un SKU puede
tener publicaciones repartidas en varios catalogos y la tabla solo admite uno.
El criterio es si el catalogo mapeado tiene AL MENOS UNA publi nuestra:

  - con publis  -> la fila sirve, no se toca (aunque el SKU este en otros)
  - sin publis   -> la fila esta vieja; se propone el catalogo donde el SKU
                    realmente tiene publicaciones
  - sin publis y varios candidatos -> no se decide solo, se informa

La verdad sale de mla_catalogo (espejo de lo que reporta ML, refrescado por
scripts/refrescar_catalogo_mla.py).

    scripts/auditar_catalogo_competencia.py            # informe
    scripts/auditar_catalogo_competencia.py --sql      # ademas imprime los UPDATE

Solo SELECTs. No escribe nada.
"""
import sys
from collections import defaultdict

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
import os                                    # noqa: E402
os.environ['CANNON_SIN_SCHEDULER'] = '1'


def main():
    import app as A

    mapa = A.query_db(
        "SELECT sku, catalog_product_id, manual, actualizado_at FROM sku_catalog_map "
        "WHERE catalog_product_id IS NOT NULL AND catalog_product_id <> '' ORDER BY sku")

    # Para cada SKU: en que catalogos tiene publis, y cuantas (de catalogo, vivas)
    publis = defaultdict(lambda: defaultdict(int))
    for r in A.query_db(
            "SELECT m.sku, c.catalog_product_id AS cat, COUNT(*) AS n "
            "FROM sku_mla_mapeo m "
            "JOIN mla_catalogo c ON c.mla_id = m.mla_id "
            "WHERE m.activo = TRUE AND c.catalog_product_id IS NOT NULL "
            "  AND c.status IN ('active','paused') "
            "GROUP BY m.sku, c.catalog_product_id"):
        publis[r['sku'].strip().upper()][r['cat']] = int(r['n'])

    ok, arreglar, ambiguas, sin_publis = [], [], [], []
    for r in mapa:
        sku = r['sku'].strip().upper()
        cat = r['catalog_product_id']
        cands = publis.get(sku, {})
        if cands.get(cat):
            ok.append((sku, cat, cands[cat]))
        elif not cands:
            sin_publis.append((sku, cat, bool(r['manual'])))
        elif len(cands) == 1:
            real, n = next(iter(cands.items()))
            arreglar.append((sku, cat, real, n, bool(r['manual'])))
        else:
            ambiguas.append((sku, cat, cands, bool(r['manual'])))

    print(f'filas en el mapa: {len(mapa)}')
    print()
    print(f'[A] correctas (el catalogo mapeado tiene publis nuestras): {len(ok)}')
    print()
    print(f'[B] para corregir (catalogo mapeado sin publis, un solo candidato): {len(arreglar)}')
    for sku, cat, real, n, man in sorted(arreglar):
        print(f'    {sku:<16} {cat:<14} -> {real:<14} {n} publi(s)'
              f'{"   [manual]" if man else ""}')
    print()
    print(f'[C] ambiguas (sin publis en el mapeado, pero el SKU esta en varios): {len(ambiguas)}')
    for sku, cat, cands, man in sorted(ambiguas):
        detalle = ', '.join(f'{c}({n})' for c, n in
                            sorted(cands.items(), key=lambda x: -x[1]))
        print(f'    {sku:<16} {cat:<14} -> {detalle}{"   [manual]" if man else ""}')
    print()
    print(f'[D] el SKU no tiene ninguna publi de catalogo viva: {len(sin_publis)}')
    for sku, cat, man in sorted(sin_publis):
        print(f'    {sku:<16} {cat}{"   [manual]" if man else ""}')

    if '--sql' in sys.argv and arreglar:
        print()
        print('-- UPDATEs propuestos (solo el grupo B)')
        for sku, cat, real, n, man in sorted(arreglar):
            print(f"UPDATE sku_catalog_map SET catalog_product_id='{real}' "
                  f"WHERE sku='{sku}' AND catalog_product_id='{cat}';")
    return 0


if __name__ == '__main__':
    sys.exit(main())
