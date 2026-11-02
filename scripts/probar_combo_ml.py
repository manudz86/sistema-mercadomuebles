#!/usr/bin/env python3
"""Verifica que un combo de ML se resuelva y descuente stock bien.

Comprueba las tres piezas de la cadena, sin tocar stock real:
  1. normalizar_sku_ml NO le recorta el sufijo (porque el SKU ya existe)
  2. descontar_stock_item lo reconoce como compuesto y lo descompone
  3. los componentes y cantidades son los esperados

El descuento se corre dentro de una transaccion que se revierte, asi que el
stock queda igual que antes. Se verifica que efectivamente haya vuelto.
"""
import os
import sys

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')

# Importar app.py arranca el scheduler con todos sus jobs. Para un script de
# prueba eso significa correr importaciones de ML desde un proceso suelto.
os.environ['CANNON_SIN_SCHEDULER'] = '1'

fallos = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


def main():
    sku_ml = sys.argv[1] if len(sys.argv) > 1 else 'CPR8020+'
    esperado = {'CPR8020': 1, 'PLATINO': 1}

    import app as A

    # 1. Normalizacion
    print('1) normalizar_sku_ml')
    A._SKUS_ML_CACHE['skus'] = None            # forzar relectura
    norm, override = A.normalizar_sku_ml(sku_ml)
    chequear(norm == sku_ml, f'{sku_ml} NO se recorta', f'-> {norm!r}')
    chequear(override == 0, 'sin override de cantidad')
    # Control: uno que si se tiene que recortar
    n2, _ = A.normalizar_sku_ml('CEX140Z')
    chequear(n2 == 'CEX140', 'CEX140Z sigue recortandose a CEX140', f'-> {n2!r}')

    cn = pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER'), password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME'), cursorclass=pymysql.cursors.DictCursor,
        autocommit=False)
    cur = cn.cursor()
    try:
        # 2. Componentes
        print('2) componentes en la base')
        cur.execute("""SELECT pb.sku, c.cantidad_necesaria
                       FROM productos_compuestos pc
                       JOIN componentes c ON c.producto_compuesto_id = pc.id
                       JOIN productos_base pb ON pb.id = c.producto_base_id
                       WHERE pc.sku = %s""", (sku_ml,))
        comps = {r['sku']: r['cantidad_necesaria'] for r in cur.fetchall()}
        chequear(comps == esperado, f'componentes = {esperado}', str(comps))

        # 3. Descuento de stock, en una transaccion que se revierte
        print('3) descuento de stock (simulado, se revierte)')
        skus = sorted(esperado)
        cur.execute(f"SELECT sku, stock_actual FROM productos_base "
                    f"WHERE sku IN ({','.join(['%s'] * len(skus))})", skus)
        antes = {r['sku']: r['stock_actual'] for r in cur.fetchall()}

        A.descontar_stock_item(cur, {'sku': sku_ml, 'cantidad': 1}, 'DEP')

        cur.execute(f"SELECT sku, stock_actual FROM productos_base "
                    f"WHERE sku IN ({','.join(['%s'] * len(skus))})", skus)
        despues = {r['sku']: r['stock_actual'] for r in cur.fetchall()}

        for s in skus:
            bajo = antes[s] - despues[s]
            chequear(bajo == esperado[s],
                     f'{s}: bajo {esperado[s]}', f'{antes[s]} -> {despues[s]}')
    finally:
        cn.rollback()
        # Confirmar que el rollback dejo todo como estaba
        cur.execute(f"SELECT sku, stock_actual FROM productos_base "
                    f"WHERE sku IN ({','.join(['%s'] * len(esperado))})", sorted(esperado))
        final = {r['sku']: r['stock_actual'] for r in cur.fetchall()}
        print('4) rollback')
        for s in sorted(esperado):
            chequear(final[s] == antes[s], f'{s}: stock restaurado',
                     f'{final[s]}')
        cur.close(); cn.close()

    print()
    print('RESULTADO:', 'el combo se resuelve y descuenta bien' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
