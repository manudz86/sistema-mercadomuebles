#!/usr/bin/env python3
"""Prueba que el progreso de sync ML solo lo escriba la corrida con run_id.

No escribe en la base: reemplaza execute_db por una función que anota las
llamadas. Verifica:
  1) sin run_id (ventas / jobs automáticos) no se guarda nada;
  2) con run_id se guarda y el registro lleva ese run_id;
  3) dos hilos simultáneos no se mezclan el run_id;
  4) un hilo reusado (scheduler) no arrastra el run_id de una corrida anterior.
"""
import os
import sys
import json
import threading

sys.path.insert(0, '/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')

import app as A  # noqa: E402

escrituras = []
A.execute_db = lambda sql, params=None: escrituras.append(json.loads(params[0]))

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    if not cond:
        fallas += 1


# 1) sin run_id
A._ML_PROGRESS_CTX.run_id = None
A._ml_progress_save({'running': True, 'done': 0})
check(escrituras == [], 'sin run_id no escribe')

# 2) con run_id
A._ML_PROGRESS_CTX.run_id = 'abc123'
A._ml_progress_save({'running': True, 'done': 1})
check(len(escrituras) == 1 and escrituras[0]['run_id'] == 'abc123', 'con run_id escribe y lo incluye')

# 3) hilos simultáneos
escrituras.clear()
barrera = threading.Barrier(2)


def corrida(rid):
    A._ML_PROGRESS_CTX.run_id = rid
    barrera.wait()
    for i in range(5):
        A._ml_progress_save({'running': True, 'done': i})


hs = [threading.Thread(target=corrida, args=(r,)) for r in ('carga', None)]
[h.start() for h in hs]
[h.join() for h in hs]
check(len(escrituras) == 5 and all(e['run_id'] == 'carga' for e in escrituras),
      'en paralelo solo escribe la corrida con run_id (5 de 5, ninguna de la venta)')

# 4) hilo reusado: la función pública resetea el run_id al arrancar
escrituras.clear()
A._ML_PROGRESS_CTX.run_id = 'vieja'
A.cargar_ml_token = lambda: None          # corta temprano, sin tocar ML
A.query_db = lambda *a, **k: []
A.actualizar_publicaciones_ml_con_progreso({'CEX80'}, run_id=None)
check(escrituras == [], 'corrida automática en hilo reusado no hereda run_id viejo')

print(f'\n{"TODO OK" if not fallas else f"{fallas} FALLA(S)"}')
sys.exit(1 if fallas else 0)
