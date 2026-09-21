#!/usr/bin/env python3
"""Saca de las promos ML las publicaciones donde TU aporte supera un umbral.

Por defecto hace DRY-RUN: lista lo que haria y NO toca nada.
Para ejecutar de verdad hay que pasar --ejecutar (hace DELETE contra la API de ML).

Uso:
    venv/bin/python3 scripts/quitar_promos_aporte.py 5              # dry-run
    venv/bin/python3 scripts/quitar_promos_aporte.py 5 --ejecutar   # borra de verdad
    venv/bin/python3 scripts/quitar_promos_aporte.py 5 --ejecutar --solo-poco-aporte-ml

--solo-poco-aporte-ml: saca unicamente las promos donde ademas ML aporta poco
  (meli_percentage < aporte propio), o sea donde el descuento lo bancas casi solo.

Siempre deja constancia en backups/promos_quitadas_<timestamp>.csv para poder
revertir a mano si hiciera falta (los logs del bot de precios estan rotos).
"""
import os
import sys
import csv
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import (app, cargar_ml_token, ml_request, query_db,  # noqa: E402
                 _promo_campanias, _quitar_promo_una)

LIMITE_PAGINAS = 200
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def items_de_campania(token, cid, ctype, status):
    out, search_after = [], None
    for _ in range(LIMITE_PAGINAS):
        params = {'promotion_type': ctype, 'app_version': 'v2',
                  'status': status, 'limit': 50}
        if search_after:
            params['search_after'] = search_after
        r = ml_request('get', f'https://api.mercadolibre.com/seller-promotions/promotions/{cid}/items',
                       token, params=params)
        if r.status_code != 200:
            break
        d = r.json() or {}
        res = d.get('results') or []
        out.extend(res)
        search_after = (d.get('paging') or {}).get('searchAfter')
        if not res or not search_after:
            break
    return out


def aporte_de(it):
    seller_p = it.get('seller_percentage')
    meli_p = it.get('meli_percentage')
    if seller_p is not None and meli_p is not None:
        return float(seller_p), float(meli_p)
    orig, fin = it.get('original_price'), it.get('price')
    if orig and fin is not None and orig > 0:
        return round((orig - fin) / orig * 100, 1), 0.0
    return (float(seller_p), 0.0) if seller_p is not None else (None, 0.0)


def main():
    umbral = 5.0
    ejecutar = '--ejecutar' in sys.argv
    solo_poco_ml = '--solo-poco-aporte-ml' in sys.argv
    for a in sys.argv[1:]:
        if not a.startswith('--'):
            try:
                umbral = float(a.replace(',', '.'))
            except ValueError:
                pass

    with app.app_context():
        token = cargar_ml_token()
        if not token:
            print('No hay token de ML configurado')
            return 1
        campanias = _promo_campanias(token)
        mapa = {r['mla_id']: r['sku'] for r in
                (query_db("SELECT mla_id, sku FROM sku_mla_mapeo WHERE activo = TRUE") or [])}

        objetivo = []
        for c in campanias:
            cid, ctype = c.get('id'), c.get('type')
            if not cid or not ctype:
                continue
            vistos = set()
            for st in ('started', 'pending'):
                for it in items_de_campania(token, cid, ctype, st):
                    mla = it.get('id')
                    if not mla or mla in vistos or mla not in mapa:
                        continue
                    vistos.add(mla)
                    pct, meli = aporte_de(it)
                    if pct is None or pct <= umbral:
                        continue
                    if solo_poco_ml and meli >= pct:
                        continue
                    objetivo.append({
                        'mla': mla, 'sku': mapa.get(mla, ''),
                        'campania': c.get('name') or cid,
                        'promotion_id': cid, 'tipo': ctype,
                        'offer_id': it.get('offer_id') or '',
                        'aporte_propio': pct, 'aporte_ml': meli,
                        'original_price': it.get('original_price'),
                        'price': it.get('price'),
                        'estado': (it.get('status') or '').lower(),
                    })

        objetivo.sort(key=lambda x: -x['aporte_propio'])
        modo = 'EJECUTAR' if ejecutar else 'DRY-RUN (no toca nada)'
        print(f'Modo: {modo}   |   umbral aporte propio > {umbral}%'
              f'{"   |   solo donde ML aporta menos que vos" if solo_poco_ml else ""}')
        print(f'Publicaciones a sacar: {len(objetivo)}\n')
        print(f'{"aporte":>7} {"ML":>6}  {"SKU":<10} {"MLA":<15} campaña')
        print('-' * 88)
        for o in objetivo:
            print(f"{o['aporte_propio']:>6.1f}% {o['aporte_ml']:>5.1f}%  {o['sku']:<10} "
                  f"{o['mla']:<15} {o['campania'][:34]}")

        if not ejecutar:
            print('\nDRY-RUN: no se borro nada. Para ejecutar, agregar --ejecutar')
            return 0
        if not objetivo:
            print('\nNada para hacer.')
            return 0

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = os.path.join(BASE, 'backups', f'promos_quitadas_{ts}.csv')
        with open(csv_path, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(objetivo[0].keys()) + ['resultado'])
            w.writeheader()
            print(f'\nConstancia en: {csv_path}\n')
            ok = err = 0
            for o in objetivo:
                res = _quitar_promo_una(token, o['mla'], o['tipo'],
                                        o['promotion_id'], o['offer_id'])
                fila = dict(o)
                fila['resultado'] = 'OK' if res.get('ok') else f"ERROR: {res.get('error')}"
                w.writerow(fila)
                fh.flush()
                if res.get('ok'):
                    ok += 1
                    print(f"  OK     {o['sku']:<10} {o['mla']}  ({o['aporte_propio']}%)")
                else:
                    err += 1
                    print(f"  ERROR  {o['sku']:<10} {o['mla']}  {res.get('error')}")
        print(f'\nListo: {ok} quitadas, {err} con error.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
