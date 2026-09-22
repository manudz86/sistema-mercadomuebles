#!/usr/bin/env python3
"""Cruza el historial (lo que el panel MOSTRO al aplicar) contra lo que ML tiene
aplicado AHORA para esa misma publicacion y campaña.

Es la prueba directa de si ML aplica algo distinto a lo que se acepto.
Solo lectura.

Uso:  venv/bin/python3 scripts/diag_mostrado_vs_hoy.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, cargar_ml_token, ml_request, query_db, _promo_aporte_de  # noqa: E402


def main():
    with app.app_context():
        token = cargar_ml_token()
        filas = query_db("""
            SELECT id, fecha, sku, mla_id, campania_id, campania_nombre, tipo, mostrado_pct
            FROM promos_ml_historial
            WHERE accion='aplicar' AND mostrado_pct IS NOT NULL
            ORDER BY id
        """) or []
        print(f'{len(filas)} aplicaciones registradas\n')
        print(f'{"SKU":<12} {"MLA":<15} {"mostró":>8} {"ML hoy":>8} {"delta":>8}  campaña')
        print('-' * 92)
        peor, n_dif, n_ok, n_sin = None, 0, 0, 0
        deltas = []
        for f in filas:
            r = ml_request('get', f"https://api.mercadolibre.com/seller-promotions/items/{f['mla_id']}",
                           token, params={'app_version': 'v2'})
            hoy = None
            if r.status_code == 200:
                for p in (r.json() or []):
                    if p.get('type') == f['tipo'] and p.get('id') == f['campania_id'] \
                       and (p.get('status') or '').lower() in ('started', 'pending', 'active'):
                        hoy = _promo_aporte_de(p)[0]
                        break
            m = float(f['mostrado_pct'])
            if hoy is None:
                n_sin += 1
                print(f"{f['sku'] or '—':<12} {f['mla_id']:<15} {m:>7.2f}% {'—':>8} {'—':>8}  "
                      f"{(f['campania_nombre'] or '')[:28]}")
                continue
            d = hoy - m
            deltas.append(d)
            if abs(d) > 0.5:
                n_dif += 1
            else:
                n_ok += 1
            if peor is None or d > peor[0]:
                peor = (d, f['sku'], f['mla_id'], m, hoy, f['campania_nombre'])
            marca = '  <<<' if d > 5 else ''
            print(f"{f['sku'] or '—':<12} {f['mla_id']:<15} {m:>7.2f}% {hoy:>7.2f}% {d:>+7.2f}  "
                  f"{(f['campania_nombre'] or '')[:28]}{marca}")

        print(f'\nRESUMEN: {n_dif} con diferencia >0.5 pts | {n_ok} coinciden | '
              f'{n_sin} ya no estan activas')
        if deltas:
            deltas.sort()
            print(f'  delta promedio {sum(deltas)/len(deltas):+.2f} | mediana '
                  f'{deltas[len(deltas)//2]:+.2f} | maximo {deltas[-1]:+.2f} pts')
        if peor:
            print(f'\n  PEOR CASO: {peor[1]} {peor[2]} — mostró {peor[3]:.2f}% y ML aplicó '
                  f'{peor[4]:.2f}% ({peor[0]:+.2f} pts) en "{peor[5]}"')
    return 0


if __name__ == '__main__':
    sys.exit(main())
