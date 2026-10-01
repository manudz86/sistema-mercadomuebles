#!/usr/bin/env python3
"""Busca filas duplicadas en los JSON acumulados de Real Trends.

Importa porque la reconciliacion reemplaza rangos de dias: si el reemplazo
fallara, quedarian filas repetidas y la facturacion saldria inflada.

Solo lectura.

Uso:  venv/bin/python3 scripts/rt_chequear_duplicados.py 2026-09 [2026-08 ...]
"""
import os
import sys
import json
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from competencia_v2_bp import RT_CATS, DATA_DIR, _dia_sort  # noqa: E402


def clave(r):
    return (str(r.get('item_id') or r.get('id') or ''), _dia_sort(r.get('day')),
            str(r.get('price') or ''), str(r.get('installments') or ''),
            str(r.get('sold_quantity') or ''))


def main():
    periodos = [a for a in sys.argv[1:] if len(a) == 7 and a[:4].isdigit()]
    if not periodos:
        print(__doc__)
        return 1
    problemas = 0
    for per in periodos:
        print(f'── {per}')
        for _cat, fname in RT_CATS:
            path = os.path.join(DATA_DIR, per, fname)
            if not os.path.exists(path):
                print(f'   {fname:<16} (no existe)')
                continue
            rows = json.load(open(path, encoding='utf-8'))
            c = Counter(clave(r) for r in rows)
            dups = {k: n for k, n in c.items() if n > 1}
            por_dia = defaultdict(int)
            for k, n in dups.items():
                por_dia[k[1]] += n - 1
            extra = sum(n - 1 for n in dups.values())
            estado = 'OK' if not dups else f'*** {extra} filas repetidas ***'
            print(f'   {fname:<16} {len(rows):>5} filas, {len(c):>5} unicas   {estado}')
            if dups:
                problemas += extra
                for d in sorted(por_dia)[:6]:
                    print(f'        {d}: +{por_dia[d]}')
        print()
    print('Sin duplicados.' if not problemas else f'TOTAL repetidas: {problemas}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
