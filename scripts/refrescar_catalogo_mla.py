#!/usr/bin/env python3
"""Refresca a mano el indice mla_catalogo (que publi nuestra esta en que catalogo).

La logica vive en app.refrescar_catalogo_mla, que es la misma que corre el job
diario de las 6:40 AR: aca solo se la dispara y se muestra el resultado. Sirve
para no esperar al job despues de publicar o mover publicaciones.

    scripts/refrescar_catalogo_mla.py
"""
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
os.environ.setdefault('CANNON_SIN_SCHEDULER', '1')


def main():
    import app as A

    consultadas, escritas, de_catalogo, fallidas = A.refrescar_catalogo_mla()
    print(f'consultadas ... {consultadas}')
    print(f'escritas ...... {escritas}')
    print(f'de catalogo ... {de_catalogo}')
    print(f'fallidas ...... {fallidas}')

    n = A.query_one("SELECT COUNT(*) c FROM mla_catalogo WHERE catalog_product_id IS NOT NULL")
    d = A.query_one("SELECT COUNT(DISTINCT catalog_product_id) c FROM mla_catalogo "
                    "WHERE catalog_product_id IS NOT NULL")
    print(f'en el indice .. {n["c"]} publis de catalogo, {d["c"]} catalogos distintos')
    return 0


if __name__ == '__main__':
    sys.exit(main())
