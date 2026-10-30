#!/usr/bin/env python3
"""Prueba que el cupón del evento NO alcance a las almohadas y que las cuentas cierren.

Lo que importa verificar, porque toca el monto cobrado:

  A) El cupón descuenta solo sobre colchones y sommiers.
  B) Las almohadas no reciben descuento del cupón.
  C) INVARIANTE: la suma de (precio por item x cantidad), ya con el factor del
     cupón, da exactamente subtotal - descuento. Si esto no se cumple, lo que
     se guarda en items_venta no coincide con lo que se cobró.
  D) Vale para cupón porcentual y para cupón de monto fijo.
  E) Con el 2x1 activo, las almohadas reciben el 2x1 y nada del cupón.

No toca la base ni la configuración: el estado del 2x1 se simula.
"""
import sys

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')

fallos = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


def invariante(tb, carrito, cupon):
    """La suma por item tiene que dar subtotal - descuento."""
    subtotal  = tb.subtotal_carrito(carrito)
    descuento = tb.descuento_cupon(carrito, cupon)
    suma = sum(
        round(tb.precio_efectivo_item(i) * tb.factor_cupon_sku(i['sku'], carrito, cupon))
        * int(i['cantidad'])
        for i in carrito
    )
    # Se compara con tolerancia de 1 peso por item, por el round() por unidad
    return abs(suma - (subtotal - descuento)) <= len(carrito), suma, subtotal - descuento


def main():
    import tienda_bp as tb

    COLCHON  = {'sku': 'CEX160', 'nombre': 'Colchón', 'precio': 500000.0, 'cantidad': 1}
    SOMMIER  = {'sku': 'SEX160', 'nombre': 'Sommier', 'precio': 800000.0, 'cantidad': 1}
    ALMOHADA = {'sku': 'CLASICA', 'nombre': 'Almohada', 'precio': 90000.0, 'cantidad': 2}

    CUPON_PCT = {'tipo': 'pct', 'valor': 5}
    CUPON_FIJO = {'tipo': 'fijo', 'valor': 50000}

    # ── 2x1 APAGADO ───────────────────────────────────────────────────────
    tb.promo_2x1_activa = lambda: False
    print('escenario: 2x1 APAGADO, cupon 5%')

    carrito = [dict(COLCHON), dict(ALMOHADA)]
    sub = tb.subtotal_carrito(carrito)            # 500.000 + 180.000
    eleg = tb.subtotal_elegible_cupon(carrito)
    desc = tb.descuento_cupon(carrito, CUPON_PCT)
    chequear(sub == 680000, 'subtotal del carrito', f'{sub:,.0f}')
    chequear(eleg == 500000, 'elegible = solo el colchon', f'{eleg:,.0f}')
    chequear(desc == 25000, 'descuento = 5% de 500.000', f'{desc:,.0f}')
    chequear(tb.factor_cupon_sku('CLASICA', carrito, CUPON_PCT) == 1.0,
             'la almohada no recibe factor de cupon')
    chequear(abs(tb.factor_cupon_sku('CEX160', carrito, CUPON_PCT) - 0.95) < 1e-9,
             'el colchon recibe 0,95')
    ok, s, e = invariante(tb, carrito, CUPON_PCT)
    chequear(ok, 'INVARIANTE suma por item = subtotal - descuento', f'{s:,.0f} vs {e:,.0f}')

    print('escenario: carrito SOLO de almohadas, cupon 5%')
    carrito = [dict(ALMOHADA)]
    chequear(tb.subtotal_elegible_cupon(carrito) == 0, 'elegible = 0')
    chequear(tb.descuento_cupon(carrito, CUPON_PCT) == 0, 'descuento = 0')
    ok, s, e = invariante(tb, carrito, CUPON_PCT)
    chequear(ok, 'INVARIANTE', f'{s:,.0f} vs {e:,.0f}')

    print('escenario: cupon de MONTO FIJO 50.000, mezcla')
    carrito = [dict(COLCHON), dict(ALMOHADA)]
    desc = tb.descuento_cupon(carrito, CUPON_FIJO)
    chequear(desc == 50000, 'descuento fijo completo (cabe en lo elegible)', f'{desc:,.0f}')
    ok, s, e = invariante(tb, carrito, CUPON_FIJO)
    chequear(ok, 'INVARIANTE con cupon fijo', f'{s:,.0f} vs {e:,.0f}')

    print('escenario: cupon fijo MAYOR que lo elegible')
    carrito = [dict(ALMOHADA), {'sku': 'CEX80', 'nombre': 'C', 'precio': 30000.0, 'cantidad': 1}]
    desc = tb.descuento_cupon(carrito, CUPON_FIJO)
    chequear(desc == 30000, 'se topea en lo elegible, no come la almohada', f'{desc:,.0f}')
    ok, s, e = invariante(tb, carrito, CUPON_FIJO)
    chequear(ok, 'INVARIANTE', f'{s:,.0f} vs {e:,.0f}')

    # ── 2x1 ENCENDIDO ─────────────────────────────────────────────────────
    tb.promo_2x1_activa = lambda: True
    print('escenario: 2x1 ENCENDIDO + cupon 5%')
    carrito = [dict(COLCHON), dict(ALMOHADA)]
    sub = tb.subtotal_carrito(carrito)
    chequear(sub == 590000, 'subtotal con 2x1 (2 almohadas = 90.000)', f'{sub:,.0f}')
    chequear(tb.subtotal_elegible_cupon(carrito) == 500000,
             'elegible sigue siendo solo el colchon')
    chequear(tb.descuento_cupon(carrito, CUPON_PCT) == 25000,
             'descuento no toca la almohada')
    pu = tb.precio_efectivo_item(dict(ALMOHADA))
    chequear(pu == 45000, 'almohada: 45.000 por unidad llevando 2', f'{pu:,.0f}')
    chequear(tb.precio_2x1_por_unidad(90000) == 45000,
             'el mensaje de vitrina dice 45.000')
    ok, s, e = invariante(tb, carrito, CUPON_PCT)
    chequear(ok, 'INVARIANTE con 2x1 + cupon', f'{s:,.0f} vs {e:,.0f}')

    print('escenario: sommier + almohada, para cubrir el otro elegible')
    carrito = [dict(SOMMIER), dict(ALMOHADA)]
    chequear(tb.subtotal_elegible_cupon(carrito) == 800000, 'el sommier es elegible')
    ok, s, e = invariante(tb, carrito, CUPON_PCT)
    chequear(ok, 'INVARIANTE', f'{s:,.0f} vs {e:,.0f}')

    print()
    print('RESULTADO:', 'todo correcto' if not fallos else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
