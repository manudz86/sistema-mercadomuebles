#!/usr/bin/env python3
"""Cotiza Mercado Envios a varios codigos postales. Solo lectura.

Dos modos:

  Por PUBLICACION de ML (tarifa de marketplace, con envio gratis si aplica):
    venv/bin/python3 scripts/ml_envio.py MLA3068728462 2 1407 1832

  Por DIMENSIONES, que es lo que sirve para cotizar desde la tienda propia:
    venv/bin/python3 scripts/ml_envio.py --dim 30x40x70,4000 --precio 208000
    venv/bin/python3 scripts/ml_envio.py --dim 30x40x70,4000 1407 5000

  dimensiones = anchoxaltoxlargo en cm, peso en gramos

Columnas:
  base      costo de lista del envio
  comprador lo que paga el comprador (0 = envio gratis)
  vendedor  lo que te descuentan a vos
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import ml_token  # noqa: E402
from ml import _get  # noqa: E402

_TOKEN = None


def api_get(path):
    global _TOKEN
    if _TOKEN is None:
        _TOKEN = ml_token()
    r = _get(path, _TOKEN)
    return r.json() if r.status_code == 200 else {'_http': r.status_code,
                                                  '_body': r.text[:200]}

CPS = ['1407', '1606', '1832', '1900', '2000', '5000', '3400', '8300', '4400', '9410']


SELLER = 29563319


def _arg(nombre, defecto=None):
    return sys.argv[sys.argv.index(nombre) + 1] if nombre in sys.argv else defecto


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    dim = _arg('--dim')
    if dim:
        precio = _arg('--precio', '100000')
        cps = [a for a in sys.argv[1:] if a.isdigit() and len(a) == 4] or CPS
        ruta = (f'/users/{SELLER}/shipping_options?dimensions={dim}'
                f'&item_price={precio}&zip_code=')
        titulo = f'dimensiones {dim} · precio ${precio}'
    else:
        mla = sys.argv[1]
        qty = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 1
        cps = [a for a in sys.argv[3:] if a.isdigit()] or CPS
        ruta = f'/items/{mla}/shipping_options?quantity={qty}&zip_code='
        titulo = f'{mla} · cantidad {qty}'

    print(f'{titulo}\n')
    print(f'{"CP":<7}{"provincia":<18}{"base":>10}{"comprador":>12}'
          f'{"vendedor":>11}  metodo')
    print('-' * 78)
    for cp in cps:
        try:
            d = api_get(ruta + cp)
        except Exception as e:
            print(f'{cp:<7}EXC {type(e).__name__}: {e}')
            continue
        if not isinstance(d, dict) or 'options' not in d:
            print(f'{cp:<7}sin opciones: {str(d)[:70]}')
            continue
        prov = ((d.get('destination') or {}).get('state') or {}).get('name') or ''
        opts = d.get('options') or []
        # La opcion recomendada es la que ve el comprador por defecto
        op = next((o for o in opts if o.get('display') == 'recommended'), opts[0] if opts else None)
        if not op:
            print(f'{cp:<7}{prov:<18}sin opciones de envio')
            continue
        print(f'{cp:<7}{prov[:17]:<18}'
              f'{op.get("base_cost", 0):>10,.0f}'
              f'{op.get("cost", 0):>12,.0f}'
              f'{op.get("list_cost", 0):>11,.0f}'
              f'  {op.get("shipping_method_type", "")}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
