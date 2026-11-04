#!/usr/bin/env python3
"""Mide cuanto tarda /buscar-sku-ml, que es lo que abre "Mis publis".

El link del monitor de competencia abre una pestaña nueva, y esa pagina consulta
a ML en vivo: datos de cada publicacion, permalinks y promos. En iOS una pestaña
en blanco esperando se ve como si estuviera colgada, asi que lo primero es saber
si tarda o si falla.

Mide el request completo y, aparte, cada llamada a ML por separado.

    scripts/diag_tiempo_busqueda_catalogo.py                 # los catalogos mas grandes
    scripts/diag_tiempo_busqueda_catalogo.py MLA34984270     # uno puntual

Solo GETs. No escribe nada salvo el indice mla_catalogo, que se refresca al buscar.
"""
import os
import sys
import time

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
os.environ['CANNON_SIN_SCHEDULER'] = '1'


def main():
    import app as A

    pedidos = [a for a in sys.argv[1:] if a.startswith('MLA')]
    if not pedidos:
        pedidos = [r['catalog_product_id'] for r in A.query_db(
            "SELECT catalog_product_id, COUNT(*) n FROM mla_catalogo "
            "WHERE catalog_product_id IS NOT NULL GROUP BY catalog_product_id "
            "ORDER BY n DESC LIMIT 3")]

    A.app.config['LOGIN_DISABLED'] = True
    import werkzeug
    if not hasattr(werkzeug, '__version__'):
        werkzeug.__version__ = 'diag'
    cli = A.app.test_client()

    # Contar e instrumentar las llamadas a ML
    llamadas = []
    real = A.ml_request

    def espiar(method, url, *a, **k):
        t0 = time.time()
        r = real(method, url, *a, **k)
        llamadas.append((round(time.time() - t0, 2), url.split('api.mercadolibre.com')[-1][:60]))
        return r

    A.ml_request = espiar
    try:
        for cat in pedidos:
            n = A.query_one("SELECT COUNT(*) c FROM mla_catalogo WHERE "
                            "catalog_product_id=%s", (cat,))['c']
            llamadas.clear()
            t0 = time.time()
            r = cli.get(f'/buscar-sku-ml?sku_buscar={cat}')
            tardo = time.time() - t0
            print(f'{cat}  ({n} publis en el indice)')
            print(f'   HTTP {r.status_code} · {tardo:.1f}s · {len(llamadas)} llamadas a ML')
            lentas = sorted(llamadas, reverse=True)[:5]
            for seg, url in lentas:
                print(f'      {seg:>5.1f}s  {url}')
            suma = sum(s for s, _ in llamadas)
            print(f'   tiempo en ML: {suma:.1f}s de {tardo:.1f}s '
                  f'({suma / tardo * 100:.0f}%)')
            print()
    finally:
        A.ml_request = real
    return 0


if __name__ == '__main__':
    sys.exit(main())
