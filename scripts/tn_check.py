#!/usr/bin/env python3
"""Chequeo de SOLO LECTURA contra la API de Tiendanube.

Sirve para saber si las credenciales guardadas en tiendanube_config siguen
vivas despues de que tiendanube_bp.py se borro (commit a4bab38, 19/04/2026).
No escribe nada, no imprime el token ni el secret: solo estado y conteos.
"""
import os
import sys

import pymysql
import requests
from dotenv import load_dotenv

load_dotenv('/home/cannon/app/config/.env')

TN_API_BASE = 'https://api.tiendanube.com/v1'
TN_CLIENT_ID = os.environ.get('TN_CLIENT_ID', '')


def get_config():
    cn = pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME'),
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with cn.cursor() as cur:
            cur.execute('SELECT * FROM tiendanube_config ORDER BY id DESC LIMIT 1')
            return cur.fetchone()
    finally:
        cn.close()


def main():
    cfg = get_config()
    if not cfg:
        print('No hay fila en tiendanube_config'); return 1

    store_id = cfg.get('store_id')
    token = cfg.get('access_token') or ''
    print(f'store_id        = {store_id}')
    print(f'token           = {"presente" if token else "AUSENTE"} ({len(token)} chars)')
    print(f'TN_CLIENT_ID    = {"presente" if TN_CLIENT_ID else "AUSENTE"}')

    if not (store_id and token):
        print('Faltan credenciales: no se puede consultar'); return 1

    headers = {
        'Authentication': f'bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': f'SistemaCannon/{TN_CLIENT_ID} (manu@cannon.com.ar)',
    }

    # GET de la tienda: el chequeo mas barato de "el token sigue valido"
    for nombre, endpoint, params in (
        ('store', 'store', None),
        ('products (conteo)', 'products', {'per_page': 1}),
    ):
        try:
            r = requests.get(f'{TN_API_BASE}/{store_id}/{endpoint}',
                             headers=headers, params=params, timeout=15)
            extra = ''
            if r.status_code == 200 and endpoint == 'products':
                # Tiendanube pagina en headers
                extra = f" | x-total-count={r.headers.get('x-total-count', '?')}"
            elif r.status_code == 200 and endpoint == 'store':
                try:
                    extra = f" | name={r.json().get('name')}"
                except Exception:
                    pass
            else:
                extra = f' | {r.text[:160]}'
            print(f'{nombre:18} -> HTTP {r.status_code}{extra}')
        except Exception as e:
            print(f'{nombre:18} -> ERROR {type(e).__name__}: {e}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
