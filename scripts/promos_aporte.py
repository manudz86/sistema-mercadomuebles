#!/usr/bin/env python3
"""Lista las promos ML ya aplicadas (activas/pendientes) donde TU aporte supera un umbral.

Solo lectura: GET a la API de Mercado Libre, sin escribir nada.

"Tu aporte" se calcula igual que el panel /promociones-ml:
  - promo co-financiada (SMART/PRICE_MATCHING) -> seller_percentage
  - promo no co-financiada (DEAL, etc.)        -> el descuento lo bancas entero

Uso:
    venv/bin/python3 scripts/promos_aporte.py            # umbral 5%
    venv/bin/python3 scripts/promos_aporte.py 10         # umbral 10%
    venv/bin/python3 scripts/promos_aporte.py 5 --todas  # incluye las no mapeadas a SKU
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import (app, cargar_ml_token, ml_request, query_db,  # noqa: E402
                 _promo_campanias, _promo_fecha_ar)

LIMITE_PAGINAS = 200  # tope de seguridad: 200 x 50 = 10.000 items por estado


def items_de_campania(token, cid, ctype, status):
    """Todos los items de una campaña en un estado, paginando por cursor."""
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
    """(pct_aporte, es_cofinanciada). None si no se puede determinar."""
    seller_p = it.get('seller_percentage')
    meli_p = it.get('meli_percentage')
    if seller_p is not None and meli_p is not None:
        return float(seller_p), True
    orig = it.get('original_price')
    fin = it.get('price')
    if orig and fin is not None and orig > 0:
        return round((orig - fin) / orig * 100, 1), False
    if seller_p is not None:
        return float(seller_p), False
    return None, False


def main():
    umbral = 5.0
    todas = '--todas' in sys.argv
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
        rows = query_db("SELECT mla_id, sku, titulo_ml FROM sku_mla_mapeo WHERE activo = TRUE") or []
        mapa = {r['mla_id']: r['sku'] for r in rows}
        titulos = {r['mla_id']: r['titulo_ml'] for r in rows}

        encontrados, total_aplicadas = [], 0
        for c in campanias:
            cid, ctype = c.get('id'), c.get('type')
            if not cid or not ctype:
                continue
            vistos = set()
            for st in ('started', 'pending'):
                for it in items_de_campania(token, cid, ctype, st):
                    mla = it.get('id')
                    if not mla or mla in vistos:
                        continue
                    vistos.add(mla)
                    if not todas and mla not in mapa:
                        continue
                    total_aplicadas += 1
                    pct, cofin = aporte_de(it)
                    if pct is not None and pct > umbral:
                        encontrados.append({
                            'mla': mla, 'sku': mapa.get(mla, '—'),
                            'titulo': (titulos.get(mla) or it.get('title') or '')[:48],
                            'campania': c.get('name') or cid, 'tipo': ctype,
                            'estado': (it.get('status') or '').lower(),
                            'pct': pct, 'cofin': cofin,
                            'orig': it.get('original_price'), 'precio': it.get('price'),
                            'f_fin': _promo_fecha_ar(it.get('end_date')),
                        })

        print(f'Promos aplicadas revisadas: {total_aplicadas}'
              f'{"" if todas else " (solo mapeadas a SKU)"}')
        print(f'Umbral: aporte propio > {umbral}%\n')
        if not encontrados:
            print(f'✅ Ninguna promo activa/pendiente con aporte propio mayor al {umbral}%.')
            return 0

        encontrados.sort(key=lambda x: -x['pct'])
        print(f'⚠️  {len(encontrados)} promo(s) con aporte mayor al {umbral}%:\n')
        print(f'{"aporte":>7}  {"SKU":<10} {"MLA":<15} {"estado":<8} {"campaña":<28} precio')
        print('-' * 104)
        for e in encontrados:
            pr = f"{e['orig']:,.0f} -> {e['precio']:,.0f}" if e['orig'] and e['precio'] else '—'
            marca = '' if e['cofin'] else '  (no co-fin: lo bancás entero)'
            print(f"{e['pct']:>6.1f}%  {e['sku']:<10} {e['mla']:<15} {e['estado']:<8} "
                  f"{e['campania'][:28]:<28} {pr}{marca}")
            print(f"{'':>9}{e['titulo']}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
