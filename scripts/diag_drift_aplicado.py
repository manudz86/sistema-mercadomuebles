#!/usr/bin/env python3
"""Compara lo que ML tenia APLICADO (promos que acabamos de quitar) contra lo
que ML OFRECE HOY para la misma publicacion y la misma campaña.

Si el % aplicado era mucho mayor que el que ML ofrece ahora, quiere decir que la
oferta vieja se habia "desfasado": no es que se haya aceptado ese numero, es que
el numero se movio despues de aceptarlo.

Lee backups/promos_quitadas_*.csv (el mas reciente). Solo lectura.

Uso:  venv/bin/python3 scripts/diag_drift_aplicado.py [archivo.csv]
"""
import os
import sys
import csv
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, cargar_ml_token, ml_request  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        cands = sorted(glob.glob(os.path.join(BASE, 'backups', 'promos_quitadas_*.csv')))
        if not cands:
            print('No hay CSV de promos quitadas')
            return 1
        ruta = cands[-1]
    print(f'Archivo: {os.path.basename(ruta)}\n')

    with open(ruta, encoding='utf-8') as fh:
        filas = [r for r in csv.DictReader(fh) if r.get('resultado') == 'OK']

    with app.app_context():
        token = cargar_ml_token()
        print(f'{"SKU":<10} {"MLA":<15} {"aplicado":>9} {"ofrece hoy":>11} {"delta":>8}  campaña')
        print('-' * 96)
        subio = bajo = igual = sin = 0
        deltas = []
        for f in filas:
            mla, cid, ctype = f['mla'], f['promotion_id'], f['tipo']
            aplicado = float(f['aporte_propio'])
            hoy = None
            r = ml_request('get', f'https://api.mercadolibre.com/seller-promotions/items/{mla}',
                           token, params={'app_version': 'v2'})
            if r.status_code == 200:
                for p in (r.json() or []):
                    if p.get('type') == ctype and p.get('id') == cid:
                        hoy = p.get('seller_percentage')
                        break
            if hoy is None:
                sin += 1
                hoy_s, delta_s = '—', '—'
            else:
                hoy = float(hoy)
                d = aplicado - hoy
                deltas.append(d)
                hoy_s, delta_s = f'{hoy:.2f}%', f'{d:+.2f}'
                if d > 0.5:
                    subio += 1
                elif d < -0.5:
                    bajo += 1
                else:
                    igual += 1
            print(f"{f['sku']:<10} {mla:<15} {aplicado:>8.1f}% {hoy_s:>11} {delta_s:>8}  "
                  f"{f['campania'][:26]}")

        print(f'\nRESUMEN de {len(filas)} promos quitadas:')
        print(f'  lo aplicado era MAYOR de lo que ML ofrece hoy : {subio}')
        print(f'  practicamente igual (+-0.5)                   : {igual}')
        print(f'  lo aplicado era MENOR                         : {bajo}')
        print(f'  ML ya no ofrece esa campaña para esa publi     : {sin}')
        if deltas:
            deltas.sort()
            print(f'  delta promedio: {sum(deltas)/len(deltas):+.2f} pts'
                  f'  |  mediana: {deltas[len(deltas)//2]:+.2f} pts'
                  f'  |  max: {deltas[-1]:+.2f} pts')
    return 0


if __name__ == '__main__':
    sys.exit(main())
