#!/usr/bin/env python3
"""Aplica un archivo de migrations/ a la base de PRODUCCIÓN (escribe: pide autorización).

Uso: venv/bin/python scripts/aplicar_migracion.py migrations/017_recupero_carritos.sql

Ejecuta cada sentencia del archivo (separadas por ';'), ignorando comentarios.
Sin la contraseña en la línea de comandos: la lee de config/.env.
"""
import os
import re
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv('/home/cannon/app/config/.env')
if len(sys.argv) != 2 or not sys.argv[1].endswith('.sql'):
    print(__doc__)
    sys.exit(2)
sql = open(sys.argv[1], encoding='utf-8').read()
sql = re.sub(r'^\s*--.*$', '', sql, flags=re.M)
sentencias = [s.strip() for s in sql.split(';') if s.strip()]

conn = pymysql.connect(host=os.getenv('DB_HOST', 'localhost'), port=int(os.getenv('DB_PORT', '3306')),
                       user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'),
                       database=os.getenv('DB_NAME'), charset='utf8mb4', autocommit=True)
with conn.cursor() as cur:
    for s in sentencias:
        cur.execute(s)
        print('OK:', ' '.join(s.split())[:90])
conn.close()
