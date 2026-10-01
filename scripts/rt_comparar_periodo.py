#!/usr/bin/env python3
"""Re-descarga un rango de Real Trends y lo compara contra el acumulado local.

Por que hace falta: job_actualizar_rt es INCREMENTAL — baja solo los dias nuevos
y los agrega, nunca reescribe dias viejos. Si una venta se cancela despues de que
la bajamos, RT deja de reportarla pero nuestro archivo la sigue contando.

SOLO LECTURA: no toca los archivos de data/. Imprime el diff.

Uso:
    venv/bin/python3 scripts/rt_comparar_periodo.py 2026-09-01 2026-09-29
    venv/bin/python3 scripts/rt_comparar_periodo.py 2026-09-01 2026-09-29 --detalle
"""
import os
import sys
import json
import re
from collections import defaultdict
from datetime import date as _date, timedelta as _timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE, 'config/.env'))

from competencia_v2_bp import (  # noqa: E402
    RT_CATS, DATA_DIR, _rt_fetch, _rt_norm, _dia_sort,
)


def clave(r):
    """Identidad de una fila: publicacion + dia + precio + cuotas.
    item_id + day no alcanza: una misma publi puede tener varias filas por dia."""
    return (
        str(r.get('item_id') or r.get('id') or ''),
        _dia_sort(r.get('day')),
        str(r.get('price') or ''),
        str(r.get('installments') or ''),
    )


def unidades(r):
    try:
        return int(round(float(r.get('sold_quantity') or 0)))
    except (TypeError, ValueError):
        return 0


