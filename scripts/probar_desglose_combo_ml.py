#!/usr/bin/env python3
"""Verifica el desglose de un combo de ML en sus piezas.

Reproduce el tramo de _importar_orden_automatica que arma items_bd, usando
el MISMO COMBOS_ML_DESGLOSAR y la misma verificacion de SKU, con la orden
real 2000019305564544 (la que entro sin la almohada).

No importa ninguna orden ni escribe en la base.
"""
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
os.environ['CANNON_SIN_SCHEDULER'] = '1'

fallos = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


def armar_items(A, items_orden):
    """Mismo tramo que _importar_orden_automatica, sin el resto de la importacion."""
    items_bd = []
    for item in items_orden:
        sku_ml = item.get('sku', '')
        sku_norm, cant_override = A.normalizar_sku_ml(sku_ml) if sku_ml else ('', 0)
        cantidad_final = (item['cantidad'] * cant_override) if cant_override > 0 else item['cantidad']
        precio_final = round(item['precio'] / cant_override) if cant_override > 0 else item['precio']

        desglose = A.COMBOS_ML_DESGLOSAR.get(sku_norm.upper())
        if desglose and all(A.verificar_sku_en_bd(s)[0] for s, _ in desglose):
            for i, (s, c) in enumerate(desglose):
                items_bd.append({'sku': s, 'cantidad': c * cantidad_final,
                                 'precio': precio_final if i == 0 else 0})
            continue
        items_bd.append({'sku': sku_norm, 'cantidad': cantidad_final, 'precio': precio_final})
    return items_bd


def main():
    import app as A

    with A.app.app_context():
        print('orden real 2000019305564544 (1x CPR8020+ a $175.750)')
        items = armar_items(A, [{'sku': 'CPR8020+', 'cantidad': 1, 'precio': 175750,
                                 'titulo': 'Colchón Cannon Princess 24kg 1 Plaza 80x190x20'}])
        for it in items:
            print(f'     {it["cantidad"]}x {it["sku"]:<10} ${it["precio"]:,}'.replace(',', '.'))
        chequear(len(items) == 2, 'se cargan 2 articulos', str(len(items)))
        chequear([i['sku'] for i in items] == ['CPR8020', 'PLATINO'],
                 'son CPR8020 y PLATINO', str([i['sku'] for i in items]))
        chequear(items[1]['precio'] == 0, 'la almohada va en 0')
        chequear(sum(i['precio'] * i['cantidad'] for i in items) == 175750,
                 'el total sigue dando el de la orden',
                 str(sum(i['precio'] * i['cantidad'] for i in items)))

        print('2 unidades del mismo combo')
        items = armar_items(A, [{'sku': 'CPR8020+', 'cantidad': 2, 'precio': 175750,
                                 'titulo': 'x'}])
        chequear([(i['sku'], i['cantidad']) for i in items]
                 == [('CPR8020', 2), ('PLATINO', 2)],
                 'se duplican las dos piezas',
                 str([(i['sku'], i['cantidad']) for i in items]))
        chequear(sum(i['precio'] * i['cantidad'] for i in items) == 351500,
                 'el total acompaña')

        print('otros SKU no se tocan (acotado a CPR8020+)')
        for sku, esperado in (('CPR8020', 'CPR8020'), ('CEX140Z', 'CEX140'),
                              ('SPR8020', 'SPR8020'), ('SEX140+2', 'SEX140+2')):
            r = armar_items(A, [{'sku': sku, 'cantidad': 1, 'precio': 1000, 'titulo': 'x'}])
            chequear(len(r) == 1 and r[0]['sku'] == esperado,
                     f'{sku} entra como 1 linea ({esperado})',
                     str([i['sku'] for i in r]))

    print()
    print('RESULTADO:', 'el desglose funciona' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
