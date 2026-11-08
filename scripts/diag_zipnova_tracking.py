#!/usr/bin/env python3
"""Qué información de seguimiento da la API de Zipnova sobre nuestros envíos (solo GET).
Lista los últimos envíos de la cuenta y, para algunos, el detalle y el historial
(/shipments/{id}/tracking). NO descarga etiquetas (eso puede cambiar el estado).

Uso: venv/bin/python scripts/diag_zipnova_tracking.py [cantidad_detalle] [--crudo]
"""
import json
import os
import sys
from collections import Counter

import requests
from dotenv import load_dotenv

load_dotenv('/home/cannon/app/config/.env')
BASE = 'https://api.zipnova.com.ar/v2'
AUTH = (os.getenv('ZIPNOVA_API_KEY', ''), os.getenv('ZIPNOVA_API_SECRET', ''))
ACC = os.getenv('ZIPNOVA_ACCOUNT_ID', '5786')
n_det = int(next((a for a in sys.argv[1:] if a.isdigit()), '4'))
crudo = '--crudo' in sys.argv
H = {'Accept': 'application/json'}


def get(path, params=None):
    r = requests.get(BASE + path, auth=AUTH, headers=H, params=params, timeout=30)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, r.text[:300]


sc, lst = get('/shipments', {'account_id': ACC})
print('GET /shipments →', sc)
envios = (lst.get('data') if isinstance(lst, dict) else lst) or []
print(f'{len(envios)} envíos en la primera página')
estados = Counter((e.get('status'), e.get('substatus_code')) for e in envios)
canales = Counter(((e.get('order') or {}).get('channel') if isinstance(e.get('order'), dict) else None) for e in envios)
print('status/substatus:', dict(estados))
print('canal de la orden:', dict(canales))
for e in envios[:n_det]:
    sid = e.get('id')
    sc, d = get(f'/shipments/{sid}')
    d = d if isinstance(d, dict) else {}
    d = d.get('data', d)
    print(f"\n--- envío {sid} ext={d.get('external_id')} status={d.get('status')}/{d.get('substatus_code')} "
          f"({d.get('status_name')} / {d.get('substatus_name')})")
    print('   carrier:', (d.get('carrier') or {}).get('name'), '| carrier_tracking_id:', d.get('carrier_tracking_id'),
          '| delivery_id:', d.get('delivery_id'))
    print('   tracking:', d.get('tracking'), '| tracking_external:', d.get('tracking_external'))
    print('   estimada:', (d.get('delivery_time') or {}).get('estimated_delivery'), '| entregado:', d.get('delivered_at'),
          '| último estado:', d.get('last_status_at'))
    print('   claves del detalle:', sorted(d.keys()))
    sc, t = get(f'/shipments/{sid}/tracking', {'sort': 'oldest'})
    evs = (t.get('data') if isinstance(t, dict) else t) or []
    print(f'   historial ({sc}):')
    for ev in evs if isinstance(evs, list) else []:
        st = ev.get('status') or {}
        print(f"      {str(ev.get('occurred_at'))[:16]}  {st.get('code')}/{st.get('substatus_code')}  {st.get('visible_name') or st.get('name')}")
    if crudo:
        print(json.dumps(d, ensure_ascii=False, indent=1, default=str)[:3000])
sc, wh = get(f'/accounts/{ACC}/webhooks')
print('\nwebhooks configurados:', sc, json.dumps(wh, ensure_ascii=False)[:500])
