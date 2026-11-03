#!/usr/bin/env python3
"""Audita si el buscador por MLA de catalogo llega a todas nuestras publis.

El buscador resuelve asi:

    catalogo C -> SKUs de sku_catalog_map con ese catalog_product_id
               -> MLAs de esos SKUs en sku_mla_mapeo
               -> se filtran los que ML reporta con catalog_product_id = C

Entonces una publi de catalogo es alcanzable si y solo si existe una fila
(sku, C) en sku_catalog_map cuyo sku tenga esa publi en sku_mla_mapeo. Eso es
lo que mide este script, publi por publi. No se agrupa por el SKU que ML tiene
cargado en la publi (seller_custom_field), porque diverge del SKU interno en
las variantes (PLATINOX2-TOP y PLATINOX2-VELLON son PLATINOX2 en ML).

Solo GETs a ML y SELECTs. No escribe nada en la base.
La respuesta de ML se cachea en un JSON para poder reanalizar sin reconsultar;
--refrescar la vuelve a pedir.
"""
import json
import os
import sys
from collections import defaultdict

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
os.environ['CANNON_SIN_SCHEDULER'] = '1'

ATTRS = 'id,catalog_listing,catalog_product_id,status,seller_custom_field,title'
CACHE = '/tmp/claude-0/-home-cannon-app/79b06826-d8a0-4536-a6c4-d75cdbfd55e8/scratchpad/items_ml_catalogo.json'


def traer_de_ml(A, mlas, tok):
    items = {}
    fallidos = []
    for i in range(0, len(mlas), 20):
        chunk = mlas[i:i + 20]
        r = A.ml_request('get', 'https://api.mercadolibre.com/items', tok,
                         params={'ids': ','.join(chunk), 'attributes': ATTRS})
        if r.status_code != 200:
            fallidos.extend(chunk)
            continue
        for it in r.json():
            cuerpo = it.get('body') or {}
            if it.get('code') != 200 or not cuerpo.get('id'):
                fallidos.append(cuerpo.get('id') or '?')
                continue
            items[cuerpo['id']] = cuerpo
        print(f'\r  {min(i + 20, len(mlas))}/{len(mlas)}', end='', flush=True)
    print()
    return items, fallidos


def main():
    import app as A

    refrescar = '--refrescar' in sys.argv

    filas = A.query_db("SELECT sku, mla_id FROM sku_mla_mapeo WHERE activo = TRUE")
    # Una publi puede estar mapeada a mas de un SKU: guardo todos
    skus_de_mla = defaultdict(set)
    mlas_de_sku = defaultdict(set)
    for f in filas:
        s = f['sku'].strip().upper()
        skus_de_mla[f['mla_id']].add(s)
        mlas_de_sku[s].add(f['mla_id'])
    mlas = sorted(skus_de_mla)
    print(f'publicaciones en sku_mla_mapeo (activas): {len(mlas)}')

    if not refrescar and os.path.exists(CACHE):
        with open(CACHE) as fh:
            items = json.load(fh)
        print(f'usando el cache de ML: {len(items)} publis ({CACHE})')
        fallidos = []
    else:
        tok = A.cargar_ml_token()
        if not tok:
            print('No hay token de ML configurado.')
            return 1
        items, fallidos = traer_de_ml(A, mlas, tok)
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, 'w') as fh:
            json.dump(items, fh)
    if fallidos:
        print(f'no se pudieron consultar {len(fallidos)}: {fallidos[:10]}')

    # Publis de catalogo segun ML (solo las que estan en juego: activas o pausadas)
    cat_de_mla = {}
    sin_id = []
    for mla, d in items.items():
        if not d.get('catalog_listing') or d.get('status') not in ('active', 'paused'):
            continue
        if not d.get('catalog_product_id'):
            sin_id.append((mla, d.get('status')))
            continue
        cat_de_mla[mla] = d['catalog_product_id']

    # El mapa, indexado como lo usa el buscador
    mapa = A.query_db("SELECT sku, catalog_product_id FROM sku_catalog_map "
                      "WHERE catalog_product_id IS NOT NULL AND catalog_product_id <> ''")
    skus_de_catalogo = defaultdict(set)
    catalogo_de_sku = {}
    for r in mapa:
        s = r['sku'].strip().upper()
        skus_de_catalogo[r['catalog_product_id']].add(s)
        catalogo_de_sku[s] = r['catalog_product_id']

    print()
    print(f'publis de catalogo (activas o pausadas) ... {len(cat_de_mla)}')
    print(f'catalogos distintos publicados ............ {len(set(cat_de_mla.values()))}')
    print(f'filas en sku_catalog_map .................. {len(mapa)}')
    print(f'catalogos distintos en el mapa ............ {len(skus_de_catalogo)}')
    print()

    alcanzables, perdidas = [], []
    for mla, cpid in cat_de_mla.items():
        # ¿algun SKU mapeado a ese catalogo tiene esta publi?
        if skus_de_catalogo.get(cpid, set()) & skus_de_mla.get(mla, set()):
            alcanzables.append(mla)
        else:
            perdidas.append((mla, cpid))

    # Agrupar las perdidas por catalogo, con el SKU interno de cada publi
    por_catalogo = defaultdict(lambda: defaultdict(list))
    for mla, cpid in perdidas:
        for s in sorted(skus_de_mla.get(mla, {'?'})):
            por_catalogo[cpid][s].append(mla)

    print(f'[1] catalogos a los que el buscador NO llegaria: {len(por_catalogo)} '
          f'({len(perdidas)} publis)')
    for cpid in sorted(por_catalogo, key=lambda c: -sum(len(v) for v in por_catalogo[c].values())):
        for s, ms in sorted(por_catalogo[cpid].items()):
            en_mapa = catalogo_de_sku.get(s)
            motivo = ('el SKU no esta en el mapa' if not en_mapa
                      else f'el mapa dice {en_mapa}')
            print(f'    {cpid:<14} {s:<16} {len(ms):>2} publi(s)  — {motivo}')

    huerfanas = sorted(s for s in catalogo_de_sku
                       if not (mlas_de_sku.get(s, set()) & set(cat_de_mla)))
    print()
    print(f'[2] filas del mapa cuyo SKU no tiene hoy ninguna publi de catalogo: {len(huerfanas)}')
    for s in huerfanas:
        print(f'    {s:<16} {catalogo_de_sku[s]}')

    if sin_id:
        print()
        print(f'[3] publis de catalogo sin catalog_product_id: {len(sin_id)}')
        for mla, st in sin_id[:20]:
            print(f'    {mla:<16} {st}')

    print()
    total = len(cat_de_mla)
    pct = (len(alcanzables) / total * 100) if total else 100.0
    print(f'COBERTURA: el buscador por catalogo llega a {len(alcanzables)}/{total} '
          f'publis de catalogo ({pct:.1f}%)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