def facturacion(r):
    try:
        return float(r.get('price') or 0) * unidades(r)
    except (TypeError, ValueError):
        return 0.0


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    d0, d1 = sys.argv[1], sys.argv[2]
    detalle = '--detalle' in sys.argv
    periodo = d0[:7]

    print(f'COMPARACION REAL TRENDS  {d0} .. {d1}')
    print(f'periodo local: {periodo}\n')

    tot = defaultdict(lambda: [0, 0, 0.0, 0.0])  # cat -> [n_local, n_rt, fact_local, fact_rt]
    faltan_en_rt, faltan_en_local = [], []

    for cat_id, fname in RT_CATS:
        path = os.path.join(DATA_DIR, periodo, fname)
        locales = []
        if os.path.exists(path):
            try:
                locales = json.load(open(path, encoding='utf-8'))
            except Exception as e:
                print(f'  {fname}: no se pudo leer ({e})')
        # acotar el local al rango pedido
        locales = [r for r in locales if d0 <= _dia_sort(r.get('day')) <= d1]

        print(f'── {fname}  (category_id {cat_id})')
        print(f'   bajando de Real Trends ...', flush=True)
        try:
            crudo, truncado = _rt_fetch(cat_id, d0, d1)
            rt = [_rt_norm(x) for x in crudo]
            if truncado:
                # RT corta en ~1000 filas: hay que rehacerlo dia por dia, igual que
                # _rt_descargar_categoria. Sin esto el diff es basura (parece que
                # "faltan" todos los dias posteriores al corte).
                print('   respuesta TRUNCADA -> rehaciendo dia por dia ...', flush=True)
                rt = []
                dia = _date.fromisoformat(d0)
                fin = _date.fromisoformat(d1)
                while dia <= fin:
                    rws, tr_d = _rt_fetch(cat_id, dia.isoformat(), dia.isoformat())
                    if tr_d:
                        print(f'      OJO: {dia} tambien vino truncado')
                    rt.extend(_rt_norm(x) for x in rws)
                    dia += _timedelta(days=1)
                print(f'   {len(rt)} filas tras el dia por dia')
        except Exception as e:
            print(f'   ERROR al bajar: {e}\n')
            continue

        k_loc = defaultdict(list)
        for r in locales:
            k_loc[clave(r)].append(r)
        k_rt = defaultdict(list)
        for r in rt:
            k_rt[clave(r)].append(r)

        u_loc = sum(unidades(r) for r in locales)
        u_rt = sum(unidades(r) for r in rt)
        f_loc = sum(facturacion(r) for r in locales)
        f_rt = sum(facturacion(r) for r in rt)
        tot[fname] = [len(locales), len(rt), f_loc, f_rt]

        print(f'   filas    local {len(locales):>6}   RT {len(rt):>6}   dif {len(rt)-len(locales):+}')
        print(f'   unidades local {u_loc:>6}   RT {u_rt:>6}   dif {u_rt-u_loc:+}')
        print(f'   facturac local ${f_loc:>14,.0f}   RT ${f_rt:>14,.0f}   dif ${f_rt-f_loc:+,.0f}')

        solo_loc = [k for k in k_loc if k not in k_rt]
        solo_rt = [k for k in k_rt if k not in k_loc]
        print(f'   filas que TENEMOS y RT ya NO reporta : {len(solo_loc)}'
              f'   (unidades {sum(unidades(r) for k in solo_loc for r in k_loc[k])})')
        print(f'   filas que RT reporta y NO tenemos    : {len(solo_rt)}'
              f'   (unidades {sum(unidades(r) for k in solo_rt for r in k_rt[k])})')

        for k in solo_loc:
            for r in k_loc[k]:
                faltan_en_rt.append((fname, r))
        for k in solo_rt:
            for r in k_rt[k]:
                faltan_en_local.append((fname, r))

        # diferencia por dia
        pd_loc, pd_rt = defaultdict(int), defaultdict(int)
        for r in locales:
            pd_loc[_dia_sort(r.get('day'))] += unidades(r)
        for r in rt:
            pd_rt[_dia_sort(r.get('day'))] += unidades(r)
        difs = [(d, pd_loc.get(d, 0), pd_rt.get(d, 0)) for d in sorted(set(pd_loc) | set(pd_rt))
                if pd_loc.get(d, 0) != pd_rt.get(d, 0)]
        if difs:
            print(f'   dias con diferencia de unidades ({len(difs)}):')
            for d, a, b in difs[:12]:
                print(f'      {d}  local {a:>5}  RT {b:>5}   {b-a:+}')
            if len(difs) > 12:
                print(f'      ... y {len(difs)-12} dia(s) mas')
        else:
            print('   sin diferencias por dia')
        print()

    print('=' * 70)
    print('RESUMEN')
    print('=' * 70)
    tl = sum(v[0] for v in tot.values()); tr = sum(v[1] for v in tot.values())
    fl = sum(v[2] for v in tot.values()); fr = sum(v[3] for v in tot.values())
    print(f'  filas       local {tl:>7}   RT {tr:>7}   dif {tr-tl:+}')
    print(f'  facturacion local ${fl:>15,.0f}   RT ${fr:>15,.0f}   dif ${fr-fl:+,.0f}')
    print(f'  filas que tenemos de mas (posibles cancelaciones): {len(faltan_en_rt)}')
    print(f'  filas que nos faltan                             : {len(faltan_en_local)}')

    def _listar(titulo, filas, tope=30):
        if not filas:
            return
        print(f'\n{titulo}')
        filas.sort(key=lambda x: -facturacion(x[1]))
        for fn, r in filas[:tope]:
            print(f'  {fn:<16} {_dia_sort(r.get("day"))}  {str(r.get("seller_nickname") or "")[:18]:<18} '
                  f'{str(r.get("title") or "")[:44]:<44} u={unidades(r):<3} ${facturacion(r):>12,.0f}')
        if len(filas) > tope:
            print(f'  ... y {len(filas)-tope} mas')

    _listar('DETALLE — las TENEMOS y RT ya no las reporta (posibles cancelaciones):',
            faltan_en_rt)
    _listar('DETALLE — RT las reporta y NO las tenemos (ventas que se nos escaparon):',
            faltan_en_local)
    return 0


if __name__ == '__main__':
    sys.exit(main())
