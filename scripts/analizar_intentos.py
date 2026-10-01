#!/usr/bin/env python3
"""Analiza intentos de pago: cruza pedidos_pendientes con payway_intentos y
muestra que cambio entre intento e intento (tarjeta, email, DNI, direccion, IP).

Solo lectura.

Uso:
    venv/bin/python3 scripts/analizar_intentos.py ref1 ref2 ...
    venv/bin/python3 scripts/analizar_intentos.py --buscar texto   (dni/email/ip)
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, query_db  # noqa: E402

CAMPOS = ['nombre', 'dni', 'email', 'telefono', 'direccion', 'cp', 'tipo_entrega',
          'tipo_factura', 'cuit', '_capi_ip']


def cargar(js):
    try:
        return json.loads(js)
    except Exception:
        # algunos registros traen comillas escapadas en _origen_*: recortar ahi
        corte = js.find(', "_origen_first"')
        if corte > 0:
            try:
                return json.loads(js[:corte] + '}')
            except Exception:
                pass
    return {}


def main():
    with app.app_context():
        if '--buscar' in sys.argv:
            t = sys.argv[sys.argv.index('--buscar') + 1]
            filas = query_db(
                "SELECT ref, fecha_creacion, cliente_json, carrito_json FROM pedidos_pendientes "
                "WHERE cliente_json LIKE %s ORDER BY fecha_creacion", (f'%{t}%',)) or []
        else:
            refs = [a for a in sys.argv[1:] if not a.startswith('--')]
            if not refs:
                print(__doc__)
                return 1
            fmt = ','.join(['%s'] * len(refs))
            filas = query_db(
                f"SELECT ref, fecha_creacion, cliente_json, carrito_json FROM pedidos_pendientes "
                f"WHERE ref IN ({fmt}) ORDER BY fecha_creacion", tuple(refs)) or []

        # pagos payway por ref
        pagos = {}
        for p in query_db("SELECT site_transaction_id, fecha, amount, status, motivo, "
                          "card_brand, bin, payment_method_id FROM payway_intentos") or []:
            ref = (p['site_transaction_id'] or '').replace('PW-', '')
            pagos[ref] = p

        print(f'{len(filas)} intento(s)\n')
        prev = None
        for f in filas:
            d = cargar(f['cliente_json'])
            pg = pagos.get(f['ref'])
            cart = cargar(f['carrito_json']) if f['carrito_json'].startswith('{') else None
            try:
                items = json.loads(f['carrito_json'])
                total = sum(float(i['precio']) * int(i['cantidad']) for i in items)
                n_items = sum(int(i['cantidad']) for i in items)
            except Exception:
                total, n_items = 0, 0

            print(f"── {f['ref']}  {f['fecha_creacion']}")
            if pg:
                print(f"   PAGO: ${pg['amount']:,.0f} {pg['status'].upper()} {pg['motivo'] or ''} "
                      f"| {pg['card_brand']} BIN {pg['bin']} (pm_id {pg['payment_method_id']})")
            else:
                print('   PAGO: (no llego a Payway)')
            print(f"   carrito: {n_items} items, ${total:,.0f}")
            for c in CAMPOS:
                v = d.get(c)
                if prev is not None and prev.get(c) != v:
                    print(f"   >>> {c}: {prev.get(c)!r}  ->  {v!r}   *** CAMBIO ***")
                else:
                    print(f"       {c}: {v!r}")
            print()
            prev = d
    return 0


if __name__ == '__main__':
    sys.exit(main())
