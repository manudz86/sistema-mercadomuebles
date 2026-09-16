#!/usr/bin/env python3
"""Backup de tablas de la DB a backups/ — sin exponer la contraseña.

CLAUDE.md exige respaldar la tabla antes de cualquier UPDATE/DELETE/INSERT en
producción. Hacerlo a mano obligaba a `set -a; . config/.env` + `mysqldump
-p"$DB_PASSWORD"`, que además deja la contraseña visible en la línea de
comandos (`ps` la muestra, y mysql tira el warning). Acá la credencial viaja
por la variable de entorno MYSQL_PWD, que mysqldump lee sin exponerla.

Uso:
    venv/bin/python3 scripts/dump.py ventas items_venta
    venv/bin/python3 scripts/dump.py --todo
    venv/bin/python3 scripts/dump.py ventas --etiqueta pre-fix-stock

Deja el archivo en backups/dump_<etiqueta>_<YYYYmmdd_HHMMSS>.sql
"""
import os
import sys
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import cargar_env  # noqa: E402

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUPS = os.path.join(APP_DIR, 'backups')


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1

    etiqueta = 'tablas'
    if '--etiqueta' in args:
        i = args.index('--etiqueta')
        try:
            etiqueta = args[i + 1]
        except IndexError:
            print('error: --etiqueta necesita un valor')
            return 1
        del args[i:i + 2]

    todo = '--todo' in args
    if todo:
        args.remove('--todo')
    tablas = args

    if not todo and not tablas:
        print('error: indicá al menos una tabla, o usá --todo')
        return 1

    env = cargar_env()          # devuelve un dict; no toca os.environ
    host = env.get('DB_HOST', 'localhost')
    port = env.get('DB_PORT', '3306')
    user = env.get('DB_USER')
    pwd = env.get('DB_PASSWORD')
    name = env.get('DB_NAME')
    if not (user and pwd and name):
        print('error: faltan DB_USER / DB_PASSWORD / DB_NAME en config/.env')
        return 1

    os.makedirs(BACKUPS, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    if todo:
        etiqueta = 'completo'
    destino = os.path.join(BACKUPS, f'dump_{etiqueta}_{ts}.sql')

    cmd = ['mysqldump', f'-h{host}', f'-P{port}', f'-u{user}',
           '--single-transaction', '--quick', name]
    if not todo:
        cmd += tablas

    entorno = dict(os.environ, MYSQL_PWD=pwd)   # la clave NO va en argv
    try:
        with open(destino, 'wb') as f:
            r = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=entorno)
    except FileNotFoundError:
        print('error: no se encontró el binario mysqldump')
        return 1

    if r.returncode != 0:
        print(f'error de mysqldump: {r.stderr.decode(errors="replace").strip()}')
        if os.path.exists(destino) and os.path.getsize(destino) == 0:
            os.remove(destino)
        return 1

    mb = os.path.getsize(destino) / 1024 / 1024
    objetivo = 'toda la base' if todo else ', '.join(tablas)
    print(f'✅ backup de {objetivo}')
    print(f'   {destino}  ({mb:.1f} MB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
