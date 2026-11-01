#!/usr/bin/env python3
"""Corrige la fecha de nacimiento en las notas de UNA venta.

Nace del caso PW-1041164792, donde un `[:10]` sobre un año de 5 digitos dejo
guardado 'Nacimiento: 20001-08-0'. La fecha correcta la confirmo la clienta.

Reemplaza solo el texto 'Nacimiento: <viejo>' por 'Nacimiento: <nuevo>' en esa
venta. No toca nada mas. Sin --aplicar solo muestra lo que haria.
"""
import argparse
import os
import sys

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('numero_venta')
    ap.add_argument('viejo', help="texto actual, ej '20001-08-0'")
    ap.add_argument('nuevo', help="texto correcto, ej '2001-08-03'")
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()

    import tienda_bp as tb
    if not tb._fecha_nacimiento_valida(a.nuevo):
        print(f'La fecha nueva {a.nuevo!r} no pasa la validacion. Abortado.')
        return 1

    viejo = f'Nacimiento: {a.viejo}'
    nuevo = f'Nacimiento: {a.nuevo}'

    cn = pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER'), password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME'), cursorclass=pymysql.cursors.DictCursor)
    try:
        cur = cn.cursor()
        cur.execute("SELECT id, notas FROM ventas WHERE numero_venta=%s", (a.numero_venta,))
        v = cur.fetchone()
        if not v:
            print(f'No existe {a.numero_venta}'); return 1
        if viejo not in (v['notas'] or ''):
            print(f'La venta no contiene {viejo!r}. Nada que hacer.'); return 1

        print(f'venta  : {a.numero_venta} (id {v["id"]})')
        print(f'antes  : ...{v["notas"][-45:]}')
        print(f'despues: ...{v["notas"].replace(viejo, nuevo)[-45:]}')

        if not a.aplicar:
            print('\n>> Vista previa. Agrega --aplicar para escribir.')
            return 0

        cur.execute("""UPDATE ventas SET notas = REPLACE(notas, %s, %s)
                       WHERE numero_venta = %s AND notas LIKE %s""",
                    (viejo, nuevo, a.numero_venta, f'%{viejo}%'))
        filas = cur.rowcount
        cn.commit()
        cur.execute("SELECT RIGHT(notas,45) t FROM ventas WHERE numero_venta=%s",
                    (a.numero_venta,))
        print(f'\nfilas afectadas: {filas}')
        print(f'quedo  : ...{cur.fetchone()["t"]}')
        cur.close()
    finally:
        cn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
