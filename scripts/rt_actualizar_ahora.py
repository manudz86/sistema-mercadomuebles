#!/usr/bin/env python3
"""Corre a mano el job diario de Real Trends (competencia_v2_bp.job_actualizar_rt):
baja los días nuevos del período actual + reconciliación de los últimos días.
Escribe data/competencia_v2/{AAAA-MM}/*.json (hacer backup antes).
Uso: venv/bin/python scripts/rt_actualizar_ahora.py
"""
import sys

sys.path.insert(0, '/home/cannon/app')
from dotenv import load_dotenv
load_dotenv('/home/cannon/app/config/.env')

import competencia_v2_bp as c

c.job_actualizar_rt()
print('datos cargados hasta:', c._periodo_max_dia('2026-11') if hasattr(c, '_periodo_max_dia') else '?')
