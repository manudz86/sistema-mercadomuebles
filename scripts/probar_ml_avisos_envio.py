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
    check(any('ml_despachado_at=%s' in q for q, _ in escrituras), 'marca ml_despachado_at')

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

if base:
    from datetime import timedelta, timezone
    AR = timezone(timedelta(hours=-3))
    hoy_ar = datetime.now(AR).replace(tzinfo=None)

    # 11. Entrega con fecha anterior (hace 2 días 18:00 AR) sin avisos previos → 3 avisos con esa fecha, en orden
    fe = (hoy_ar - timedelta(days=2)).replace(hour=18, minute=0, second=0, microsecond=0)
    ok, msg, av = correr({**v0, 'estado_entrega': 'entregada', 'fecha_entrega': fe}, 'delivered')
    fechas = [p[1]['payload']['date'][:16] for p in posts]
    esperado = [(fe - timedelta(minutes=m)).strftime('%Y-%m-%dT%H:%M') for m in (2, 1, 0)]
    check(ok is True and fechas == esperado, f'entrega con fecha anterior: {fechas}')
    check(any(p == (fe + timedelta(hours=3), v0['id']) for q, p in escrituras if 'ml_entregado_at=%s' in q),
          'ml_entregado_at guarda la fecha del evento (UTC)')

    # 12. "En camino" ya informado DESPUÉS de esa fecha → no manda nada y explica
    ok, msg, av = correr({**v0, 'estado_entrega': 'entregada', 'fecha_entrega': fe,
                          'ml_despachado_at': datetime.utcnow().replace(microsecond=0)}, 'delivered')
    check(ok is False and not posts and 'no puede ser anterior' in msg, f'orden respetado: {msg}')

    # 13. "En camino" informado ANTES de esa fecha → manda los 2 que faltan con la fecha elegida
    ok, msg, av = correr({**v0, 'estado_entrega': 'entregada', 'fecha_entrega': fe,
                          'ml_despachado_at': fe + timedelta(hours=3) - timedelta(hours=5)}, 'delivered')
    check(ok is True and [p[1]['payload']['date'][:16] for p in posts] == esperado[1:], 'previo anterior: 2 avisos con la fecha elegida')

    # 13b. Caso viernes: papel azul 19:00 y proceso 19:05 ese día, entregada "ese día" (18:00) → entrega 19:07
    ok, msg, av = correr({**v0, 'estado_entrega': 'entregada', 'fecha_entrega': fe,
                          'ml_despachado_at': fe + timedelta(hours=4),                       # 19:00 AR en UTC
                          'ml_en_reparto_at': fe + timedelta(hours=4, minutes=5)}, 'delivered')  # 19:05 AR
    check(ok is True and [p[1]['payload']['date'][:16] for p in posts] == [(fe + timedelta(hours=1, minutes=7)).strftime('%Y-%m-%dT%H:%M')],
          f'viernes 19 hs: entrega después del último aviso, mismo día → {[p[1]["payload"]["date"][:16] for p in posts]}')
    #     ...y si falta "Salió a distribución": 2 avisos después del de las 19:00
    ok, msg, av = correr({**v0, 'estado_entrega': 'entregada', 'fecha_entrega': fe,
                          'ml_despachado_at': fe + timedelta(hours=4)}, 'delivered')
    check(ok is True and [p[1]['payload']['date'][:16] for p in posts] ==
          [(fe + timedelta(hours=1, minutes=m)).strftime('%Y-%m-%dT%H:%M') for m in (2, 3)], 'viernes 19 hs sin proceso: 19:02 y 19:03')
    #     ...último aviso a las 23:59 → no entra en el día → no manda y explica
    ok, msg, av = correr({**v0, 'estado_entrega': 'entregada', 'fecha_entrega': fe,
                          'ml_despachado_at': fe + timedelta(hours=3, minutes=5, seconds=59) + timedelta(hours=5, minutes=54)}, 'delivered')
    check(ok is False and not posts, f'último aviso 23:59: no manda ({msg})')

    # 14. Entregada recién (fecha_entrega = ahora) → fecha de cada aviso = ahora
    ok, msg, av = correr({**v0, 'estado_entrega': 'entregada', 'fecha_entrega': hoy_ar}, 'delivered')
    check(ok is True and all(p[1]['payload']['date'][:13] == datetime.now(AR).strftime('%Y-%m-%dT%H') for p in posts),
          'entregada hoy: avisos con la hora actual')

