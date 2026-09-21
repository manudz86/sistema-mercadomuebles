#!/usr/bin/env python3
"""Verificacion del historial de promos + tope de aporte (sin tocar ML).

Comprueba:
  1. que la tabla promos_ml_historial exista y se pueda escribir/leer
  2. que _promo_limite_aporte() lea la config
  3. que _promo_aporte_de() calcule bien co-financiadas y no co-financiadas
  4. que bot_precios_log ahora exista y sistema_logs acepte el INSERT corregido

Escribe filas de PRUEBA en promos_ml_historial y despues las borra.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import (app, query_db, query_one, execute_db,  # noqa: E402
                 _promo_limite_aporte, _promo_aporte_de, _promo_hist_registrar)

MLA_TEST = 'MLA_TEST_BORRAR'


def main():
    with app.app_context():
        print('1) Tope de aporte configurado')
        print(f'   _promo_limite_aporte() = {_promo_limite_aporte()}%')

        print('\n2) Calculo de aporte')
        casos = [
            ({'seller_percentage': 23.5, 'meli_percentage': 5.7}, 'co-financiada'),
            ({'original_price': 770000, 'price': 606000}, 'no co-financiada (DEAL)'),
            ({}, 'sin datos'),
        ]
        for p, desc in casos:
            print(f'   {desc:<28} -> {_promo_aporte_de(p)}')

        print('\n3) Escritura y lectura del historial')
        _promo_hist_registrar(accion='aplicar', origen='script', mla_id=MLA_TEST,
                              sku='TEST', campania_id='P-TEST', campania_nombre='Prueba',
                              tipo='SMART', mostrado_pct=3.0, aplicado_pct=14.25,
                              aplicado_meli_pct=0.75, aplicado_precio=100, aplicado_original=120,
                              supero_limite=True, revertida=True, ok=False,
                              error='prueba automatica')
        _promo_hist_registrar(accion='aplicar', origen='script', mla_id=MLA_TEST,
                              sku='TEST', campania_id='P-TEST', campania_nombre='Prueba',
                              tipo='SMART', mostrado_pct=3.0, aplicado_pct=3.1)
        filas = query_db("SELECT mostrado_pct, aplicado_pct, delta_pct, coincide, "
                         "supero_limite, revertida FROM promos_ml_historial "
                         "WHERE mla_id=%s ORDER BY id", (MLA_TEST,)) or []
        for f in filas:
            print(f"   mostrado={f['mostrado_pct']} aplicado={f['aplicado_pct']} "
                  f"delta={f['delta_pct']} coincide={f['coincide']} "
                  f"supero={f['supero_limite']} revertida={f['revertida']}")
        ok_calc = (len(filas) == 2
                   and float(filas[0]['delta_pct']) == 11.25 and filas[0]['coincide'] == 0
                   and filas[1]['coincide'] == 1)
        print(f'   calculo de delta/coincide: {"OK" if ok_calc else "MAL"}')

        execute_db("DELETE FROM promos_ml_historial WHERE mla_id=%s", (MLA_TEST,))
        resto = query_one("SELECT COUNT(*) AS n FROM promos_ml_historial WHERE mla_id=%s",
                          (MLA_TEST,))
        print(f'   limpieza de filas de prueba: {"OK" if resto["n"] == 0 else "QUEDARON"}')

        print('\n4) Logs del bot de precios')
        t = query_one("SHOW TABLES LIKE 'bot_precios_log'")
        print(f'   tabla bot_precios_log: {"existe" if t else "NO EXISTE"}')
        cols = {c['Field'] for c in (query_db("DESCRIBE sistema_logs") or [])}
        print(f'   sistema_logs tiene "detalle": {"si" if "detalle" in cols else "NO"}')
        print(f'   sistema_logs tiene "descripcion": '
              f'{"si (raro)" if "descripcion" in cols else "no (correcto)"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
