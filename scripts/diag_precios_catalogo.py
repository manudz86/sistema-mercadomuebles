#!/usr/bin/env python3
"""SOLO LECTURA: compara los campos de precio que da ML para cada vendedor de un catálogo.

/products/{id}/items (lo que usa el monitor) vs /items/{id}/sale_price (precio que se ve
en la web, con descuentos/promos aplicadas).
Uso: venv/bin/python scripts/diag_precios_catalogo.py MLA68660478 [zip]
"""
import sys
import time

import requests

sys.path.insert(0, '/home/cannon/app')
from competencia_bp import _token  # noqa: E402

cat = sys.argv[1]
zip_code = sys.argv[2] if len(sys.argv) > 2 else '1407'
tok = _token()
H = {'Authorization': f'Bearer {tok}'}

r = requests.get(f'https://api.mercadolibre.com/products/{cat}/items', headers=H,
                 params={'zip_code': zip_code, 'limit': 50}, timeout=15)
print('products/items:', r.status_code)
res = r.json().get('results', [])
for it in res:
    iid = it.get('item_id')
    sp = requests.get(f'https://api.mercadolibre.com/items/{iid}/sale_price', headers=H,
                      params={'context': 'channel_marketplace'}, timeout=15)
    spj = sp.json() if sp.ok else {}
    print(f"{iid} seller={it.get('seller_id')} lt={it.get('listing_type_id')} "
          f"price={it.get('price')} original={it.get('original_price')} "
          f"tags={[t for t in it.get('tags', []) if 'campaign' in t or 'funded' in t]}")
    print(f"    sale_price: {sp.status_code} amount={spj.get('amount')} regular={spj.get('regular_amount')} "
          f"promo={ (spj.get('metadata') or {}).get('promotion_type') } "
          f"campaign={(spj.get('metadata') or {}).get('campaign_id')}")
    time.sleep(0.2)
