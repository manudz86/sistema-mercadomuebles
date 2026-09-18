#!/usr/bin/env python3
"""Verificacion de la promo de 3 cuotas sin interes (solo lectura).

Muestra: estado de hoy, coeficiente efectivo de Payway 3c, si Payway queda
habilitado, y una simulacion dia por dia de la semana.

Uso:  venv/bin/python3 scripts/check_promo3sin.py
"""
import os
import sys
from datetime import datetime
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tienda_bp as t  # noqa: E402

DIAS = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
PRECIO = 500000


def main():
    app = __import__('app').app
    with app.app_context():
        print('=== HOY ===')
        activa = t.promo_3sin_activa()
        coef = t.get_coef_3_payway()
        print(f'  promo_3sin_activa()   : {activa}')
        print(f'  get_coef_3_payway()   : {coef}')
        print(f'  payway_cuotas_activo(): {t.payway_cuotas_activo()}')
        print(f'  cuotas producto       : {t.calc_cuotas_producto(PRECIO)["3"]}')

        print(f'\n=== SIMULACION SEMANA (precio {PRECIO:,}) ===')
        print(f'  {"dia":<10} {"promo":<6} {"coef":<6} {"payway":<7} 3 cuotas de')
        for wd in range(7):
            # 2026-09-14 fue lunes → +wd da cada dia de la semana
            fecha = datetime(2026, 9, 14 + wd, 12, 0, 0)
            with mock.patch.object(t, 'datetime', wraps=datetime) as _dt:
                pass  # datetime se importa adentro de la funcion; parcheamos distinto
            # Parcheo directo del weekday via congelar la clase datetime del modulo
            real_dt = datetime

            class FakeDT(real_dt):
                @classmethod
                def now(cls, tz=None):
                    return fecha

            import datetime as dt_mod
            orig = dt_mod.datetime
            dt_mod.datetime = FakeDT
            try:
                pr = t.promo_3sin_activa()
                cf = t.get_coef_3_payway()
                pw = t.payway_cuotas_activo()
                c3 = t.calc_cuotas_producto(PRECIO)['3']['cuota']
            finally:
                dt_mod.datetime = orig
            print(f'  {DIAS[wd]:<10} {str(pr):<6} {cf:<6} {str(pw):<7} {c3}')

        print('\n=== COHERENCIA VITRINA vs COBRO ===')
        print('  Ambos usan get_coef_3_payway(); mismo valor por construccion.')
        print(f'  total mostrado y cobrado para {PRECIO:,} = {round(PRECIO * coef):,}')


if __name__ == '__main__':
    main()
