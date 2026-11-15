#!/usr/bin/env python3
"""Prueba que DB_USER/DB_PASSWORD de config/.env conecten a MySQL. Nunca imprime la contraseña.
Uso: venv/bin/python scripts/check_conexion_db.py
"""
import os
import re

import pymysql
from dotenv import dotenv_values

env = dotenv_values('/home/cannon/app/config/.env')
pw = env.get('DB_PASSWORD') or ''
crudo = [l for l in open('/home/cannon/app/config/.env', encoding='utf-8') if l.startswith('DB_PASSWORD=')]
raros = bool(re.search(r'[\s"#$]', pw))
print(f'líneas DB_PASSWORD: {len(crudo)} | largo: {len(pw)} | caracteres raros: {raros}')
try:
    c = pymysql.connect(host='localhost', user=env.get('DB_USER') or 'cannon', password=pw,
                        db=env.get('DB_NAME') or 'inventario_cannon', connect_timeout=5)
    cur = c.cursor()
    cur.execute('SELECT COUNT(*) FROM usuarios')
    print(f'conexión OK (usuarios={cur.fetchone()[0]})')
    c.close()
except Exception as e:
    print(f'conexión FALLA: {type(e).__name__} {getattr(e, "args", [""])[0]}')
