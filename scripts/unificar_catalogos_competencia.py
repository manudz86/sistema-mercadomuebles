#!/usr/bin/env python3
"""Reune en su SKU real los catalogos que estaban con etiquetas inventadas.

Mientras sku_catalog_map admitia un solo catalogo por SKU, la unica forma de
monitorear un segundo catalogo del mismo producto era inventarle un nombre de
SKU: PLATINOX2 / PLATINOX2-TOP / PLATINOX2-VELLON son el mismo SKU con tres
catalogos. Con la clave (sku, catalog_product_id) ya no hace falta.

Hace tres cosas, todas idempotentes:

  1. mueve las etiquetas inventadas al SKU real (cambia el sku de la fila)
  2. saca las filas automaticas que apuntan a un catalogo donde no tenemos
     ninguna publicacion (quedaron viejas; el monitor comparaba contra
     competidores de otro producto)
  3. agrega los catalogos que al SKU le faltan, segun mla_catalogo

Sin --aplicar solo muestra lo que haria.
"""
import sys

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
import os                                    # noqa: E402
os.environ['CANNON_SIN_SCHEDULER'] = '1'

# Etiqueta inventada -> SKU real. Confirmado con el usuario: no existen como
# producto ni tienen publicaciones propias; son catalogos de esos tres SKU.
# (SREP140+ era la etiqueta de un catalogo que venia con almohadas; CPR8020+,
# en cambio, SI es un SKU de publicaciones real y no se toca.)
ETIQUETAS = {
    'CREP1402':         'CREP140',
    'PLATINOX2-TOP':    'PLATINOX2',
    'PLATINOX2-VELLON': 'PLATINOX2',
    'SREP140-2':        'SREP140',
    'SREP140-3':        'SREP140',
    'SREP140+':         'SREP140',
}


def main():
    import app as A

    aplicar = '--aplicar' in sys.argv

    mapa = A.query_db("SELECT sku, catalog_product_id, manual FROM sku_catalog_map "
                      "WHERE catalog_product_id IS NOT NULL AND catalog_product_id <> ''")
    pares = {(r['sku'].strip().upper(), r['catalog_product_id']) for r in mapa}
    manual_de = {(r['sku'].strip().upper(), r['catalog_product_id']): bool(r['manual'])
                 for r in mapa}

    # Donde tiene publicaciones cada SKU, segun el indice de ML
    real = {}
    for r in A.query_db(
            "SELECT m.sku, c.catalog_product_id AS cat, COUNT(*) AS n "
            "FROM sku_mla_mapeo m JOIN mla_catalogo c ON c.mla_id = m.mla_id "
            "WHERE m.activo = TRUE AND c.catalog_product_id IS NOT NULL "
            "  AND c.status IN ('active','paused') "
            "GROUP BY m.sku, c.catalog_product_id"):
        real[(r['sku'].strip().upper(), r['cat'])] = int(r['n'])

    cats_de_sku = {}
    for (sku, cat), n in real.items():
        cats_de_sku.setdefault(sku, {})[cat] = n

    # ── 1. etiquetas a su SKU real
    mover = []
    for etiqueta, destino in ETIQUETAS.items():
        fila = next((p for p in pares if p[0] == etiqueta), None)
        if not fila:
            continue
        cat = fila[1]
        if (destino, cat) in pares:
            mover.append((etiqueta, destino, cat, 'ya existe en el destino: se borra'))
        else:
            mover.append((etiqueta, destino, cat, 'se cambia el sku'))

    # ── 2. filas automaticas apuntando a un catalogo sin publicaciones nuestras
    sacar = []
    for (sku, cat) in sorted(pares):
        if manual_de.get((sku, cat)):
            continue                       # las manuales las decide el usuario
        if sku in ETIQUETAS:
            continue
        if not cats_de_sku.get(sku):
            continue                       # el SKU no tiene publis de catalogo: se deja
        if not real.get((sku, cat)):
            sacar.append((sku, cat))

    # ── 3. catalogos que le faltan a un SKU ya monitoreado
    skus_monitoreados = {s for s, _ in pares} | set(ETIQUETAS.values())
    skus_monitoreados -= set(ETIQUETAS)
    agregar = []
    for sku in sorted(skus_monitoreados):
        for cat, n in sorted(cats_de_sku.get(sku, {}).items(), key=lambda x: -x[1]):
            if (sku, cat) in pares:
                continue
            if any(e for e, d in ETIQUETAS.items() if d == sku and (e, cat) in pares):
                continue                   # va a llegar por el paso 1
            agregar.append((sku, cat, n))

    print(f'[1] etiquetas a reunificar: {len(mover)}')
    for e, d, c, q in sorted(mover):
        print(f'    {e:<17} -> {d:<12} {c:<14} ({q})')
    print()
    print(f'[2] filas automaticas a sacar (catalogo sin publis nuestras): {len(sacar)}')
    for s, c in sacar:
        print(f'    {s:<17}    {c}')
    print()
    print(f'[3] catalogos faltantes a agregar: {len(agregar)}')
    for s, c, n in agregar:
        print(f'    {s:<17}    {c:<14} {n} publi(s)')

    if not aplicar:
        print()
        print('>> Vista previa. Agrega --aplicar para escribirlo.')
        return 0

    conn = A.get_db_connection()
    try:
        with conn.cursor() as cur:
            for e, d, c, q in mover:
                if q.startswith('ya existe'):
                    cur.execute("DELETE FROM sku_catalog_map WHERE sku=%s AND "
                                "catalog_product_id=%s", (e, c))
                else:
                    cur.execute("UPDATE sku_catalog_map SET sku=%s WHERE sku=%s AND "
                                "catalog_product_id=%s", (d, e, c))
            for s, c in sacar:
                cur.execute("DELETE FROM sku_catalog_map WHERE sku=%s AND "
                            "catalog_product_id=%s AND manual=0", (s, c))
            for s, c, n in agregar:
                cur.execute("INSERT INTO sku_catalog_map (sku, catalog_product_id, manual) "
                            "VALUES (%s,%s,0) ON DUPLICATE KEY UPDATE "
                            "actualizado_at=CURRENT_TIMESTAMP", (s, c))
        conn.commit()
    finally:
        conn.close()

    print()
    print('aplicado. estado final de los SKU con varios catalogos:')
    for r in A.query_db(
            "SELECT sku, COUNT(*) n, GROUP_CONCAT(catalog_product_id ORDER BY "
            "catalog_product_id) cuales FROM sku_catalog_map GROUP BY sku "
            "HAVING n > 1 ORDER BY n DESC, sku"):
        print(f'    {r["sku"]:<17} {r["n"]} · {r["cuales"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
