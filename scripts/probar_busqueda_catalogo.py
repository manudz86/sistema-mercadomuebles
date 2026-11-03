#!/usr/bin/env python3
"""Verifica la busqueda por MLA de catalogo en Modificar Publis ML.

Casos:
  - MLA de catalogo propio: trae nuestras publis de ESE catalogo, pausadas
    incluidas, y no mezcla las de listado general del mismo SKU
  - SKU normal: sigue funcionando igual que antes
  - MLA de una publi propia: sigue funcionando igual que antes
  - MLA inventado: no revienta
  - el indice mla_catalogo se actualiza solo al buscar
  - GET y POST dan el mismo resultado (el link desde competencia usa GET)

Hace GETs a ML (los que haria la pantalla) y escribe en mla_catalogo, que es un
indice reconstruible. No toca publicaciones ni precios.
"""
import os
import re
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


def mlas_en_tabla(html):
    """Los MLA que la pagina lista como publicaciones (los de la columna/forms)."""
    return sorted(set(re.findall(r'MLA\d{8,}', html)))


def main():
    import app as A

    A.app.config['LOGIN_DISABLED'] = True
    import werkzeug
    if not hasattr(werkzeug, '__version__'):
        werkzeug.__version__ = 'prueba'
    cli = A.app.test_client()

    # Un catalogo nuestro con publis pausadas, para probar lo que la API de ML
    # sola no podria devolver
    fila = A.query_one(
        "SELECT catalog_product_id, COUNT(*) n, SUM(status='paused') pausadas "
        "FROM mla_catalogo WHERE catalog_product_id IS NOT NULL "
        "GROUP BY catalog_product_id HAVING pausadas > 0 ORDER BY n DESC LIMIT 1")
    if not fila:
        print('No hay en el indice un catalogo con publis pausadas. Abortado.')
        return 1
    cat = fila['catalog_product_id']
    esperados = sorted(r['mla_id'] for r in A.query_db(
        "SELECT mla_id FROM mla_catalogo WHERE catalog_product_id = %s", (cat,)))
    skus = sorted(r['sku'] for r in A.query_db(
        "SELECT DISTINCT sku FROM sku_mla_mapeo WHERE activo = TRUE AND mla_id IN "
        f"({','.join(['%s'] * len(esperados))})", tuple(esperados)))
    print(f'catalogo de prueba: {cat} — {fila["n"]} publis ({fila["pausadas"]} pausadas), '
          f'SKU {", ".join(skus)}')

    print('busqueda por MLA de catalogo')
    r = cli.get(f'/buscar-sku-ml?sku_buscar={cat}')
    chequear(r.status_code == 200, 'responde 200', str(r.status_code))
    h = r.get_data(as_text=True)
    listados = [m for m in mlas_en_tabla(h) if m in esperados]
    chequear(sorted(listados) == esperados,
             'lista exactamente las publis de ese catalogo',
             f'{len(listados)}/{len(esperados)}')
    chequear(f'Catálogo {cat}' in h, 'muestra el badge del catalogo')
    chequear('Pausada' in h, 'incluye las pausadas (la API de ML no las da)')

    # Ninguna publi de listado general del mismo SKU se tiene que colar
    generales = [r2['mla_id'] for r2 in A.query_db(
        "SELECT mla_id FROM mla_catalogo WHERE catalog_product_id IS NULL AND mla_id IN "
        "(SELECT mla_id FROM sku_mla_mapeo WHERE activo = TRUE AND sku IN "
        f"({','.join(['%s'] * len(skus))}))", tuple(skus))]
    coladas = [m for m in generales if m in mlas_en_tabla(h)]
    chequear(not coladas, 'no se cuelan las publis de listado general',
             f'{len(generales)} generales, coladas: {coladas[:4]}')

    print('GET y POST dan lo mismo (el link de competencia usa GET)')
    rp = cli.post('/buscar-sku-ml', data={'sku_buscar': cat})
    hp = rp.get_data(as_text=True)
    chequear(rp.status_code == 200, 'el POST sigue respondiendo 200', str(rp.status_code))
    chequear([m for m in mlas_en_tabla(hp) if m in esperados] == listados,
             'misma lista por POST que por GET')

    print('un SKU normal no cambia')
    sku = skus[0]
    rs = cli.get(f'/buscar-sku-ml?sku_buscar={sku}')
    hs = rs.get_data(as_text=True)
    todas = sorted(r2['mla_id'] for r2 in A.query_db(
        "SELECT mla_id FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE", (sku,)))
    chequear(rs.status_code == 200, 'responde 200', str(rs.status_code))
    chequear(all(m in mlas_en_tabla(hs) for m in todas),
             f'trae las {len(todas)} publis del SKU, de catalogo y generales',
             f'{len([m for m in todas if m in mlas_en_tabla(hs)])}/{len(todas)}')
    chequear(f'Catálogo {cat}' not in hs, 'y no se marca como busqueda por catalogo')

    print('un MLA de publi propia no cambia')
    propio = esperados[0]
    rm = cli.get(f'/buscar-sku-ml?sku_buscar={propio}')
    hm = rm.get_data(as_text=True)
    chequear(rm.status_code == 200, 'responde 200', str(rm.status_code))
    chequear(propio in mlas_en_tabla(hm), 'muestra esa publicacion')
    chequear('Catálogo' not in hm.split('Resultados para')[1][:400] if 'Resultados para' in hm else True,
             'no la confunde con un catalogo')

    print('un MLA inventado no revienta')
    ri = cli.get('/buscar-sku-ml?sku_buscar=MLA99999999999', follow_redirects=True)
    chequear(ri.status_code == 200, 'responde 200 igual', str(ri.status_code))

    print('el indice se mantiene solo al buscar')
    antes = A.query_one("SELECT COUNT(*) c FROM mla_catalogo")['c']
    A.query_db("SELECT 1")
    cli.get(f'/buscar-sku-ml?sku_buscar={sku}')
    fresco = A.query_one(
        "SELECT COUNT(*) c FROM mla_catalogo WHERE mla_id IN "
        f"({','.join(['%s'] * len(todas))}) AND actualizado_at >= NOW() - INTERVAL 2 MINUTE",
        tuple(todas))['c']
    chequear(fresco >= 1, 'la busqueda refresco las filas de esas publis',
             f'{fresco}/{len(todas)} frescas')
    chequear(A.query_one("SELECT COUNT(*) c FROM mla_catalogo")['c'] >= antes,
             'y no borro nada del indice')

    print()
    print('RESULTADO:', 'la busqueda por catalogo funciona' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
