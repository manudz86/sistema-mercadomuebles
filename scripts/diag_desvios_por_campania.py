#!/usr/bin/env python3
"""Para cada promo que ML aplico distinto a lo mostrado: campaña y hora ARGENTINA.

Ademas cruza al reves: de las promos que hubo que quitar hoy, cuales NO tienen
registro de haber sido aplicadas desde el panel (= aparecieron por fuera).

Toma el % aplicado del CSV de remocion de hoy; si no esta ahi, lo consulta a la API.
Solo lectura.

Uso:  venv/bin/python3 scripts/diag_desvios_por_campania.py [csv]
"""
import os
import sys
import csv
import glob
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, cargar_ml_token, ml_request, query_db, _promo_aporte_de  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AR = timedelta(hours=-3)  # el VPS y MySQL corren en UTC


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else sorted(
        glob.glob(os.path.join(BASE, 'backups', 'promos_quitadas_*.csv')))[-1]
    quitadas = {}
    with open(ruta, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r.get('resultado') == 'OK':
                quitadas[(r['mla'], r['promotion_id'])] = float(r['aporte_propio'])
    print(f'CSV de remocion: {os.path.basename(ruta)}  ({len(quitadas)} quitadas)\n')

    with app.app_context():
        token = cargar_ml_token()
        filas = query_db("""
            SELECT fecha, sku, mla_id, campania_id, campania_nombre, tipo, mostrado_pct, origen
            FROM promos_ml_historial
            WHERE accion='aplicar' AND mostrado_pct IS NOT NULL
            ORDER BY fecha, id
        """) or []

        desvios, aplicadas_panel = [], set()
        for f in filas:
            aplicadas_panel.add((f['mla_id'], f['campania_id']))
            m = float(f['mostrado_pct'])
            ap = quitadas.get((f['mla_id'], f['campania_id']))
            if ap is None:
                r = ml_request('get', f"https://api.mercadolibre.com/seller-promotions/items/{f['mla_id']}",
                               token, params={'app_version': 'v2'})
                if r.status_code == 200:
                    for p in (r.json() or []):
                        if p.get('type') == f['tipo'] and p.get('id') == f['campania_id'] \
                           and (p.get('status') or '').lower() in ('started', 'pending', 'active'):
                            ap = _promo_aporte_de(p)[0]
                            break
            if ap is None or abs(ap - m) <= 0.5:
                continue
            desvios.append({'fecha_ar': f['fecha'] + AR, 'sku': f['sku'], 'mla': f['mla_id'],
                            'camp': f['campania_nombre'] or f['campania_id'],
                            'mostrado': m, 'aplicado': ap, 'delta': ap - m, 'origen': f['origen']})

        print(f'=== {len(desvios)} PROMOS CON DESVIO — campaña y hora ARGENTINA ===\n')
        por_camp = {}
        for d in sorted(desvios, key=lambda x: -x['delta']):
            por_camp.setdefault(d['camp'], []).append(d)
        for camp, items in sorted(por_camp.items(), key=lambda kv: -len(kv[1])):
            print(f'--- {camp}  ({len(items)} desvio(s)) ---')
            print(f'  {"hora AR":<17} {"SKU":<12} {"MLA":<15} {"mostró":>8} {"aplicó":>8} {"delta":>8} origen')
            for d in items:
                print(f"  {d['fecha_ar'].strftime('%d/%m %H:%M:%S'):<17} {d['sku'] or '—':<12} "
                      f"{d['mla']:<15} {d['mostrado']:>7.2f}% {d['aplicado']:>7.2f}% "
                      f"{d['delta']:>+7.2f}  {d['origen']}")
            print()

        print('=== CRUCE INVERSO: quitadas hoy que NO pasaron por el panel ===')
        huerfanas = [k for k in quitadas if k not in aplicadas_panel]
        if not huerfanas:
            print('  Ninguna: las 15 quitadas hoy figuran aplicadas desde el panel.')
        else:
            print(f'  {len(huerfanas)} sin registro de aplicacion desde el panel:')
            for mla, cid in huerfanas:
                print(f'    {mla}  campaña {cid}  (aporte {quitadas[(mla, cid)]}%)')
            print('  OJO: el historial arranca el 21/09 ~21:00 AR. Promos aplicadas antes')
            print('  de esa hora no tienen registro y apareceran aca sin que sea anomalo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
