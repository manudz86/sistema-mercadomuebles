#!/usr/bin/env python3
"""Chequeo de sintaxis de templates Jinja2 (solo parseo, no renderiza).

Uso:
    venv/bin/python3 scripts/check_jinja.py templates/tienda/home.html [...]
    venv/bin/python3 scripts/check_jinja.py            # todos los .html de templates/

Sale con codigo 1 si algun template no parsea.
"""
import sys
import os

from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def listar_todos():
    encontrados = []
    for raiz, _dirs, archivos in os.walk(os.path.join(BASE, 'templates')):
        for a in archivos:
            if a.endswith('.html'):
                encontrados.append(os.path.join(raiz, a))
    return sorted(encontrados)


def main():
    rutas = sys.argv[1:] or listar_todos()
    env = Environment(loader=FileSystemLoader(os.path.join(BASE, 'templates')))
    errores = 0
    for ruta in rutas:
        ruta_abs = ruta if os.path.isabs(ruta) else os.path.join(BASE, ruta)
        nombre = os.path.relpath(ruta_abs, BASE)
        try:
            with open(ruta_abs, encoding='utf-8') as fh:
                env.parse(fh.read(), filename=ruta_abs)
        except TemplateSyntaxError as e:
            errores += 1
            print(f"ERROR  {nombre}:{e.lineno}  {e.message}")
        except OSError as e:
            errores += 1
            print(f"ERROR  {nombre}  no se pudo leer: {e}")
        else:
            print(f"OK     {nombre}")
    print(f"\n{len(rutas)} template(s), {errores} con error")
    return 1 if errores else 0


if __name__ == '__main__':
    sys.exit(main())
