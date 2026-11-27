#!/usr/bin/env python3
"""SOLO LECTURA: prueba el mapeo código de rechazo Payway → motivo público y que
/tienda/pago/error muestre el texto correcto (y que ignore claves desconocidas).
Uso: venv/bin/python scripts/probar_pago_error_motivos.py
"""
import os
import sys

os.environ['CANNON_SIN_SCHEDULER'] = '1'   # importar app sin levantar jobs
sys.path.insert(0, '/home/cannon/app')
from app import app  # noqa: E402
from tienda_bp import _payway_motivo_publico, PAGO_ERROR_MOTIVOS, pago_error  # noqa: E402

casos = {51: 'fondos', 5: 'autorizar', 1: 'autorizar', 45: 'no_habilitada', 56: 'no_habilitada',
         57: 'no_habilitada', 14: 'datos', 53: 'datos', 12: 'datos', 91: 'tecnico', 58: 'tecnico',
         -1: 'tecnico', 12035: 'tecnico', 43: 'generico', 999: 'generico'}
ok = True
for rid, esperado in casos.items():
    got = _payway_motivo_publico({'status_details': {'error': {'reason': {'id': rid}}}})
    ok &= got == esperado
    print(f"{rid:>6} → {got:<14} {'OK' if got == esperado else 'FALLA, esperaba ' + esperado}")
for raro in ({}, {'status_details': None}, {'status_details': {'error': {'reason': {'id': 'x'}}}}):
    got = _payway_motivo_publico(raro)
    ok &= got == 'generico'
    print(f"{str(raro)[:40]:<40} → {got}")

for mot in list(PAGO_ERROR_MOTIVOS) + ['', '<script>x</script>']:
    with app.test_request_context('/tienda/pago/error', query_string={'motivo': mot} if mot else None):
        html = pago_error()
    esperado = PAGO_ERROR_MOTIVOS[mot][0] if mot in PAGO_ERROR_MOTIVOS else 'Podés intentarlo de nuevo'
    bien = esperado in html and '<script>x' not in html
    ok &= bien
    print(f"GET motivo={mot!r:<22} {'OK' if bien else 'FALLA'}")
print('\nTODO OK' if ok else '\nHAY FALLAS')
