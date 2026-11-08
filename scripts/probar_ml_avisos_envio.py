#!/usr/bin/env python3
"""Prueba los avisos de seguimiento ME1 a ML (ml_avisar_envio_me1) SIN mandar nada ni escribir en la base.
- Los GET a ML (orden y envío) son reales; los POST a ML, execute_db y log_evento se reemplazan por simulaciones.
- Verifica: a quién aplica, orden de los avisos, que no se repitan, que un rechazo corte la cadena,
  cuerpo V2 (service_id 154), y que las plantillas compilen y el macro de íconos se renderice.

Uso: venv/bin/python scripts/probar_ml_avisos_envio.py
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import app as A  # noqa: E402

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    fallas += 0 if cond else 1


# ── Simulaciones: nada sale a ML por POST, nada se escribe ──────────────────────
posts, escrituras = [], []
rechazar_paso = {'valor': None}
_ml_request_real = A.ml_request
_query_one_real = A.query_one


class _Resp:
    def __init__(self, code, text='{}'):
        self.status_code, self.text = code, text


def ml_request_falso(method, url, token, json_data=None, params=None, **kw):
    if method.lower() != 'get':
        posts.append((url, json_data))
        paso = 'out_for_delivery' if (json_data or {}).get('substatus') == 'out_for_delivery' else (json_data or {}).get('status')
        if rechazar_paso['valor'] == paso:
            return _Resp(400, '{"message":"simulado"}')
        return _Resp(200)
    return _ml_request_real(method, url, token, json_data=json_data, params=params)


A.ml_request = ml_request_falso
A.execute_db = lambda q, p=None: escrituras.append((' '.join(q.split()), p))
A.log_evento = lambda *a, **k: None

# ── Plantillas ──────────────────────────────────────────────────────────────────
for t in ('ventas_activas.html', 'proceso_envio.html', 'ventas_historicas.html', '_ml_seguimiento.html'):
    try:
        A.app.jinja_env.get_template(t)
        check(True, f'{t} compila')
    except Exception as e:
        check(False, f'{t}: {e}')

ahora = datetime(2026, 11, 8, 15, 30)
with A.app.test_request_context('/'):
    m = A.app.jinja_env.from_string('{% from "_ml_seguimiento.html" import ml_seguimiento %}{{ ml_seguimiento(v) }}')
    html = m.render(v={'id': 1, 'canal': 'Mercado Libre', 'metodo_envio': 'Flete Propio', 'ml_despachado_at': ahora,
                       'ml_en_reparto_at': ahora, 'ml_entregado_at': None, 'ml_aviso_error': 'delivered: ML 400'})
    check('🚚' in html and '📦' in html and '✅' not in html and '⚠️ ML' in html and '08/11 12:30' in html,
          'macro: íconos, error con reintento y hora AR (15:30 UTC → 12:30)')
    html = m.render(v={'id': 1, 'canal': 'Mercado Libre', 'metodo_envio': 'Flex', 'ml_despachado_at': ahora})
    check(html.strip() == '', 'macro: nada para Flex')

# ── Ventas reales para las pruebas ───────────────────────────────────────────────
cands = A.query_db("SELECT id, numero_venta, estado_entrega FROM ventas WHERE canal='Mercado Libre' "
                   "AND metodo_envio='Flete Propio' AND estado_entrega IN ('pendiente','en_proceso') "
                   "ORDER BY id DESC LIMIT 15")
token = A.cargar_ml_token()
base = None
for c in cands:
    oid = c['numero_venta'][3:]
    o = _ml_request_real('get', f'https://api.mercadolibre.com/orders/{oid}', token)
    sid = (o.json().get('shipping') or {}).get('id') if o.status_code == 200 else None
    if not sid:
        continue
    s = _ml_request_real('get', f'https://api.mercadolibre.com/shipments/{sid}', token).json()
    print(f"      {c['numero_venta']} {c['estado_entrega']} shipment {sid} mode={s.get('mode')} "
          f"status={s.get('status')}/{s.get('substatus')}")
    if s.get('mode') == 'me1' and s.get('status') not in ('shipped', 'delivered', 'cancelled'):
        base = dict(c)
        break
check(base is not None, 'hay una venta ML Flete Propio ME1 sin despachar para probar')


def con_venta(v):
    A.query_one = lambda q, p=None: v if 'ml_despachado_at' in q else _query_one_real(q, p)


def correr(v, hasta, enviar=True):
    posts.clear()
    escrituras.clear()
    con_venta(v)
    r = A.ml_avisar_envio_me1(v['id'], hasta, enviar=enviar, token=token)
    A.query_one = _query_one_real
    return r


if base:
    v0 = {**base, 'canal': 'Mercado Libre', 'metodo_envio': 'Flete Propio',
          'ml_despachado_at': None, 'ml_en_reparto_at': None, 'ml_entregado_at': None}

    # 1. Papel azul en Activas → solo "En camino"
    ok, msg, av = correr({**v0, 'estado_entrega': 'pendiente'}, 'shipped')
    check(ok is True and len(posts) == 1 and posts[0][1]['status'] == 'shipped' and posts[0][1]['substatus'] is None,
          f'papel azul: 1 aviso shipped/null ({msg})')
    b = posts[0][1] if posts else {}
    check(posts and '/v2/shipments/' in posts[0][0] and b['payload'].get('service_id') == 154
          and b['payload'].get('date', '').endswith('-03:00'), 'cuerpo V2: url /v2, service_id 154, fecha -03:00')
    check(any('ml_despachado_at=NOW()' in q for q, _ in escrituras), 'marca ml_despachado_at')

    # 2. Pasar a Proceso sin haber impreso → En camino + Salió a distribución, en orden
    ok, msg, av = correr({**v0, 'estado_entrega': 'en_proceso'}, 'out_for_delivery')
    check(ok is True and [p[1]['substatus'] for p in posts] == [None, 'out_for_delivery'],
          'pasar a proceso sin papel: shipped → out_for_delivery')

    # 3. Pasar a Proceso ya impreso → solo Salió a distribución
    ok, msg, av = correr({**v0, 'estado_entrega': 'en_proceso', 'ml_despachado_at': ahora}, 'out_for_delivery')
    check(ok is True and [p[1]['substatus'] for p in posts] == ['out_for_delivery'], 'pasar a proceso ya impreso: solo out_for_delivery')

    # 4. Entregada sin nada previo → los tres en orden
    ok, msg, av = correr({**v0, 'estado_entrega': 'entregada'}, 'delivered')
    check(ok is True and [(p[1]['status'], p[1]['substatus']) for p in posts] ==
          [('shipped', None), ('shipped', 'out_for_delivery'), ('delivered', None)], 'entregada desde cero: 3 avisos en orden')

    # 5. Todo ya informado → no manda nada
    ok, msg, av = correr({**v0, 'estado_entrega': 'entregada', 'ml_despachado_at': ahora, 'ml_en_reparto_at': ahora,
                          'ml_entregado_at': ahora}, 'delivered')
    check(ok is True and not posts and msg == 'ya informado', 'ya informado: no repite (ni consulta a ML)')

    # 6. ML rechaza el 2º aviso → corta, guarda el error, no manda "delivered"
    rechazar_paso['valor'] = 'out_for_delivery'
    ok, msg, av = correr({**v0, 'estado_entrega': 'entregada'}, 'delivered')
    rechazar_paso['valor'] = None
    check(ok is False and len(posts) == 2 and any('ml_aviso_error' in q for q, _ in escrituras)
          and not any('ml_entregado_at=NOW()' in q for q, _ in escrituras), f'rechazo corta la cadena y guarda error ({msg})')

    # 7. Estado que no corresponde (pendiente → delivered) → no aplica, sin llamadas
    ok, msg, av = correr({**v0, 'estado_entrega': 'pendiente'}, 'delivered')
    check(ok is None and not posts, f'estado pendiente + delivered: no aplica ({msg})')

    # 8. Simulacro sin enviar (enviar=False): arma cuerpos, no POST ni escrituras
    ok, msg, av = correr({**v0, 'estado_entrega': 'en_proceso'}, 'out_for_delivery', enviar=False)
    check(ok is True and len(av) == 2 and not posts and not escrituras, 'enviar=False: solo arma los 2 cuerpos')

# 9. No aplica a otros métodos/canales (consulta real a la base)
for cond, nombre in (("canal='Mercado Libre' AND metodo_envio='Flex'", 'ML Flex'),
                     ("canal='Mercado Libre' AND metodo_envio='Zippin'", 'ML Zippin'),
                     ("canal='tienda_web'", 'tienda web')):
    v = A.query_one(f"SELECT id FROM ventas WHERE {cond} ORDER BY id DESC LIMIT 1")
    if v:
        posts.clear()
        ok, msg, _ = A.ml_avisar_envio_me1(v['id'], 'shipped', token=token)
        check(ok is None and not posts, f'{nombre}: no aplica ({msg})')

# 10. Lote en segundo plano: ids basura no rompen
A.ml_avisar_envio_me1_bg(['x', None], 'shipped')
check(True, 'ml_avisar_envio_me1_bg ignora ids inválidos')

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
