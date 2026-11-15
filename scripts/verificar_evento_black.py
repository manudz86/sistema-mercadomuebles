#!/usr/bin/env python3
"""Con la configuración REAL de la base (solo lectura): qué muestra el evento hoy y cada día
del 25 al 30/11 (vía get_hot_event(simular)), y que los banners existan.
Uso: venv/bin/python scripts/verificar_evento_black.py
"""
import os
import sys
from datetime import date

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import werkzeug  # noqa: E402
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3'
import app as A  # noqa: E402
import tienda_bp as T  # noqa: E402

with A.app.test_request_context('/tienda/'):
    h = T.get_hot_event()
    print(f"HOY: activo={h['activo']} titulo={h['titulo']} cupon={h['cupon']}")
    for d in range(24, 31):
        h = T.get_hot_event(date(2026, 11, d))
        ok = all(os.path.isfile('/home/cannon/app' + h[k]) for k in ('banner_desktop', 'banner_mobile'))
        print(f"{d}/11 {h['banner_desktop'].rsplit('/', 1)[-1]:<30} archivos={'OK' if ok else 'FALTAN'} "
              f"fechas='{h['fechas']}' 3sin={h['cuotas_3sin']} hasta={h['fecha_fin_iso'][:16]} tema={h['tema']}")