# 15. Fecha del formulario
hoy = (datetime.utcnow() - __import__('datetime').timedelta(hours=3)).date()
td = __import__('datetime').timedelta
for valor, esp, nombre in (('', (None, None), 'vacío = hoy'),
                           (hoy.isoformat(), (None, None), 'hoy = ahora'),
                           ((hoy - td(days=2)).isoformat(), (f'{hoy - td(days=2)} 18:00:00', None), 'anteayer = 18:00'),
                           ((hoy + td(days=1)).isoformat(), (None, 'La fecha de entrega no puede ser futura'), 'futura'),
                           ((hoy - td(days=61)).isoformat(), (None, 'La fecha de entrega es de hace más de 60 días'), '> 60 días'),
                           ('08/11/2026', (None, 'Fecha de entrega inválida'), 'formato inválido')):
    with A.app.test_request_context('/', method='POST', data={'fecha_entrega': valor}):
        r = A.fecha_entrega_desde_form()
    check(r == esp, f'formulario {nombre}: {r}')
check(A.entrega_antes_de_venta({'fecha_venta': datetime(2026, 11, 5, 10)}, '2026-11-04 18:00:00')
      and not A.entrega_antes_de_venta({'fecha_venta': datetime(2026, 11, 5, 10)}, '2026-11-05 18:00:00')
      and not A.entrega_antes_de_venta({'fecha_venta': datetime(2026, 11, 5, 10)}, None), 'entrega anterior a la venta')

# 16. Selector de fecha en el navegador (Chromium): Hoy por defecto, Ayer, Otra fecha, lote
from playwright.sync_api import sync_playwright  # noqa: E402
inc = A.app.jinja_env.get_template('_fecha_entrega.html').render()
pagina = ('<html><body><div id="modalConfirmacion"><h5 id="modalTitulo"></h5><div id="modalMensaje"></div>'
          '<button id="btnConfirmar"></button></div><script>let ventaIdActual=null, accionActual=null;'
          'window.bootstrap={Modal:{getOrCreateInstance:()=>({show(){}})}};'
          'window._enviado=null; HTMLFormElement.prototype.submit=function(){window._enviado='
          '{action:this.getAttribute("action"), campos:[...new FormData(this).entries()]}};</script>' + inc + '</body></html>')
with sync_playwright() as pw:
    nav = pw.chromium.launch(args=['--no-sandbox'])
    pag = nav.new_page(viewport={'width': 390, 'height': 844})
    pag.set_content(pagina)
    pag.evaluate("abrirEntregaMultiple(['11','12'], '/ventas/proceso/marcar-entregadas-multiple')")
    hoy_js = pag.eval_on_selector('#fe-fecha', 'e => e.value')
    check(hoy_js == hoy.isoformat() or hoy_js == (hoy + td(days=1)).isoformat() or hoy_js == (hoy - td(days=1)).isoformat(),
          f'por defecto Hoy ({hoy_js})')
    check(pag.locator('#modalTitulo').inner_text() == 'Marcar 2 venta(s) como Entregadas', 'título del lote')
    pag.click('text=Ayer')
    ayer_js = pag.eval_on_selector('#fe-fecha', 'e => e.value')
    pag.evaluate('enviarEntregaMultiple()')
    env = pag.evaluate('window._enviado')
    check(env and env['action'].endswith('/ventas/proceso/marcar-entregadas-multiple')
          and env['campos'] == [['venta_ids', '11'], ['venta_ids', '12'], ['fecha_entrega', ayer_js]],
          f'lote con Ayer → {env and env["campos"]}')
    pag.evaluate('window._enviado=null')
    pag.click('text=Otra fecha')
    check(pag.is_visible('#fe-otra'), 'Otra fecha muestra el calendario')
    pag.on('dialog', lambda d: d.accept())
    pag.evaluate('enviarEntregaMultiple()')
    check(pag.evaluate('window._enviado') is None, 'Otra fecha sin completar: no envía')
    pag.fill('#fe-otra', (hoy - td(days=4)).isoformat())
    pag.evaluate('enviarEntregaMultiple()')
    env = pag.evaluate('window._enviado')
    check(env and ['fecha_entrega', (hoy - td(days=4)).isoformat()] in env['campos'], 'Otra fecha elegida va en el form')
    anchos = pag.evaluate("[...document.querySelectorAll('.fe-opciones .btn')].map(b => Math.round(b.getBoundingClientRect().height))")
    check(min(anchos) >= 44, f'botones cómodos para el dedo (alto {anchos} px)')
    nav.close()

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
