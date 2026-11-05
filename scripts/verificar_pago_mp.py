#!/usr/bin/env python3
"""Consulta (solo GET) el estado de pagos de Mercado Pago por id.

Uso: venv/bin/python scripts/verificar_pago_mp.py <payment_id> [<payment_id> ...]
"""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv('/home/cannon/app/config/.env')
tok = os.getenv('MP_ACCESS_TOKEN', '')
if not tok or len(sys.argv) < 2:
    print(__doc__ if len(sys.argv) < 2 else 'Falta MP_ACCESS_TOKEN')
    sys.exit(2)

for pid in sys.argv[1:]:
    r = requests.get(f'https://api.mercadopago.com/v1/payments/{pid}',
                     headers={'Authorization': f'Bearer {tok}'}, timeout=30)
    if r.status_code != 200:
        print(pid, 'HTTP', r.status_code, r.text[:120])
        continue
    p = r.json()
    print(pid, p.get('status'), p.get('status_detail'), p.get('transaction_amount'),
          p.get('date_created', '')[:19], 'ref=', p.get('external_reference'),
          'desc=', (p.get('description') or '')[:40])
