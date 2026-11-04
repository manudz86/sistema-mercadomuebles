#!/usr/bin/env python3
"""Verifica que el monitor de competencia soporte varios catalogos por SKU.

Chequea las tres piezas:

  - la tabla acepta el mismo SKU con dos catalogos (clave (sku, catalogo))
  - _get_catalogos devuelve TODOS los catalogos del SKU
  - correr_agente recorre un snapshot por par (SKU, catalogo), con el delay
    largo entre SKU y el corto entre catalogos del mismo SKU
  - quitar un catalogo no se lleva los otros del mismo SKU

Para no pegarle a ML ni escribir snapshots, se intercepta _snapshot_catalogo.
Las filas de prueba usan un SKU ZZ-TEST y se borran al final.
"""
import sys
import time

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
import os                                    # noqa: E402
os.environ['CANNON_SIN_SCHEDULER'] = '1'

SKU = 'ZZTESTMULTI'
CAT_A, CAT_B = 'MLA99000001', 'MLA99000002'

fallos = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


def main():
    import app as A
    import competencia_bp as C

    def limpiar():
        A.execute_db("DELETE FROM sku_catalog_map WHERE sku=%s", (SKU,))

    limpiar()
    try:
        print('la tabla acepta el mismo SKU con dos catalogos')
        for cat in (CAT_A, CAT_B):
            A.execute_db("INSERT INTO sku_catalog_map (sku, catalog_product_id, manual) "
                         "VALUES (%s,%s,1) ON DUPLICATE KEY UPDATE manual=1", (SKU, cat))
        n = A.query_one("SELECT COUNT(*) c FROM sku_catalog_map WHERE sku=%s", (SKU,))['c']
        chequear(n == 2, 'quedan las dos filas', f'{n} fila(s)')

        print('_get_catalogos devuelve los dos')
        cats = C._get_catalogos(SKU)
        chequear(sorted(cats) == [CAT_A, CAT_B], 'devuelve ambos catalogos', str(cats))

        print('correr_agente hace un snapshot por par (SKU, catalogo)')
        visitados = []
        real_snap = C._snapshot_catalogo
        real_lista = C._get_skus_monitorear
        C._snapshot_catalogo = lambda sku, cat: (visitados.append((sku, cat)), 3)[1]
        C._get_skus_monitorear = lambda: [SKU]
        try:
            t0 = time.time()
            r = C.correr_agente(delay_entre_skus=0, delay_entre_catalogos=0)
            tardo = time.time() - t0
        finally:
            C._snapshot_catalogo = real_snap
            C._get_skus_monitorear = real_lista
        chequear(sorted(visitados) == [(SKU, CAT_A), (SKU, CAT_B)],
                 'visita los dos catalogos', str(visitados))
        chequear(r.get('procesados') == 2, 'cuenta 2 procesados', str(r.get('procesados')))
        chequear(r.get('total_rows') == 6, 'suma las filas de los dos', str(r.get('total_rows')))
        chequear(not r.get('errores'), 'sin errores', str(r.get('errores')))
        chequear(tardo < 5, 'con delay 0 no espera', f'{tardo:.1f}s')

        print('el delay corto corre entre catalogos del mismo SKU')
        visitados.clear()
        C._snapshot_catalogo = lambda sku, cat: (visitados.append((sku, cat)), 1)[1]
        C._get_skus_monitorear = lambda: [SKU]
        try:
            t0 = time.time()
            C.correr_agente(delay_entre_skus=0, delay_entre_catalogos=2)
            tardo = time.time() - t0
        finally:
            C._snapshot_catalogo = real_snap
            C._get_skus_monitorear = real_lista
        chequear(1.5 < tardo < 6, 'espera una sola vez entre los dos catalogos',
                 f'{tardo:.1f}s (esperado ~2s)')

        print('quitar un catalogo deja el otro')
        app = C.competencia_bp
        import flask
        fl = flask.Flask(__name__)
        fl.register_blueprint(app)
        with fl.test_request_context(
                '/admin/competencia/catalogo/quitar', method='POST',
                json={'sku': SKU, 'catalog': CAT_A}):
            resp = C.competencia_catalogo_quitar()
        ok_json = resp.get_json() if hasattr(resp, 'get_json') else resp
        chequear(bool(ok_json.get('ok')), 'el endpoint responde ok', str(ok_json))
        quedan = [r['catalog_product_id'] for r in A.query_db(
            "SELECT catalog_product_id FROM sku_catalog_map WHERE sku=%s", (SKU,))]
        chequear(quedan == [CAT_B], 'queda solo el otro catalogo', str(quedan))
    finally:
        limpiar()
        n = A.query_one("SELECT COUNT(*) c FROM sku_catalog_map WHERE sku=%s", (SKU,))['c']
        print(f'filas de prueba borradas: quedan {n}')

    print()
    print('RESULTADO:', 'el multi-catalogo funciona' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
