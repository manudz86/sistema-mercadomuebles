#!/usr/bin/env python3
"""Diagnostico: ¿ML devuelve varias ofertas distintas para la MISMA publicacion?

El panel /promociones-ml deduplica por MLA y se queda con la PRIMERA fila.
Si ML devuelve varias ofertas con seller_percentage distinto, lo que ves NO es
necesariamente lo que se aplica.

Ademas compara la oferta que muestra el panel (endpoint de campaña) contra la
que elegiria _participar_campania_una (endpoint por item).

Solo lectura.

Uso:  venv/bin/python3 scripts/diag_promos_duplicadas.py [status]
      status: candidate (default) | started
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, cargar_ml_token, ml_request, _promo_campanias  # noqa: E402


def paginar(token, cid, ctype, status):
    out, sa = [], None
    for _ in range(200):
        params = {'promotion_type': ctype, 'app_version': 'v2', 'limit': 50, 'status': status}
        if sa:
            params['search_after'] = sa
        r = ml_request('get', f'https://api.mercadolibre.com/seller-promotions/promotions/{cid}/items',
                       token, params=params)
        if r.status_code != 200:
            break
        d = r.json() or {}
        res = d.get('results') or []
        out.extend(res)
        sa = (d.get('paging') or {}).get('searchAfter')
        if not res or not sa:
            break
    return out


def main():
    status = sys.argv[1] if len(sys.argv) > 1 else 'candidate'
    with app.app_context():
        token = cargar_ml_token()
        campanias = [c for c in _promo_campanias(token)
                     if c.get('type') in ('SMART', 'PRICE_MATCHING')]
        for c in campanias:
            cid, ctype, nombre = c.get('id'), c.get('type'), c.get('name') or c.get('id')
            items = paginar(token, cid, ctype, status)
            por_mla = defaultdict(list)
            for it in items:
                if it.get('id'):
                    por_mla[it['id']].append(it)

            repetidos = {k: v for k, v in por_mla.items() if len(v) > 1}
            distintos = {}
            for mla, filas in repetidos.items():
                pcts = {f.get('seller_percentage') for f in filas}
                if len(pcts) > 1:
                    distintos[mla] = filas

            print(f'\n=== {nombre} ({ctype}, status={status}) ===')
            print(f'  filas devueltas por ML : {len(items)}')
            print(f'  MLAs unicos            : {len(por_mla)}')
            print(f'  MLAs repetidos         : {len(repetidos)}')
            print(f'  repetidos CON seller_percentage DISTINTO : {len(distintos)}')

            for mla, filas in list(distintos.items())[:4]:
                print(f'\n  --- {mla}: ML devuelve {len(filas)} ofertas distintas ---')
                for i, f in enumerate(filas):
                    marca = '  <-- la que MUESTRA el panel (primera)' if i == 0 else ''
                    print(f"    [{i}] seller={f.get('seller_percentage')}%  "
                          f"meli={f.get('meli_percentage')}%  "
                          f"{f.get('original_price')} -> {f.get('price')}  "
                          f"offer={f.get('offer_id') or f.get('ref_id')}{marca}")
                # que elegiria _participar_campania_una (endpoint por item)
                r = ml_request('get', f'https://api.mercadolibre.com/seller-promotions/items/{mla}',
                               token, params={'app_version': 'v2'})
                if r.status_code == 200:
                    for p in (r.json() or []):
                        if p.get('type') == ctype and p.get('id') == cid and p.get('ref_id'):
                            print(f"    => _participar_campania_una tomaria: "
                                  f"seller={p.get('seller_percentage')}%  "
                                  f"meli={p.get('meli_percentage')}%  ref={p.get('ref_id')}")
                            break
    return 0


if __name__ == '__main__':
    sys.exit(main())
