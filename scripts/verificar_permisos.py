#!/usr/bin/env python3
"""Mide cuantos comandos de una sesion NO matchean la allowlist, y por que.

Sirve para que "estoy pidiendo demasiadas autorizaciones" sea un numero y no una
sensacion. Lee el transcript de la sesion, saca cada comando Bash, lo parte en
sus partes (en un comando compuesto alcanza con que una parte no este permitida
para que pregunte) y lo compara con los patrones de .claude/settings.local.json.

    scripts/verificar_permisos.py                  # la sesion mas reciente
    scripts/verificar_permisos.py <archivo.jsonl>  # una sesion puntual

Ojo con leer el numero: cuenta comandos que NO matchean la allowlist, que es la
cota de arriba. Los permisos que se ven en pantalla son menos, porque Claude Code
recuerda los "si, no preguntes mas" dentro de una misma sesion.

Solo lee archivos. No toca la base ni el codigo.
"""
import glob
import json
import os
import re
import sys
from collections import Counter
from fnmatch import fnmatch

SETTINGS = '/home/cannon/app/.claude/settings.local.json'
SESIONES = '/root/.claude/projects/-home-cannon-app/*.jsonl'


def patrones(cfg, clave):
    out = []
    for p in cfg['permissions'].get(clave, []):
        m = re.match(r'^Bash\((.*)\)$', p)
        if m:
            out.append(m.group(1))
    return out


def partes(cmd):
    """Las sub-invocaciones de un comando compuesto."""
    return [t.strip() for t in re.split(r'&&|\|\||;|\|', cmd) if t.strip()]


def permitido(parte, allow, ask):
    if any(fnmatch(parte, p) for p in ask):
        return False
    return any(fnmatch(parte, p) for p in allow)


def comandos_de(transcript):
    out = []
    with open(transcript) as fh:
        for linea in fh:
            try:
                d = json.loads(linea)
            except Exception:
                continue
            for c in ((d.get('message') or {}).get('content') or []):
                if isinstance(c, dict) and c.get('type') == 'tool_use' \
                        and c.get('name') == 'Bash':
                    cmd = (c.get('input') or {}).get('command')
                    if cmd:
                        out.append(cmd)
    return out


def main():
    arg = [a for a in sys.argv[1:] if not a.startswith('-')]
    if arg:
        transcript = arg[0]
    else:
        archivos = sorted(glob.glob(SESIONES), key=os.path.getmtime, reverse=True)
        if not archivos:
            print('No encontre transcripts en', SESIONES)
            return 1
        transcript = archivos[0]
    print(f'sesion: {os.path.basename(transcript)}')

    cfg = json.load(open(SETTINGS))
    allow, ask = patrones(cfg, 'allow'), patrones(cfg, 'ask')
    print(f'reglas: {len(allow)} allow · {len(ask)} ask')

    comandos = comandos_de(transcript)
    if not comandos:
        print('la sesion no tiene comandos Bash')
        return 0

    pedidos, motivos, ejemplos = 0, Counter(), {}
    for cmd in comandos:
        malas = [p for p in partes(cmd) if not permitido(p, allow, ask)]
        if malas:
            pedidos += 1
            tok = ' '.join(malas[0].split()[:2])
            motivos[tok] += 1
            ejemplos.setdefault(tok, cmd)

    print()
    print(f'comandos Bash .............. {len(comandos)}')
    print(f'no matchean la allowlist ... {pedidos} ({pedidos / len(comandos) * 100:.0f}%)')
    print()
    print('por que (primer tramo no permitido):')
    for k, v in motivos.most_common(20):
        print(f'  {v:>4}  {k}')
        print(f'        ej: {ejemplos[k].splitlines()[0][:100]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
