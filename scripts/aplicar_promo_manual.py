#!/usr/bin/env python3
"""Aplica UNA promo de ML a mano, salteando el tope de aporte propio.

El tope (configuracion.promo_max_aporte_pct) existe para que no se apliquen solas
promos caras. Este script es la via explicita para aplicar una igual, con decision
tomada. Queda registrado en promos_ml_historial con origen 'manual'.

ESCRIBE en Mercado Libre (POST real sobre una publicacion).

Uso:
    venv/bin/python3 scripts/aplicar_promo_manual.py MLA123 SMART P-MLA456
    venv/bin/python3 scripts/aplicar_promo_manual.py MLA123 SMART P-MLA456 --dry-run
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import (app, cargar_ml_token, ml_request, query_one,  # noqa: E402
                 _participar_campania_una, _participar_deal_una,
                 _promo_leer_aplicada, _promo_aporte_de, _promo_hist_registrar)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) < 3:
        print(__doc__)
        return 1
    mla, tipo, pid = args[0], args[1].upper(), args[2]
    dry = '--dry-run' in sys.argv

    with app.app_context():
        tok = cargar_ml_token()
        if not tok:
            print('No hay token de ML')
            return 1

        # estado previo
        r = ml_request('get', f'https://api.mercadolibre.com/seller-promotions/items/{mla}',
                       tok, params={'app_version': 'v2'})
        cand = None
        for p in (r.json() or []) if r.status_code == 200 else []:
            if p.get('type') == tipo and p.get('id') == pid:
                cand = p
                break
        if not cand:
            print(f'No encontre la promo {pid} ({tipo}) para {mla}')
            return 1

        ap, meli = _promo_aporte_de(cand)
        print(f'PROMO A APLICAR')
        print(f'  publicacion : {mla}')
        print(f'  campania    : {pid}  {cand.get("name")}')
        print(f'  estado      : {cand.get("status")}')
        print(f'  precio      : {cand.get("original_price")} -> {cand.get("price")}')
        print(f'  tu aporte   : {ap}%   ML: {meli}%')

        row = query_one("SELECT valor FROM configuracion WHERE clave='promo_max_aporte_pct'")
        tope = float(row['valor']) if row and row['valor'] else 5.0
        print(f'  tope vigente: {tope}%  -> {"SUPERA el tope" if ap and ap > tope else "dentro del tope"}')

        if dry:
            print('\n--dry-run: no se aplico nada.')
            return 0

        print('\naplicando ...')
        if tipo == 'DEAL':
            res = _participar_deal_una(tok, mla, pid)
        else:
            res = _participar_campania_una(tok, mla, tipo, pid)
        print(f'  resultado: {res}')

        sku = None
        try:
            q = query_one("SELECT sku FROM sku_mla_mapeo WHERE mla_id=%s AND activo=TRUE", (mla,))
            sku = q['sku'] if q else None
        except Exception:
            pass

        aplicada = _promo_leer_aplicada(tok, mla, tipo, pid)
        ap2, meli2 = _promo_aporte_de(aplicada) if aplicada else (None, None)
        if aplicada:
            print(f'  verificado en ML: aporte {ap2}%  ML {meli2}%  '
                  f'{aplicada.get("original_price")} -> {aplicada.get("price")}  '
                  f'estado {aplicada.get("status")}')
        else:
            print('  (ML todavia no la reporta como activa; puede tardar unos segundos)')

        _promo_hist_registrar(
            accion='aplicar', origen='manual', mla_id=mla, sku=sku, tipo=tipo,
            campania_id=pid, campania_nombre=cand.get('name'),
            mostrado_pct=ap, aplicado_pct=ap2, aplicado_meli_pct=meli2,
            aplicado_precio=(aplicada or {}).get('price'),
            aplicado_original=(aplicada or {}).get('original_price'),
            supero_limite=bool(ap2 and ap2 > tope), revertida=False,
            ok=bool(res.get('ok')),
            error=res.get('error') or 'aplicada a mano salteando el tope (decision comercial)')
        print('  registrado en promos_ml_historial (origen=manual)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
