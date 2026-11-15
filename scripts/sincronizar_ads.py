#!/usr/bin/env python3
"""Sincroniza YA las métricas de Meta/Google Ads desde Windsor (escribe en ads_metricas_diarias y
ads_google_clics). Es lo mismo que el botón "Actualizar datos" de la página. Uso:
  venv/bin/python scripts/sincronizar_ads.py [dias]
"""
import os
import sys

sys.path.insert(0, '/home/cannon/app')
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import ads_bp  # noqa: E402

print(ads_bp.sincronizar(int(sys.argv[1]) if len(sys.argv) > 1 else ads_bp.DIAS_SYNC))
