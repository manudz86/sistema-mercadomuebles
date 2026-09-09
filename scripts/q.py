#!/usr/bin/env python3
"""Consultas SQL de SOLO LECTURA a la base del sistema.

Uso:
    venv/bin/python3 scripts/q.py "SELECT ... FROM ventas WHERE ..."
    venv/bin/python3 scripts/q.py --json "SELECT ..."
    venv/bin/python3 scripts/q.py --tabla ventas          # describe una tabla
    venv/bin/python3 scripts/q.py --tablas                # lista las tablas

Doble candado (a propósito):
  1) se conecta con el usuario de solo lectura (DB_RO_USER), que no tiene permiso
     de escritura en MySQL;
  2) además rechaza cualquier sentencia que no sea SELECT/SHOW/DESCRIBE/EXPLAIN.
Para escribir en producción se usa el flujo normal, que pide autorización.
"""
import sys
import json as _json

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from _common import conectar_db, imprimir_tabla  # noqa: E402

PERMITIDAS = ('select', 'show', 'describe', 'desc', 'explain', 'with')


def es_lectura(sql):
    """True solo si la sentencia es de lectura y es UNA sola sentencia."""
    limpio = sql.strip().rstrip(';').strip()
    if not limpio:
        return False, 'consulta vacía'
    # una sola sentencia (evita "SELECT 1; DELETE ...")
    if ';' in limpio:
        return False, 'no se permite más de una sentencia'
    primera = limpio.split(None, 1)[0].lower()
    if primera not in PERMITIDAS:
        return False, f'solo lectura: "{primera.upper()}" no está permitido'
    # palabras de escritura en cualquier parte (por si van dentro de un CTE)
    bajo = limpio.lower()
    for mala in (' insert ', ' update ', ' delete ', ' drop ', ' alter ',
                 ' truncate ', ' grant ', ' create ', ' replace '):
        if mala in f' {bajo} ':
            return False, f'la consulta contiene "{mala.strip().upper()}"'
    return True, ''


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    salida_json = False
    if args[0] == '--json':
        salida_json = True
        args = args[1:]
    if not args:
        print('Falta la consulta.')
        return 1

    if args[0] == '--tablas':
        sql = "SHOW TABLES"
    elif args[0] == '--tabla':
        if len(args) < 2:
            print('Uso: --tabla <nombre>')
            return 1
        sql = f"DESCRIBE `{args[1]}`"
    else:
        sql = ' '.join(args)

    ok, motivo = es_lectura(sql)
    if not ok:
        print(f'❌ Rechazado ({motivo}).')
        print('   Este script es solo de lectura. Para escribir, usá el flujo normal.')
        return 2

    db = conectar_db(solo_lectura=True)
    try:
        cur = db.cursor()
        cur.execute(sql)
        filas = cur.fetchall()
        cur.close()
    finally:
        db.close()

    if salida_json:
        print(_json.dumps(filas, ensure_ascii=False, default=str, indent=2))
    else:
        imprimir_tabla(filas)
    return 0


if __name__ == '__main__':
    sys.exit(main())
