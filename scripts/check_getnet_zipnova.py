#!/usr/bin/env python3
"""Verifica que el bloque Zipnova del webhook de GetNet habria disparado.

SOLO LECTURA: reconstruye la condicion y arma los bultos, pero NUNCA llama a
zipnova_crear_envio (eso crearia un envio real).

Uso:  venv/bin/python3 scripts/check_getnet_zipnova.py [pedido_ref ...]
      sin argumentos usa los dos pedidos afectados del 18/09
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from tienda_bp import get_db, armar_bultos_zipnova  # noqa: E402

DEFAULT = ['0ca2677948e044', '53393c2d84e84b']


def main():
    refs = sys.argv[1:] or DEFAULT
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        fmt = ','.join(['%s'] * len(refs))
        cur.execute(f"""
            SELECT pedido_ref, datos_cliente, datos_carrito, metodo_envio, total
            FROM pedidos_pendientes_getnet WHERE pedido_ref IN ({fmt})
        """, tuple(refs))
        filas = cur.fetchall()
        cur.close()

        for r in filas:
            cli = json.loads(r['datos_cliente'])
            cart = json.loads(r['datos_carrito'])
            metodo = r['metodo_envio']
            tiene_quote = bool(cli.get('zipnova_quote'))
            dispara = (metodo == 'Zippin' and tiene_quote)
            print(f"\n=== {r['pedido_ref']} ===")
            print(f"  metodo_envio          : {metodo}")
            print(f"  cli['zipnova_quote']  : {'presente' if tiene_quote else 'FALTA'}")
            print(f"  -> el bloque dispara  : {'SI' if dispara else 'NO'}")
            if not dispara:
                continue
            try:
                db_b = get_db()
                bultos = armar_bultos_zipnova(cart, db_b)
                db_b.close()
                print(f"  bultos armados        : {len(bultos)}")
                for b in bultos:
                    print(f"     - {b.get('sku'):<16} {b.get('weight')}g "
                          f"{b.get('width')}x{b.get('length')}x{b.get('height')}cm")
                q = cli.get('zipnova_quote') or {}
                print(f"  destino               : CP {q.get('cp_destino')} "
                      f"{q.get('ciudad')} / {q.get('provincia')}")
                print(f"  carrier cotizado      : {q.get('carrier_name')} "
                      f"(${q.get('precio')})")
            except Exception as e:
                print(f"  ERROR armando bultos  : {type(e).__name__}: {e}")
        db.close()
    print('\n(no se llamo a zipnova_crear_envio: verificacion de solo lectura)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
