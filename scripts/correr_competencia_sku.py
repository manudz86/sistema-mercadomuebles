#!/usr/bin/env python3
"""Corre el monitor de competencia para uno o varios SKU puntuales.

Sirve para reparar o verificar sin esperar al job completo, que tarda ~2 h.
Recorre TODOS los catalogos de cada SKU, que es el punto: un SKU puede competir
en varios.

ESCRIBE en competencia_snapshots (reemplaza lo del dia para esos pares
SKU/catalogo). Solo lee de ML.

    scripts/correr_competencia_sku.py PLATINOX2
    scripts/correr_competencia_sku.py PLATINOX2 SREP140 --delay 10
"""
import os
import sys
import time

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
os.environ.setdefault('CANNON_SIN_SCHEDULER', '1')


def main():
    import app as A
    import competencia_bp as C

    # Se saltea tanto el flag como su valor, si no el numero entra como SKU
    args = sys.argv[1:]
    delay, skus, i = 10, [], 0
    while i < len(args):
        if args[i] == '--delay':
            try:
                delay = int(args[i + 1])
            except (IndexError, ValueError):
                pass
            i += 2
            continue
        if not args[i].startswith('--'):
            skus.append(args[i].upper())
        i += 1
    if not skus:
        print(__doc__)
        return 1

    total = 0
    for sku in skus:
        cats = C._get_catalogos(sku)
        if not cats:
            print(f'{sku}: sin catalogos en el mapa')
            continue
        print(f'{sku}: {len(cats)} catalogo(s) — {", ".join(cats)}')
        for i, cat in enumerate(cats):
            if i:
                time.sleep(delay)
            t0 = time.time()
            try:
                n = C._snapshot_catalogo(sku, cat)
                total += n
                print(f'   {cat}  {n} fila(s)  ({time.time() - t0:.0f}s)')
            except Exception as e:
                print(f'   {cat}  ERROR: {e}')

    print()
    print(f'filas escritas: {total}')
    for sku in skus:
        print(f'--- {sku} en los snapshots de hoy ---')
        for r in A.query_db(
                "SELECT catalog_product_id, COUNT(*) n, SUM(es_propio) propias "
                "FROM competencia_snapshots WHERE sku=%s AND DATE(fecha)=CURDATE() "
                "GROUP BY catalog_product_id ORDER BY catalog_product_id", (sku,)):
            print(f'   {r["catalog_product_id"]:<14} {r["n"]:>3} publis '
                  f'({int(r["propias"] or 0)} nuestras)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
