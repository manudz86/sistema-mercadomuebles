#!/usr/bin/env python3
"""Por que un catalogo del mapa no dejo filas en la ultima corrida.

La corrida de hoy proceso 126 pares (SKU, catalogo) sin errores pero solo 94
catalogos quedaron en competencia_snapshots. Esto compara, paso por paso, lo
que el agente deberia recorrer contra lo que efectivamente guardo, y prueba un
catalogo puntual contra ML para ver si la API devuelve algo.

    scripts/diag_corrida_competencia.py                # el panorama
    scripts/diag_corrida_competencia.py MLA34984270    # ademas prueba ese

Solo lecturas y GETs a ML.
"""
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
os.environ['CANNON_SIN_SCHEDULER'] = '1'


def main():
    import app as A
    import competencia_bp as C

    skus = C._get_skus_monitorear()
    print(f'SKUs que el agente recorre: {len(skus)}')

    pares = []
    for s in skus:
        for c in C._get_catalogos(s):
            pares.append((s, c))
    print(f'pares (SKU, catalogo) que deberia visitar: {len(pares)}')
    print(f'catalogos distintos ahi: {len(set(c for _, c in pares))}')

    hechos = {r['catalog_product_id'] for r in A.query_db(
        "SELECT DISTINCT catalog_product_id FROM competencia_snapshots "
        "WHERE DATE(fecha)=CURDATE() AND catalog_product_id IS NOT NULL")}
    print(f'catalogos con filas hoy: {len(hechos)}')

    faltan = [(s, c) for s, c in pares if c not in hechos]
    print()
    print(f'pares visitados que no dejaron ninguna fila: {len(faltan)}')
    for s, c in faltan[:25]:
        print(f'    {s:<16} {c}')

    # Los que estan en el mapa pero el agente ni los mira
    del_mapa = {(r['sku'].strip().upper(), r['catalog_product_id'])
                for r in A.query_db("SELECT sku, catalog_product_id FROM sku_catalog_map "
                                    "WHERE catalog_product_id IS NOT NULL")}
    ni_mirados = sorted(del_mapa - set(pares))
    print()
    print(f'pares del mapa que el agente NO recorre (el SKU no esta en la lista): '
          f'{len(ni_mirados)}')
    for s, c in ni_mirados[:25]:
        print(f'    {s:<16} {c}')

    pedido = [a for a in sys.argv[1:] if a.startswith('MLA')]
    for cat in pedido:
        print()
        print(f'probando {cat} contra ML (lo que hace _ml_catalog_all)...')
        res = C._ml_catalog_all(cat, '1425')
        print(f'   la API devolvio {len(res)} publicaciones')
        propias = [r for r in res if r.get('seller_id') == C.MY_SELLER_ID]
        print(f'   de las cuales nuestras: {len(propias)}')
        if res[:1]:
            r0 = res[0]
            print(f'   ejemplo: item {r0.get("item_id")} seller {r0.get("seller_id")} '
                  f'precio {(r0.get("price") or {})}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
