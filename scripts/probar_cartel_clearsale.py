#!/usr/bin/env python3
"""Verifica el cartel de arriba y el filtro de ventas rechazadas por ClearSale.

Pide /ventas/activas a la propia app (con el login desactivado para la prueba)
y comprueba que:

  - el cartel rojo aparece cuando hay ventas rechazadas activas
  - ?solo_clearsale=1 deja SOLO esas ventas
  - el cartel de ML sigue intacto y los dos filtros no se pisan

No escribe nada: solo GETs a la propia app.
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


def ventas_en_pagina(html, universo):
    """Cuales de las ventas activas de la base aparecen en la pagina. Se compara
    contra la lista real en vez de buscar un patron: hay textos sueltos en la
    pagina que parecen un numero de venta y no lo son."""
    return sorted(n for n in universo if n and n in html)


def main():
    import app as A

    ph, par = A._cs_rechazan_sql()
    print(f'estados de rechazo ... {par}')
    chequear(bool(ph) and 'SUS' in par, 'CS_RECHAZAN llega a la query', ph)

    esperadas = [r['numero_venta'] for r in A.query_db(
        "SELECT numero_venta FROM ventas WHERE estado_entrega='pendiente' "
        f"AND UPPER(COALESCE(clearsale_estado,'')) IN ({ph})", tuple(par))]
    print(f'ventas rechazadas activas en la base: {esperadas or "ninguna"}')

    # LOGIN_DISABLED hace que @login_required deje pasar: alcanza para pedir la
    # pagina sin armar una sesion (el flask/werkzeug de este venv no se lleva
    # bien con session_transaction).
    A.app.config['LOGIN_DISABLED'] = True
    A.app.config['WTF_CSRF_ENABLED'] = False
    # El werkzeug instalado no expone __version__ y test_client lo lee para armar
    # el User-Agent. Se lo pongo solo para esta prueba.
    import werkzeug
    if not hasattr(werkzeug, '__version__'):
        werkzeug.__version__ = 'prueba'
    cli = A.app.test_client()

    sin = cli.get('/ventas/activas')
    con = cli.get('/ventas/activas?solo_clearsale=1')
    chequear(sin.status_code == 200 and con.status_code == 200,
             'las dos vistas responden 200', f'{sin.status_code} / {con.status_code}')
    h_sin = sin.get_data(as_text=True)
    h_con = con.get_data(as_text=True)

    hay = bool(esperadas)
    print('cartel de arriba')
    chequear(('rechazada por ClearSale' in h_sin or 'rechazadas por ClearSale' in h_sin) == hay,
             'el cartel aparece solo si hay ventas rechazadas', f'hay={hay}')
    if hay:
        chequear('No entregar: cancelar la venta y devolver el importe' in h_sin,
                 'el cartel dice que no se entregue y se devuelva')
        chequear('solo_clearsale=1' in h_sin, 'ofrece el link al filtro')
        chequear('Mostrando' in h_con and 'por ClearSale' in h_con,
                 'con el filtro puesto cambia el texto del cartel')
        chequear('/ventas/activas"' in h_con, 'y ofrece volver a ver todas')

    print('el filtro')
    universo = [r['numero_venta'] for r in A.query_db(
        "SELECT numero_venta FROM ventas WHERE estado_entrega='pendiente'")]
    listadas = ventas_en_pagina(h_con, universo)
    chequear(all(v in listadas for v in esperadas),
             'las rechazadas aparecen con el filtro puesto', str(listadas[:6]))
    sobrantes = [v for v in listadas if v not in esperadas]
    chequear(not sobrantes, 'no se cuela ninguna otra venta', str(sobrantes[:6]))
    chequear(len(ventas_en_pagina(h_sin, universo)) >= len(listadas),
             'sin filtro se ven al menos las mismas',
             f'{len(ventas_en_pagina(h_sin, universo))} sin filtro / {len(listadas)} con filtro')

    print('el recuadro rojo dentro de la fila')
    if hay:
        chequear('ClearSale:' in h_con and 'Cancelar y devolver' in h_con,
                 'la fila sigue mostrando la alerta roja')

    print('no se rompio el cartel de ML')
    n_ml = A.query_one("SELECT COUNT(*) c FROM ventas WHERE estado_entrega='pendiente' "
                       "AND cancelada_en_ml=1")['c']
    chequear(('cancelada en ML' in h_sin or 'canceladas en ML' in h_sin) == bool(n_ml),
             'el cartel de ML responde a su propio contador', f'n_ml={n_ml}')
    ml = cli.get('/ventas/activas?solo_canceladas=1')
    chequear(ml.status_code == 200, 'el filtro de ML sigue respondiendo', str(ml.status_code))
    amb = cli.get('/ventas/activas?solo_canceladas=1&solo_clearsale=1')
    chequear(amb.status_code == 200, 'los dos filtros juntos no revientan', str(amb.status_code))

    print()
    print('RESULTADO:', 'el cartel y el filtro funcionan' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
