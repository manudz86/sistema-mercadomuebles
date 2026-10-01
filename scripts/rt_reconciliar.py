#!/usr/bin/env python3
"""Reconcilia periodos de Real Trends: re-baja los ultimos N dias y los reemplaza.

Es la version manual de lo que ahora hace el job diario. Sirve para recuperar
periodos cerrados (ej. el 31/08, que nunca se bajo).

ESCRIBE sobre data/competencia_v2/<periodo>/*.json — hacer backup antes.

Uso:
    venv/bin/python3 scripts/rt_reconciliar.py 2026-08            # ultimos 7 dias
    venv/bin/python3 scripts/rt_reconciliar.py 2026-08 2026-09    # varios periodos
    venv/bin/python3 scripts/rt_reconciliar.py 2026-08 --dias 10
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE, 'config/.env'))

from competencia_v2_bp import (  # noqa: E402
    RT_CATS, DATA_DIR, _rt_reconciliar_categoria, RT_DIAS_RECONCILIAR,
)


def main():
    dias = RT_DIAS_RECONCILIAR
    if '--dias' in sys.argv:
        dias = int(sys.argv[sys.argv.index('--dias') + 1])
    periodos = [a for a in sys.argv[1:] if a[:4].isdigit() and len(a) == 7]
    if not periodos:
        print(__doc__)
        return 1

    print(f'Reconciliando {periodos} — ventana de {dias} dias\n')
    tocados = set()
    for per in periodos:
        print(f'── {per}')
        for cat, fname in RT_CATS:
            try:
                add, quit_, tot = _rt_reconciliar_categoria(cat, fname, per, dias=dias)
            except Exception as e:
                print(f'   {fname:<16} ERROR: {e}')
                continue
            if add or quit_:
                tocados.add(per)
                aviso = '  <-- RT reporta MENOS que antes (revisar)' if quit_ > add else ''
                print(f'   {fname:<16} {quit_:>4} reemplazadas por {add:<4}  '
                      f'neto {add-quit_:+4}   total {tot}{aviso}')
            else:
                print(f'   {fname:<16} sin cambios')
        print()

    for per in tocados:          # invalidar cache para que los informes reprocesen
        n = 0
        for old in os.listdir(DATA_DIR):
            if old.startswith(f'.cache_{per}_'):
                os.remove(os.path.join(DATA_DIR, old))
                n += 1
        if n:
            print(f'cache invalidada para {per} ({n} archivo/s)')
    if not tocados:
        print('No hubo cambios.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
