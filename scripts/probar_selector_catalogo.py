#!/usr/bin/env python3
"""Verifica el selector de catalogo en Modificar Publis ML.

Al buscar un SKU que compite en varios catalogos, la pantalla tiene que:

  - mostrar el numero de catalogo en el badge de cada publicacion (no solo
    la palabra CATALOGO)
  - ofrecer un boton por catalogo, con la cantidad de publis de cada uno
  - ofrecer "Sin catalogo" si el SKU tambien tiene publis de listado general
  - marcar cada fila y cada tarjeta mobile con su catalogo, que es lo que el
    filtro usa para esconderlas
  - no mostrar el selector cuando el SKU esta en un solo catalogo y no tiene
    publis de listado general

Hace los GET que haria la pantalla (consulta a ML). No escribe nada salvo el
indice mla_catalogo, que se refresca solo al buscar y es reconstruible.
"""
import os
import re
import sys
from collections import Counter

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
os.environ['CANNON_SIN_SCHEDULER'] = '1'

fallos = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


def main():
    import app as A

    A.app.config['LOGIN_DISABLED'] = True
    import werkzeug
    if not hasattr(werkzeug, '__version__'):
        werkzeug.__version__ = 'prueba'
    cli = A.app.test_client()

    # Un SKU que compita en varios catalogos y que ademas tenga publis de
    # listado general, para probar los dos botones
    fila = A.query_one(
        "SELECT m.sku, COUNT(DISTINCT c.catalog_product_id) cats "
        "FROM sku_mla_mapeo m JOIN mla_catalogo c ON c.mla_id = m.mla_id "
        "WHERE m.activo = TRUE AND c.catalog_product_id IS NOT NULL "
        "GROUP BY m.sku HAVING cats > 1 ORDER BY cats DESC LIMIT 1")
    if not fila:
        print('No hay ningun SKU en varios catalogos. Abortado.')
        return 1
    sku = fila['sku']

    esperado = Counter()
    for r in A.query_db(
            "SELECT c.catalog_product_id cat, COUNT(*) n FROM sku_mla_mapeo m "
            "JOIN mla_catalogo c ON c.mla_id = m.mla_id WHERE m.activo = TRUE "
            "AND m.sku = %s AND c.catalog_product_id IS NOT NULL "
            "GROUP BY c.catalog_product_id", (sku,)):
        esperado[r['cat']] = int(r['n'])
    print(f'SKU de prueba: {sku} — {len(esperado)} catalogos: '
          f'{", ".join(f"{c}({n})" for c, n in esperado.most_common())}')

    r = cli.get(f'/buscar-sku-ml?sku_buscar={sku}')
    chequear(r.status_code == 200, 'la pantalla responde 200', str(r.status_code))
    h = r.get_data(as_text=True)

    print('el badge dice el numero de catalogo')
    for cat in esperado:
        chequear(f'/p/{cat}' in h, f'el badge linkea al catalogo {cat}')
    chequear('bi-bookmark-star-fill"></i>\n                                        CATÁLOGO'
             not in h, 'ya no dice solo "CATÁLOGO" sin numero')

    print('el selector')
    chequear('btn-filtro-cat' in h, 'aparece el selector de catalogo')
    chequear('Este SKU compite en' in h, 'avisa que compite en varios catalogos')
    for cat, n in esperado.items():
        chequear(f'data-cat="{cat}"' in h, f'hay boton para {cat}')
        chequear(f'{cat} ({n})' in h, f'el boton de {cat} dice {n} publi(s)')
    chequear('data-cat=""' in h, 'hay boton "Todas"')

    print('las filas y tarjetas quedan marcadas con su catalogo')
    en_filas = Counter(re.findall(r'<tr data-status-raw[^>]*?data-catalogo="(MLA\d+)"', h,
                                  re.S))
    chequear(en_filas == esperado, 'cada fila de la tabla trae su catalogo',
             f'{dict(en_filas)}')
    tarjetas = Counter(re.findall(r'card mb-2 shadow-sm"\s*\n\s*data-catalogo="(MLA\d+)"', h))
    chequear(tarjetas == esperado, 'cada tarjeta mobile trae su catalogo',
             f'{dict(tarjetas)}')
    sin_cat = len(re.findall(r'data-catalogo=""', h))
    chequear(sin_cat % 2 == 0,
             'las publis sin catalogo quedan con el atributo vacio en ambas vistas',
             f'{sin_cat} apariciones')
    if sin_cat:
        chequear('data-cat="__sin__"' in h, 'hay boton "Sin catalogo"')

    print('un SKU en un solo catalogo no muestra el selector')
    solo = A.query_one(
        "SELECT m.sku FROM sku_mla_mapeo m JOIN mla_catalogo c ON c.mla_id = m.mla_id "
        "WHERE m.activo = TRUE AND c.catalog_product_id IS NOT NULL "
        "GROUP BY m.sku HAVING COUNT(DISTINCT c.catalog_product_id) = 1 "
        "AND SUM(c.catalog_product_id IS NULL) = 0 LIMIT 1")
    if solo:
        h2 = cli.get(f'/buscar-sku-ml?sku_buscar={solo["sku"]}').get_data(as_text=True)
        tiene_generales = 'data-catalogo=""' in h2
        chequear(('btn-filtro-cat' in h2) == tiene_generales,
                 f'{solo["sku"]}: el selector aparece solo si hay publis fuera de catalogo',
                 f'generales={tiene_generales}')

    print()
    print('RESULTADO:', 'el selector de catalogo funciona' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
