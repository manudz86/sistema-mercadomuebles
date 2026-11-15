#!/usr/bin/env python3
"""Muestra líneas de código con posibles secretos, ENMASCARANDO los literales.

Uso:
  venv/bin/python scripts/auditar_secretos.py archivo.py[:linea[-linea]] ...
  venv/bin/python scripts/auditar_secretos.py --buscar archivo.py ...   (busca password/token/secret/key)

Los strings entre comillas se reemplazan por <str len=N> salvo nombres de variables
de entorno (MAYUSCULAS_CON_GUION) y textos cortos (<=4). Nunca imprime valores.
"""
import re
import sys

LIT = re.compile(r"""(?P<q>['"])(?P<s>(?:\\.|(?!(?P=q)).)*)(?P=q)""")
PISTAS = re.compile(r'passw|secret|token|api_key|apikey|clave|pwd|PASSWORD|SECRET|TOKEN|KEY', re.I)


def enmascarar(linea):
    def rep(m):
        s = m.group('s')
        if len(s) <= 4 or re.fullmatch(r'[A-Z][A-Z0-9_]*', s) or re.fullmatch(r'[a-z_]+', s):
            return m.group(0)
        return f'<str len={len(s)}>'
    return LIT.sub(rep, linea)


def main(args):
    buscar = False
    if args and args[0] == '--buscar':
        buscar, args = True, args[1:]
    for a in args:
        arch, _, rango = a.partition(':')
        try:
            lineas = open(arch, encoding='utf-8', errors='replace').read().split('\n')
        except OSError as e:
            print(f'{arch}: {e}')
            continue
        if rango:
            ini, _, fin = rango.partition('-')
            idx = range(int(ini), int(fin or ini) + 1)
        else:
            idx = range(1, len(lineas) + 1)
        for n in idx:
            if n > len(lineas):
                break
            l = lineas[n - 1]
            if buscar and not PISTAS.search(l):
                continue
            print(f'{arch}:{n}: {enmascarar(l.rstrip())}')


if __name__ == '__main__':
    main(sys.argv[1:])
