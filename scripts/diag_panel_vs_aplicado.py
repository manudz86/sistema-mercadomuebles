#!/usr/bin/env python3
"""¿Lo que MUESTRA el panel es lo que ML APLICA?

El panel arma la grilla con el endpoint de campaña:
    GET /seller-promotions/promotions/{cid}/items
pero al participar, _participar_campania_una resuelve la oferta con el endpoint
por item:
    GET /seller-promotions/items/{mla}
Si esos dos endpoints devuelven seller_percentage distinto para la misma
publicacion y la misma campaña, entonces lo que aceptas NO es lo que se aplica.

Solo lectura: no participa ni borra nada.

Uso:  venv/bin/python3 scripts/diag_panel_vs_aplicado.py [max_items_por_campania]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, cargar_ml_token, ml_request, _promo_campanias, query_db  # noqa: E402


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
    tope = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    with app.app_context():
        token = cargar_ml_token()
        mapa = {r['mla_id'] for r in
                (query_db("SELECT mla_id FROM sku_mla_mapeo WHERE activo = TRUE") or [])}
        campanias = [c for c in _promo_campanias(token)
                     if c.get('type') in ('SMART', 'PRICE_MATCHING')]

        total_comp = total_dif = 0
        for c in campanias:
            cid, ctype, nombre = c.get('id'), c.get('type'), c.get('name') or c.get('id')
            cands = [it for it in paginar(token, cid, ctype, 'candidate')
                     if it.get('id') in mapa][:tope]
            if not cands:
                continue
            print(f'\n=== {nombre} ({ctype}) — comparando {len(cands)} publicaciones ===')
            print(f'  {"MLA":<15} {"panel":>8} {"al aplicar":>11}   veredicto')
            print('  ' + '-' * 58)
            difs = 0
            for it in cands:
                mla = it['id']
                panel_pct = it.get('seller_percentage')
                r = ml_request('get', f'https://api.mercadolibre.com/seller-promotions/items/{mla}',
                               token, params={'app_version': 'v2'})
                item_pct = None
                if r.status_code == 200:
                    # misma logica que _participar_campania_una: primer match por
                    # tipo+promotion_id con ref_id, SIN filtrar por status
                    for p in (r.json() or []):
                        if p.get('type') == ctype and p.get('id') == cid and p.get('ref_id'):
                            item_pct = p.get('seller_percentage')
                            break
                total_comp += 1
                igual = (panel_pct == item_pct)
                if not igual:
                    difs += 1
                    total_dif += 1
                pp = f'{panel_pct}%' if panel_pct is not None else '—'
                ip = f'{item_pct}%' if item_pct is not None else '—'
                print(f'  {mla:<15} {pp:>8} {ip:>11}   {"OK" if igual else "*** DISTINTO ***"}')
            print(f'  -> {difs}/{len(cands)} con diferencia')

        print(f'\n===== RESUMEN: {total_dif}/{total_comp} publicaciones donde el panel '
              f'muestra un % distinto al que se aplicaria =====')
    return 0


if __name__ == '__main__':
    sys.exit(main())
