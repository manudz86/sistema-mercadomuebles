#!/usr/bin/env python3
"""Lista los jobs del scheduler y dice cuales tienen lock entre workers.

Los 5 workers de gunicorn arrancan cada uno su scheduler, asi que un job sin
GET_LOCK corre 5 veces en paralelo. Segun que haga, eso es ruido en el log,
trabajo duplicado o datos repetidos.

Solo lectura (analiza el codigo, no ejecuta nada).

Uso:  venv/bin/python3 scripts/check_jobs_lock.py
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVOS = ['app.py', 'competencia_v2_bp.py', 'competencia_bp.py']


def cuerpo_funcion(src, nombre):
    """Texto de la funcion `nombre` hasta el proximo def/decorador de nivel 0."""
    m = re.search(rf'^def {re.escape(nombre)}\(', src, re.M)
    if not m:
        return ''
    resto = src[m.start():]
    sig = re.search(r'\n(?=@|def )', resto[1:])
    return resto[:sig.start() + 1] if sig else resto


def main():
    agendados = []
    for arch in ARCHIVOS:
        p = os.path.join(BASE, arch)
        if not os.path.exists(p):
            continue
        src = open(p, encoding='utf-8').read()
        for m in re.finditer(r'add_job\(\s*([A-Za-z_][A-Za-z_0-9.]*)', src):
            agendados.append((arch, m.group(1)))

    print(f'{"job":<34} {"archivo":<22} lock')
    print('-' * 68)
    vistos = set()
    sin = []
    for arch, fn in sorted(set(agendados)):
        if fn in vistos:
            continue
        vistos.add(fn)
        cuerpo = ''
        for a in ARCHIVOS:
            p = os.path.join(BASE, a)
            if os.path.exists(p):
                cuerpo = cuerpo_funcion(open(p, encoding='utf-8').read(), fn.split('.')[-1])
                if cuerpo:
                    arch = a
                    break
        tiene = '_adquirir_lock' in cuerpo
        print(f'{fn:<34} {arch:<22} {"SI" if tiene else "-- NO --"}')
        if not tiene and cuerpo:
            sin.append(fn)

    if sin:
        print(f'\n{len(sin)} job(s) sin lock: {", ".join(sin)}')
        print('Corren 5 veces (una por worker). Revisar si eso importa en cada caso.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
