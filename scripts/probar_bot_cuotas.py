#!/usr/bin/env python3
"""Compara lo que el bot de WhatsApp le dice al cliente contra lo que cobra la web.

Imprime el bloque de promos que se inyecta al system prompt y, para una muestra
de productos, la linea "Cuotas Web" del contexto del bot junto a los importes
que calcula la ficha del producto. Si no coinciden, el bot esta cotizando
distinto de lo que se cobra.

Solo lectura.
"""
import re
import sys

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')

fallos = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


def main():
    import tienda_bp as tb
    import whatsapp_bp as wb
    from flask import Flask

    app = Flask(__name__, root_path='/home/cannon/app',
                static_folder='/home/cannon/app/static',
                template_folder='/home/cannon/app/templates')
    app.secret_key = 'bot'
    app.register_blueprint(tb.tienda_bp, url_prefix='/tienda')

    with app.test_request_context('/tienda/'):
        print('=' * 72)
        print('BLOQUE DE PROMOS QUE VE EL BOT')
        print('=' * 72)
        promos = wb.get_promos_context()
        print(promos if promos else '(vacio)')
        print()

        # Estado real, para contrastar
        print('=' * 72)
        print('ESTADO REAL DE LA TIENDA')
        print('=' * 72)
        estado = {
            '3 cuotas activas':  tb.hay_3cuotas_activo(),
            '  (3 sin interes)': tb.promo_3sin_activa(),
            '6 GetNet':          tb.getnet_activo(),
            '6 Payway':          tb.payway_6_activo(),
            '12 MercadoPago':    tb.mp_12_cuotas_activo(),
            'evento activo':     tb.get_hot_event().get('activo'),
            '2x1 almohadas':     tb.promo_2x1_activa(),
        }
        for k, v in estado.items():
            print(f'  {k:<20} {"SI" if v else "no"}')
        print()

        # Coherencia del bloque de promos con el estado
        he = tb.get_hot_event()
        if he.get('activo'):
            chequear(he.get('titulo', '') in promos, 'el bloque nombra el evento')
            chequear(he.get('cupon', '') in promos, 'el bloque nombra el cupon')
            chequear(str(he.get('fechas', '')) in promos,
                     'el bloque usa el texto del cartel (no se adelanta)',
                     he.get('fechas', ''))
            chequear('NO aplica a almohadas' in promos,
                     'aclara que el cupon no alcanza a las almohadas')
        chequear(('SIN INTERÉS' in promos),
                 'menciona la promo de 3 sin interes (vigente o no)')

        # Contexto de productos: comparar la linea de cuotas con la ficha
        print('=' * 72)
        print('CUOTAS: BOT vs FICHA DEL PRODUCTO')
        print('=' * 72)
        wb._productos_cache = {'ts': 0, 'data': None}   # invalidar cache si existe
        ctx = wb.get_productos_context()

        lineas = ctx.split('\n')
        revisados = 0
        for i, ln in enumerate(lineas):
            # Formato real: "• Nombre (SKU:XXX) | Web: $326,700 (-10%) | Lista: ..."
            # o, sin descuento, "| Precio: $X". Los miles van con coma.
            m = re.match(r'• (.+?) \(SKU:([^)]+)\) \| (?:Web|Precio): \$([\d.,]+)', ln)
            if not m:
                continue
            cuotas_ln = lineas[i + 1] if i + 1 < len(lineas) else ''
            if 'Cuotas Web:' not in cuotas_ln:
                continue
            sku = m.group(2)
            precio = float(m.group(3).replace('.', '').replace(',', ''))
            esperado = tb.calc_cuotas_producto(precio, sku)

            for n in ('3', '6', '12'):
                if f'{n} fijas' in cuotas_ln or (n == '3' and 'SIN INTERÉS' in cuotas_ln):
                    tot = esperado[n]['total']
                    chequear(tot in cuotas_ln,
                             f'{sku}: total de {n} cuotas coincide con la ficha', tot)
            revisados += 1
            if revisados <= 2:
                print(f'    {ln[:88]}')
                print(f'    {cuotas_ln}')
            if revisados >= 6:
                break

        chequear(revisados > 0, 'se encontraron productos con linea de cuotas',
                 f'{revisados} revisados')

        # Que no ofrezca planes apagados
        if not tb.getnet_activo() and not tb.payway_6_activo():
            chequear('6 fijas' not in ctx, 'NO ofrece 6 cuotas (ningun medio activo)')
        else:
            chequear('6 fijas' in ctx, 'SI ofrece 6 cuotas (hay medio activo)')
        if not tb.mp_12_cuotas_activo():
            chequear('12 fijas' not in ctx, 'NO ofrece 12 cuotas')

    print()
    print('RESULTADO:', 'el bot dice lo mismo que la web' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
