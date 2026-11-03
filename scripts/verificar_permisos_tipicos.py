#!/usr/bin/env python3
"""Chequea que los comandos del dia a dia no pidan autorizacion.

Es la contraparte de verificar_permisos.py: en vez de medir una sesion pasada,
toma la lista de comandos que se usan en una tarea normal y verifica que la
allowlist los cubra, y que los dos unicos que SI deben pedir permiso (escribir
en la base y reiniciar) sigan pidiendolo.

Si manana alguien toca .claude/settings.local.json y rompe un patron, esto lo
caza. Solo lee archivos.
"""
import json
import re
import sys
from fnmatch import fnmatch

SETTINGS = '/home/cannon/app/.claude/settings.local.json'

# Lo que tiene que pasar de largo
DEBEN_PASAR = [
    'venv/bin/python scripts/q.py "SELECT 1"',
    'venv/bin/python3 scripts/q.py "SELECT 1"',
    'venv/bin/python scripts/ml.py /items/MLA123',
    'venv/bin/python scripts/dump.py ventas',
    'venv/bin/python -m py_compile app.py',
    'venv/bin/python3 -m py_compile app.py tienda_bp.py',
    'venv/bin/python scripts/probar_busqueda_catalogo.py',
    'venv/bin/python scripts/auditar_catalogo_map.py',
    'venv/bin/python scripts/verificar_permisos.py',
    'venv/bin/python scripts/validar_feed_meta.py',
    'venv/bin/python scripts/diag_clearsale.py 25524',
    'CANNON_SIN_SCHEDULER=1 venv/bin/python scripts/generar_mapas.py',
    'cp -a app.py "backups/app.py_20261103_204044.bak"',
    'git --no-pager diff app.py',
    'git add app.py templates/home.html',
    'git commit -q -m "x"',
    'git push -q',
    'git log -3 --format=%h',
    'grep -n "def buscar" app.py',
    'sed -n "100,120p" app.py',
    'systemctl is-active cannon',
    'journalctl -u cannon --since -2min --no-pager',
    'curl -s -o /dev/null -w "%{http_code}" https://www.mercadomuebles.com.ar/tienda/',
    'echo',
    'head',
    'ls -t backups/',
    'awk -v d="[03/Nov" "$4 > d" /var/log/nginx/access.log',
]

# Lo que tiene que pedir autorizacion
DEBEN_PEDIR = [
    'mysql inventario_cannon -e "UPDATE ventas SET estado_entrega=\'cancelada\' WHERE id=1"',
    'mysql inventario_cannon < migrations/014_mla_catalogo.sql',
    'systemctl restart cannon',
    'systemctl stop cannon',
    'rm -rf static/img/catalogo',
    'sed -i "s/a/b/" app.py',
    'tee app.py',
    'venv/bin/python scripts/reenviar_clearsale.py PW-1 --aplicar',
    'venv/bin/python scripts/promos_aporte.py 4 --ejecutar',
    'venv/bin/pip install requests',
]

fallos = []


def main():
    cfg = json.load(open(SETTINGS))

    def pats(clave):
        return [re.match(r'^Bash\((.*)\)$', p).group(1)
                for p in cfg['permissions'].get(clave, []) if p.startswith('Bash(')]

    allow, ask = pats('allow'), pats('ask')

    def permitido(cmd):
        trozos = [t.strip() for t in re.split(r'&&|\|\||;|\|', cmd) if t.strip()]
        for t in trozos:
            if any(fnmatch(t, p) for p in ask):
                return False
            if not any(fnmatch(t, p) for p in allow):
                return False
        return True

    print('tienen que pasar sin preguntar:')
    for c in DEBEN_PASAR:
        ok = permitido(c)
        print(f'  {"OK   " if ok else "PIDE "} {c[:88]}')
        if not ok:
            fallos.append(c)

    print()
    print('tienen que pedir autorizacion:')
    for c in DEBEN_PEDIR:
        pide = not permitido(c)
        print(f'  {"OK   " if pide else "PASA "} {c[:88]}')
        if not pide:
            fallos.append(c)

    print()
    if fallos:
        print(f'HAY {len(fallos)} CASOS MAL:')
        for f in fallos:
            print(f'  {f[:100]}')
        return 1
    print('RESULTADO: la allowlist esta como se acordo')
    return 0


if __name__ == '__main__':
    sys.exit(main())
