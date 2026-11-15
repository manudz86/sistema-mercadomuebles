#!/usr/bin/env python3
"""Lista todas las rutas registradas (endpoint, métodos, path), ordenadas por path. Solo lectura.

Uso: venv/bin/python scripts/generar_lista_rutas.py [archivo_salida]
"""
import os
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import werkzeug  # noqa: E402
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3'
import app as A  # noqa: E402

lineas = []
for r in sorted(A.app.url_map.iter_rules(), key=lambda r: r.rule):
    m = ','.join(sorted(x for x in r.methods if x not in ('HEAD', 'OPTIONS')))
    lineas.append(f"{r.rule}\t{m}\t{r.endpoint}")
salida = '\n'.join(lineas)
if len(sys.argv) > 1:
    with open(sys.argv[1], 'w') as f:
        f.write(salida + '\n')
    print(f'{len(lineas)} rutas → {sys.argv[1]}')
else:
    print(salida)
