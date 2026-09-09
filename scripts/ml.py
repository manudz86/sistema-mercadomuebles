#!/usr/bin/env python3
"""Consultas de SOLO LECTURA a la API de Mercado Libre.

Uso:
    venv/bin/python3 scripts/ml.py item MLA123456789
    venv/bin/python3 scripts/ml.py item MLA123 --campos id,price,status,shipping
    venv/bin/python3 scripts/ml.py items MLA1,MLA2,MLA3
    venv/bin/python3 scripts/ml.py catalogo MLA64714379        # producto de catálogo
    venv/bin/python3 scripts/ml.py ofertas MLA64714379         # vendedores del catálogo
    venv/bin/python3 scripts/ml.py promos MLA123456789         # promos de una publi
    venv/bin/python3 scripts/ml.py campanias                   # campañas del vendedor
    venv/bin/python3 scripts/ml.py campania P-MLA123 SMART [--status started]
    venv/bin/python3 scripts/ml.py orden 2000018335540326
    venv/bin/python3 scripts/ml.py envio 47843335308
    venv/bin/python3 scripts/ml.py usuario 29563319
    venv/bin/python3 scripts/ml.py get /items/MLA123?attributes=id,price   # crudo

Solo hace GET. Cualquier cambio real (PUT/POST/DELETE) va por el flujo normal,
que pide autorización.
"""
import sys
import os
import json as _json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ml_token, conectar_db  # noqa: E402

import requests  # noqa: E402

BASE = 'https://api.mercadolibre.com'
MI_SELLER_ID = 29563319


def _get(path, token, params=None):
    url = path if path.startswith('http') else BASE + path
    r = requests.get(url, headers={'Authorization': f'Bearer {token}'},
                     params=params, timeout=30)
    return r


def _pp(obj):
    print(_json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def _skus_por_mla():
    """{mla_id: sku} desde el mapeo local, para enriquecer las salidas."""
    try:
        db = conectar_db()
        cur = db.cursor()
        cur.execute("SELECT mla_id, sku FROM sku_mla_mapeo WHERE activo=TRUE")
        m = {r['mla_id']: r['sku'] for r in cur.fetchall()}
        cur.close(); db.close()
        return m
    except Exception:
        return {}


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    cmd = args[0]
    rest = args[1:]

    # flags sueltos
    campos = None
    status_f = None
    limpio = []
    i = 0
    while i < len(rest):
        if rest[i] == '--campos' and i + 1 < len(rest):
            campos = rest[i + 1]; i += 2
        elif rest[i] == '--status' and i + 1 < len(rest):
            status_f = rest[i + 1]; i += 2
        else:
            limpio.append(rest[i]); i += 1
    rest = limpio

    token = ml_token()

    if cmd == 'item':
        if not rest:
            print('Falta el MLA'); return 1
        p = {'attributes': campos} if campos else None
        r = _get(f'/items/{rest[0]}', token, p)
        print(f'HTTP {r.status_code}')
        _pp(r.json())

    elif cmd == 'items':
        if not rest:
            print('Faltan los MLA (separados por coma)'); return 1
        ids = [x for x in rest[0].replace(' ', '').split(',') if x]
        att = campos or 'id,title,status,price,available_quantity,catalog_product_id,shipping'
        sk = _skus_por_mla()
        for j in range(0, len(ids), 20):
            r = _get('/items', token, {'ids': ','.join(ids[j:j + 20]), 'attributes': att})
            for w in (r.json() or []):
                b = w.get('body') or {}
                b['_sku_local'] = sk.get(b.get('id'))
                _pp(b)

    elif cmd == 'catalogo':
        if not rest:
            print('Falta el catálogo (MLAxxxx)'); return 1
        r = _get(f'/products/{rest[0]}', token)
        print(f'HTTP {r.status_code}')
        _pp(r.json())

    elif cmd == 'ofertas':
        if not rest:
            print('Falta el catálogo (MLAxxxx)'); return 1
        r = _get(f'/products/{rest[0]}/items', token, {'limit': 50})
        if r.status_code != 200:
            print(f'HTTP {r.status_code}'); print(r.text[:300]); return 1
        res = (r.json() or {}).get('results', [])
        filas = []
        for it in res:
            sid = it.get('seller_id')
            nick = None
            try:
                ru = _get(f'/users/{sid}', token)
                if ru.ok:
                    nick = ru.json().get('nickname')
            except Exception:
                pass
            filas.append({'item_id': it.get('item_id'), 'precio': it.get('price'),
                          'seller_id': sid, 'nickname': nick,
                          'yo': 'SÍ' if sid == MI_SELLER_ID else ''})
        filas.sort(key=lambda x: x['precio'] or 0)
        from _common import imprimir_tabla
        imprimir_tabla(filas)

    elif cmd == 'promos':
        if not rest:
            print('Falta el MLA'); return 1
        r = _get(f'/seller-promotions/items/{rest[0]}', token, {'app_version': 'v2'})
        print(f'HTTP {r.status_code}')
        _pp(r.json())

    elif cmd == 'campanias':
        r = _get(f'/seller-promotions/users/{MI_SELLER_ID}', token, {'app_version': 'v2'})
        d = r.json()
        _pp(d.get('results', d))

    elif cmd == 'campania':
        if len(rest) < 2:
            print('Uso: campania <P-MLAxxx> <TIPO> [--status started]'); return 1
        cid, ctipo = rest[0], rest[1]
        p = {'promotion_type': ctipo, 'app_version': 'v2', 'limit': 50}
        if status_f:
            p['status'] = status_f
        vistos, filas, off = set(), [], 0
        sk = _skus_por_mla()
        while True:
            p['offset'] = off
            r = _get(f'/seller-promotions/promotions/{cid}/items', token, p)
            if r.status_code != 200:
                print(f'HTTP {r.status_code}'); print(r.text[:300]); break
            d = r.json() or {}
            res = d.get('results') or []
            for it in res:
                m = it.get('id')
                if m in vistos:
                    continue
                vistos.add(m)
                filas.append({'mla': m, 'sku': sk.get(m), 'status': it.get('status'),
                              'precio': it.get('price'), 'orig': it.get('original_price'),
                              'tu_%': it.get('seller_percentage'),
                              'desde': it.get('start_date'), 'hasta': it.get('end_date')})
            tot = d.get('paging', {}).get('total', len(res))
            off += 50
            if off >= tot or not res:
                break
        from _common import imprimir_tabla
        imprimir_tabla(filas, max_ancho=26)

    elif cmd == 'orden':
        if not rest:
            print('Falta el número de orden'); return 1
        r = _get(f'/orders/{rest[0]}', token)
        print(f'HTTP {r.status_code}')
        _pp(r.json())

    elif cmd == 'envio':
        if not rest:
            print('Falta el shipping_id'); return 1
        r = _get(f'/shipments/{rest[0]}', token)
        print(f'HTTP {r.status_code}')
        _pp(r.json())

    elif cmd == 'usuario':
        uid = rest[0] if rest else MI_SELLER_ID
        r = _get(f'/users/{uid}', token)
        print(f'HTTP {r.status_code}')
        _pp(r.json())

    elif cmd == 'get':
        if not rest:
            print('Falta el path, ej: /items/MLA123'); return 1
        r = _get(rest[0], token)
        print(f'HTTP {r.status_code}')
        try:
            _pp(r.json())
        except Exception:
            print(r.text[:2000])

    else:
        print(f'Comando desconocido: {cmd}\n')
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
