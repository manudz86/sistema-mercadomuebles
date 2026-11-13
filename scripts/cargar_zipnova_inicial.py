#!/usr/bin/env python3
"""Carga inicial de Zipnova (ESCRIBE en las tablas nuevas de la migración 020):
retiros y resúmenes de los mails de los últimos N días, envíos de Zipnova desde una fecha
(enlazados a ventas) y mensajes ML sin leer. Idempotente: se puede volver a correr.

Uso: venv/bin/python scripts/cargar_zipnova_inicial.py [dias_mail=30] [desde_envios=2026-01-01]
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
import app  # noqa: E402,F401
import zipnova_bp as Z  # noqa: E402

dias = int(sys.argv[1]) if len(sys.argv) > 1 else 30
desde = sys.argv[2] if len(sys.argv) > 2 else '2026-01-01'
print('Mails:', Z._con_lock('mails', 0, lambda: Z.sync_mails(dias=dias)))
print('Envíos:', Z._con_lock('envios', 0, lambda: Z.sync_envios(desde=desde, max_resolver=1000)))
print('Mensajes ML:', Z._con_lock('ml_no_leidos', 0, Z.sync_ml_no_leidos))
