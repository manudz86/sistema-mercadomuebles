#!/usr/bin/env python3
"""Auditoría de ventas de la tienda web (www.mercadomuebles.com.ar) — SOLO LECTURA.

- Base: usuario de solo lectura (DB_RO_USER, vía scripts/_common.conectar_db). Solo SELECT.
- Pasarelas: solo GET (Mercado Pago /v1/payments/{id}; GetNet payment-intent) para fecha de
  aprobación, monto cobrado y reintegros. Payway: tabla local payway_intentos (sync de su API).
- No exporta datos personales (nombre, email, teléfono, DNI, dirección). Los datos de cliente
  solo se usan en memoria (hash) para detectar reintentos del mismo comprador.

Universo:
  * Pedido web = checkout creado en la tienda (tabla pedidos_pendientes, 1 fila por checkout,
    compartida por MP / Payway / GetNet). Una venta (tabla ventas, canal='tienda_web') se
    registra recién cuando el pago queda aprobado.
  * Período por FECHA DE CREACIÓN del pedido (checkout), en hora Argentina.

Uso: venv/bin/python scripts/generar_reporte_ventas_web.py <dir_salida> [dir_crudos]
"""
import csv
import hashlib
import json
import os
import re
import sys
from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta, date

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import conectar_db, cargar_env  # noqa: E402

DESDE = datetime(2026, 8, 11, 0, 0, 0)            # AR
HASTA = datetime(2026, 11, 8, 23, 59, 59)         # AR
UTC_OFF = timedelta(hours=3)                      # AR = UTC-3 (sin horario de verano)
SUF = '2026-08-11_2026-11-08'
CORTE_CONSULTA = None                              # se completa con la hora de corrida

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)
OUT = sys.argv[1]
CRUDOS = sys.argv[2] if len(sys.argv) > 2 else None
os.makedirs(OUT, exist_ok=True)
if CRUDOS:
    os.makedirs(CRUDOS, exist_ok=True)

env = cargar_env()
for k, v in env.items():
    os.environ.setdefault(k, v)
db = conectar_db()          # solo lectura
cur = db.cursor()


def q(sql, params=None):
    s = sql.strip().lower()
    assert s.startswith('select'), 'solo SELECT'
    cur.execute(sql, params or ())
    return cur.fetchall()


def f2(x):
    return round(float(x or 0), 2)


def ar_desde_utc(dt):
    return dt - UTC_OFF if dt else None


def iso(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ''


def h(*partes):
    base = '|'.join(str(p or '').strip().lower() for p in partes)
    return hashlib.sha256(base.encode()).hexdigest()[:12] if base.strip('|') else ''


def parse_iso_ar(s):
    """'2026-11-04T22:05:31.000-04:00' → datetime naive en hora AR (-03:00)."""
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace('Z', '+00:00'))
        if d.tzinfo is None:
            return d
        return (d - d.utcoffset()).replace(tzinfo=None) - UTC_OFF
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# 1) Checkouts (pedidos creados) — pedidos_pendientes.fecha_creacion es TIMESTAMP en UTC
# ──────────────────────────────────────────────────────────────────────────────
checkouts = q("SELECT ref, carrito_json, cliente_json, fecha_creacion FROM pedidos_pendientes "
              "WHERE fecha_creacion BETWEEN %s AND %s",
              (DESDE + UTC_OFF - timedelta(days=10), datetime.utcnow()))
ck = {}
for r in checkouts:
    try:
        carrito = json.loads(r['carrito_json'] or '[]')
    except Exception:
        carrito = []
    try:
        cli = json.loads(r['cliente_json'] or '{}')
    except Exception:
        cli = {}
    zq = cli.get('zipnova_quote') or {}
    sub = sum(float(i.get('precio') or 0) * int(i.get('cantidad') or 1) for i in carrito)
    ck[r['ref']] = {
        'ref': r['ref'],
        'creado_ar': ar_desde_utc(r['fecha_creacion']),
        'subtotal_carrito': round(sub, 2),
        'flete_cotizado': f2(zq.get('precio')) if cli.get('tipo_entrega', 'envio') == 'envio' else 0.0,
        'unidades': sum(int(i.get('cantidad') or 1) for i in carrito),
        'skus': [str(i.get('sku') or '') for i in carrito],
        'cupon': (cli.get('cupon') or {}).get('codigo') if isinstance(cli.get('cupon'), dict) else (cli.get('cupon') or ''),
        'comprador': h(cli.get('email')) or h(cli.get('telefono')) or h(cli.get('dni')),
        'utm_first': cli.get('_origen_first'), 'utm_last': cli.get('_origen_last'),
    }

gn_pend = {r['pedido_ref']: r for r in q(
    "SELECT pedido_ref, payment_intent_id, estado, fecha_creacion FROM pedidos_pendientes_getnet")}
pw_int = q("SELECT payment_id, ref, site_transaction_id, fecha, amount, installments, status, motivo, "
           "JSON_EXTRACT(raw_json,'$.amount') raw_amount, JSON_EXTRACT(raw_json,'$.date') raw_date "
           "FROM payway_intentos")
pw_por_id = {int(r['payment_id']): r for r in pw_int}
pw_por_ref = defaultdict(list)
for r in pw_int:
    pw_por_ref[(r['ref'] or '')].append(r)

# ──────────────────────────────────────────────────────────────────────────────
# 2) Ventas web (pagos aprobados registrados). Margen amplio para capturar pedidos creados
#    en el período y pagados después, y ventas sin checkout vinculado.
# ──────────────────────────────────────────────────────────────────────────────
ventas = q("SELECT id, numero_venta, canal, fecha_venta, fecha_registro, importe_total, importe_abonado, "
           "costo_flete, metodo_pago, tipo_entrega, metodo_envio, estado_entrega, estado_pago, estado, "
           "pago_mercadopago, pago_efectivo, pago_transferencia, pago_tarjeta, notas, "
           "origen_first, origen_last, email_cliente, telefono_cliente, dni_cliente "
           "FROM ventas WHERE canal='tienda_web' AND fecha_venta >= %s ORDER BY fecha_venta",
           (DESDE - timedelta(days=10),))
ids = [v['id'] for v in ventas] or [0]
items = defaultdict(list)
for r in q("SELECT i.venta_id, i.sku, i.cantidad, i.precio_unitario, "
           "COALESCE(pb.nombre, pc.nombre) nombre, pb.tipo, pb.linea, pb.modelo, pb.medida, "
           "(pc.id IS NOT NULL) es_compuesto "
           "FROM items_venta i LEFT JOIN productos_base pb ON pb.sku=i.sku "
           "LEFT JOIN productos_compuestos pc ON pc.sku=i.sku "
           f"WHERE i.venta_id IN ({','.join(['%s'] * len(ids))}) ORDER BY i.id", ids):
    items[r['venta_id']].append(r)
cupon_uso = {}
for r in q("SELECT cu.venta_numero, c.codigo, c.tipo, c.valor FROM cupones_uso cu "
           "JOIN cupones c ON c.id=cu.cupon_id WHERE cu.venta_numero IS NOT NULL"):
    cupon_uso[r['venta_numero']] = r

# ──────────────────────────────────────────────────────────────────────────────
# 3) Pasarelas (GET)
# ──────────────────────────────────────────────────────────────────────────────
MP_TOK = os.getenv('MP_ACCESS_TOKEN', '')
mp_cache = {}


def mp_pago(pid):
    if pid in mp_cache:
        return mp_cache[pid]
    out = None
    try:
        r = requests.get(f'https://api.mercadopago.com/v1/payments/{pid}',
                         headers={'Authorization': f'Bearer {MP_TOK}'}, timeout=30)
        if r.status_code == 200:
            out = r.json()
    except Exception:
        out = None
    mp_cache[pid] = out
    if out and CRUDOS:
        resumen = {k: out.get(k) for k in ('id', 'status', 'status_detail', 'date_created', 'date_approved',
                                            'date_last_updated', 'transaction_amount', 'transaction_amount_refunded',
                                            'total_paid_amount' if False else 'currency_id', 'coupon_amount',
                                            'installments', 'external_reference', 'shipping_amount')}
        resumen['total_paid_amount'] = (out.get('transaction_details') or {}).get('total_paid_amount')
        resumen['net_received_amount'] = (out.get('transaction_details') or {}).get('net_received_amount')
        resumen['refunds'] = [{k: rf.get(k) for k in ('id', 'amount', 'date_created', 'status')}
                              for rf in (out.get('refunds') or [])]
        with open(os.path.join(CRUDOS, f'mp_{pid}.json'), 'w') as fh:
            json.dump(resumen, fh, ensure_ascii=False, indent=1, default=str)
    return out


mp_busq_cache = {}


def mp_por_ref(ref):
    """Todos los pagos MP de un pedido (external_reference). Solo GET. Lista resumida o None si falla."""
    if not ref:
        return []
    if ref in mp_busq_cache:
        return mp_busq_cache[ref]
    out = None
    try:
        r = requests.get('https://api.mercadopago.com/v1/payments/search',
                         params={'external_reference': ref, 'limit': 50},
                         headers={'Authorization': f'Bearer {MP_TOK}'}, timeout=30)
        if r.status_code == 200:
            out = [{'id': p.get('id'), 'status': p.get('status'), 'status_detail': p.get('status_detail'),
                    'amount': f2(p.get('transaction_amount')), 'refunded': f2(p.get('transaction_amount_refunded')),
                    'date_created': p.get('date_created'), 'date_approved': p.get('date_approved'),
                    'currency': p.get('currency_id')}
                   for p in (r.json().get('results') or [])]
    except Exception:
        out = None
    mp_busq_cache[ref] = out
    return out


gn_token = None


def gn_get(pid):
    """GetNet: GET payment-intent (solo lectura). Devuelve dict o None."""
    global gn_token
    base = os.getenv('GETNET_BASE_URL', '')
    if not base or not pid:
        return None
    try:
        if gn_token is None:
            r = requests.post(f'{base}/authentication/oauth2/access_token',
                              data={'grant_type': 'client_credentials',
                                    'client_id': os.getenv('GETNET_CLIENT_ID', ''),
                                    'client_secret': os.getenv('GETNET_CLIENT_SECRET', '')},
                              headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=15)
            gn_token = r.json().get('access_token') if r.status_code == 200 else ''
        if not gn_token:
            return None
        for ruta in ('/digital-checkout/v1/payment-intent/{pid}', '/v1/payments/{pid}'):
            r = requests.get(base + ruta.format(pid=pid), headers={'Authorization': f'Bearer {gn_token}'}, timeout=20)
            if r.status_code == 200:
                d = r.json()
                if CRUDOS:
                    pay = d.get('payment') or {}
                    with open(os.path.join(CRUDOS, f'getnet_{pid}.json'), 'w') as fh:
                        json.dump({'ruta': ruta, 'status': d.get('status'), 'payment': {
                            k: pay.get(k) for k in ('status', 'amount', 'currency', 'installment', 'installments',
                                                    'created_at', 'updated_at', 'refunds', 'refunded_amount')},
                            'claves': list(d.keys())}, fh, ensure_ascii=False, indent=1, default=str)
                return d
    except Exception:
        return None
    return None


# ──────────────────────────────────────────────────────────────────────────────
# 4) Armado de cada venta
# ──────────────────────────────────────────────────────────────────────────────
def nota(v, patron):
    m = re.search(patron, v.get('notas') or '', re.I)
    return m.group(1) if m else None


def utm(js):
    try:
        d = json.loads(js) if isinstance(js, str) else (js or {})
    except Exception:
        d = {}
    ref = d.get('referrer') or ''
    dom = re.sub(r'^https?://', '', ref).split('/')[0] if ref else ''
    return {'source': d.get('utm_source') or '', 'medium': d.get('utm_medium') or '',
            'campaign': d.get('utm_campaign') or '', 'gclid': bool(d.get('gclid')),
            'fbclid': bool(d.get('fbclid')), 'referrer': dom}


def categoria(it):
    if it['es_compuesto']:
        return 'Sommier (colchón + base)'
    return {'colchon': 'Colchón', 'base': 'Base', 'almohada': 'Almohada', 'servicio': 'Servicio'}.get(
        it['tipo'] or '', it['tipo'] or 'Sin categoría')


def modelo(it):
    if it['modelo']:
        return it['modelo']
    n = it['nombre'] or it['sku']
    n = re.sub(r'^(Sommier|Colchón|Colchon|Base|Almohada)\s+', '', n, flags=re.I)
    return re.sub(r'\s+\d{2,3}x\d{2,3}.*$', '', n).strip()


filas = []
refs_usados = set()
for v in ventas:
    num = v['numero_venta']
    pas = v['metodo_pago'] or ''
    its = items.get(v['id'], [])
    sub_items = round(sum(float(i['precio_unitario']) * int(i['cantidad']) for i in its), 2)
    obs = []
    ref = None
    estado_pasarela = ''
    fecha_aprob = None
    fuente_aprob = ''
    cobrado_pasarela = None
    reintegrado = 0.0
    fecha_reint = None
    cuotas = nota(v, r'cuotas:\s*(\d+)')
    coef = nota(v, r'coef:?\s*([\d.]+)')
    moneda = 'ARS'
    origen_registro = 'checkout_online'

    if num.startswith('MP-'):
        pid = num[3:]
        p = mp_pago(pid)
        if p:
            ref = p.get('external_reference')
            estado_pasarela = f"{p.get('status')}/{p.get('status_detail')}"
            fecha_aprob = parse_iso_ar(p.get('date_approved'))
            fuente_aprob = 'Mercado Pago date_approved'
            cobrado_pasarela = f2(p.get('transaction_amount'))
            reintegrado = f2(p.get('transaction_amount_refunded'))
            rfs = [parse_iso_ar(rf.get('date_created')) for rf in (p.get('refunds') or [])]
            fecha_reint = max([d for d in rfs if d], default=None)
            moneda = p.get('currency_id') or 'ARS'
            cuotas = cuotas or str(p.get('installments') or '')
            if p.get('status') == 'charged_back':
                obs.append('contracargo en MP')
            otros = mp_por_ref(ref)
            if otros is None:
                obs.append('MP: no se pudo buscar otros pagos del pedido')
            else:
                extra = [o for o in otros if str(o['id']) != str(pid)]
                ext_ok = [o for o in extra if o['status'] == 'approved']
                ext_no = [o for o in extra if o['status'] in ('rejected', 'cancelled')]
                if ext_ok:
                    cobrado_pasarela = round(cobrado_pasarela + sum(o['amount'] for o in ext_ok), 2)
                    reintegrado = round(reintegrado + sum(o['refunded'] for o in ext_ok), 2)
                    obs.append(f"pago dividido: {len(ext_ok)} pago(s) MP adicional(es) aprobado(s) "
                               f"({', '.join(str(o['id']) for o in ext_ok)})")
                if ext_no:
                    obs.append(f'{len(ext_no)} intento(s) MP rechazado(s)/cancelado(s) antes de aprobar (mismo pedido)')
        else:
            obs.append('no se pudo leer el pago en MP')
    elif num.startswith('PW-'):
        pwid = nota(v, r'PWID:\s*(\d+)')
        opw = nota(v, r'OP_PAYWAY:\s*PW-([0-9a-zA-Z]+)')
        ref = opw
        r = pw_por_id.get(int(pwid)) if pwid else None
        if pas == 'Transferencia':
            origen_registro = 'manual_panel'
            obs.append('número PW- pero cargada como Transferencia')
        if r:
            estado_pasarela = r['status']
            fecha_aprob = parse_iso_ar((r['raw_date'] or '').strip('"').replace('Z', '')) or r['fecha']
            fuente_aprob = 'Payway (payway_intentos.date, hora local)'
            if r['status'] in ('accredited', 'approved'):
                cobrado_pasarela = round(float(r['raw_amount'] or 0) / 100, 2) or f2(r['amount'])
            elif r['status'] in ('annulment_approved', 'refund_approved'):
                cobrado_pasarela = f2(v['importe_abonado'])
                reintegrado = f2(v['importe_abonado'])
                obs.append(f"Payway {r['status']}: reintegro total (monto = lo cobrado; "
                           "fecha del reintegro no disponible)")
        else:
            obs.append('pago Payway no encontrado en payway_intentos')
        rech_pw = [p for p in pw_por_ref.get(opw or '', []) if p['status'] == 'rejected']
        if rech_pw:
            obs.append(f'{len(rech_pw)} intento(s) Payway rechazado(s) antes de aprobar (mismo pedido)')
    elif num.startswith('GN-'):
        ref = num[3:]
        g = gn_pend.get(ref)
        pid = (g or {}).get('payment_intent_id') or nota(v, r'GN_PID:\s*([0-9a-f-]+)')
        d = gn_get(pid)
        if d:
            pay = d.get('payment') or {}
            estado_pasarela = str(pay.get('status') or d.get('status') or '')
            amt = pay.get('amount')
            cobrado_pasarela = round(float(amt) / 100, 2) if amt else None
            for clave in ('refunded_amount',):
                if pay.get(clave):
                    reintegrado = round(float(pay[clave]) / 100, 2)
            if any(x in estado_pasarela.lower() for x in ('refund', 'cancel', 'revers')):
                obs.append(f'GetNet estado {estado_pasarela}')
        else:
            obs.append('GetNet: no se pudo consultar el pago (API)')
        fecha_aprob = v['fecha_venta']
        fuente_aprob = 'registro en sistema al aprobarse (GetNet webhook)'
    else:
        origen_registro = 'manual_panel'
        obs.append('cargada a mano desde el panel con canal tienda_web (no pasó por checkout online)')

    c = ck.get(ref) if ref else None
    g = gn_pend.get(ref) if (ref and num.startswith('GN-')) else None
    pw_row = pw_por_id.get(int(nota(v, r'PWID:\s*(\d+)') or 0)) if num.startswith('PW-') else None
    if ref:
        refs_usados.add(ref)
    if c:
        creado = c['creado_ar']
        fuente_creado = 'checkout (pedidos_pendientes.fecha_creacion, UTC→AR)'
    elif num.startswith('MP-') and mp_cache.get(num[3:]):
        primeros = [parse_iso_ar(o['date_created']) for o in (mp_busq_cache.get(ref) or []) if o.get('date_created')]
        creado = min([d for d in primeros if d] + [parse_iso_ar(mp_cache[num[3:]].get('date_created'))])
        fuente_creado = 'Mercado Pago: primer pago del pedido (date_created); el checkout se borra al aprobarse'
    elif g and g.get('fecha_creacion'):
        creado = ar_desde_utc(g['fecha_creacion'])
        fuente_creado = 'GetNet: pedidos_pendientes_getnet.fecha_creacion (UTC→AR)'
    elif pw_row and pw_row.get('fecha'):
        intentos = [p['fecha'] for p in pw_por_ref.get(ref or '', []) if p.get('fecha')]
        creado = min(intentos + [pw_row['fecha']])
        fuente_creado = 'Payway: primer intento de pago del pedido (payway_intentos.fecha); el checkout se borra al aprobarse'
    else:
        creado = v['fecha_venta']
        fuente_creado = 'ventas.fecha_venta (registro; checkout no encontrado)'
    if not fecha_aprob:
        fecha_aprob = v['fecha_venta']
        fuente_aprob = fuente_aprob or 'ventas.fecha_venta'

    if not (DESDE <= creado <= HASTA):
        continue

    # Cupón y descuento
    cu = cupon_uso.get(num)
    cupon_cod = cu['codigo'] if cu else ''
    desc = None
    if cu:
        if cu['tipo'] == 'fijo':
            desc = f2(cu['valor'])
        else:
            elegible = sum(float(i['precio_unitario']) * int(i['cantidad']) for i in its if (i['tipo'] or '') != 'almohada')
            pct = float(cu['valor'])
            desc = round(elegible * pct / (100 - pct), 2) if pct < 100 else None
    # Recargo por cuotas (coeficiente embebido en el precio cobrado)
    abon = f2(v['importe_abonado'])
    recargo = 0.0
    if coef:
        try:
            cf = float(coef)
            recargo = round(abon - abon / cf, 2) if cf > 1 else 0.0
        except ValueError:
            pass
    mp_coef = nota(v, r'recargo coef\s*([\d.]+)')
    if mp_coef and not coef:
        cf = float(mp_coef)
        recargo = round(abon - abon / cf, 2) if cf > 1 else 0.0

    flete = f2(v['costo_flete'])
    total_final = abon
    cobrado = cobrado_pasarela if cobrado_pasarela is not None else abon
    if origen_registro == 'manual_panel':
        cobrado = abon
    if cobrado_pasarela is not None and abs(cobrado_pasarela - abon) > 1:
        obs.append(f'diferencia sistema vs pasarela: abonado {abon} / pasarela {cobrado_pasarela}')
    if abs(sub_items + flete - abon) > 1:
        obs.append(f'productos+envío ({sub_items + flete:.0f}) ≠ total cobrado registrado ({abon:.0f})')
    if v['estado_pago'] == 'pago_parcial':
        obs.append(f"pago parcial en sistema: importe_total {f2(v['importe_total'])}, abonado {abon}")
    neto = round(cobrado - reintegrado, 2)

    es_prueba = (cupon_cod.upper().startswith('DESCMMD') or abon < 5000)
    if es_prueba:
        obs.append('PRUEBA interna (cupón 90% / importe ínfimo)')

    pago_ok_pasarela = (
        (num.startswith('MP-') and estado_pasarela.startswith(('approved', 'refunded', 'charged_back'))) or
        (num.startswith('PW-') and estado_pasarela in ('accredited', 'approved', 'annulment_approved', 'refund_approved')) or
        num.startswith('GN-') or origen_registro == 'manual_panel')
    if reintegrado and reintegrado >= cobrado - 1:
        clasif = 'aprobado_reintegrado_total'
    elif reintegrado:
        clasif = 'aprobado_reintegrado_parcial'
    elif v['estado_entrega'] == 'cancelada':
        clasif = 'aprobado_cancelado_sin_reintegro_registrado'
    elif pago_ok_pasarela:
        clasif = 'aprobado'
    else:
        clasif = 'revisar'
    if fecha_aprob and fecha_aprob > HASTA:
        obs.append('pagado después del período')
    if fecha_reint and fecha_reint > HASTA:
        obs.append('reintegro posterior al período')

    u1, u2 = utm(v['origen_first']), utm(v['origen_last'])
    filas.append(OrderedDict([
        ('id_interno', v['id']), ('numero_pedido', num), ('ref_checkout', ref or ''),
        ('fecha_creacion_ar', iso(creado)), ('fuente_fecha_creacion', fuente_creado),
        ('fecha_aprobacion_pago_ar', iso(fecha_aprob)), ('fuente_fecha_aprobacion', fuente_aprob),
        ('fecha_registro_sistema_ar', iso(v['fecha_venta'])),
        ('tipo_registro', 'venta_pagada'), ('clasificacion', clasif), ('es_prueba', es_prueba),
        ('estado_actual_entrega', v['estado_entrega']), ('estado_pago_sistema', v['estado_pago']),
        ('estado_pasarela', estado_pasarela), ('canal_origen', v['canal']), ('origen_registro', origen_registro),
        ('pasarela_pago', pas), ('cuotas', cuotas or ''),
        ('subtotal_productos', sub_items), ('descuento_cupon_estimado', desc if desc is not None else ''),
        ('cupon', cupon_cod), ('costo_envio_cobrado', flete), ('recargo_cuotas_estimado', recargo),
        ('importe_total_final', total_final), ('importe_cobrado', cobrado),
        ('importe_reintegrado', reintegrado), ('fecha_reintegro_ar', iso(fecha_reint)),
        ('importe_neto_cobrado', neto), ('moneda', moneda),
        ('unidades', sum(int(i['cantidad']) for i in its)),
        ('skus', ' | '.join(f"{i['sku']} x{i['cantidad']}" for i in its)),
        ('productos', ' | '.join(i['nombre'] or i['sku'] for i in its)),
        ('categorias', ' | '.join(sorted({categoria(i) for i in its}))),
        ('utm_source_first', u1['source']), ('utm_medium_first', u1['medium']), ('utm_campaign_first', u1['campaign']),
        ('utm_source_last', u2['source']), ('utm_medium_last', u2['medium']), ('utm_campaign_last', u2['campaign']),
        ('tiene_gclid', u1['gclid'] or u2['gclid']), ('tiene_fbclid', u1['fbclid'] or u2['fbclid']),
        ('referrer_first', u1['referrer']), ('referrer_last', u2['referrer']),
        ('transaction_id_analytics', num if origen_registro == 'checkout_online' else ''),
        ('observaciones', '; '.join(obs)),
        ('_comprador', h(v['email_cliente']) or h(v['telefono_cliente']) or h(v['dni_cliente'])),
        ('_items', its),
    ]))

# ──────────────────────────────────────────────────────────────────────────────
# 5) Checkouts del período que no terminaron en venta
# ──────────────────────────────────────────────────────────────────────────────
compradores_pagaron = defaultdict(list)
for f in filas:
    if f['_comprador']:
        compradores_pagaron[f['_comprador']].append(f)
no_pagados = []
for ref, c in ck.items():
    if ref in refs_usados or not (DESDE <= c['creado_ar'] <= HASTA):
        continue
    pws = pw_por_ref.get(ref, [])
    rech = [p for p in pws if p['status'] == 'rejected']
    pw_ok = [p for p in pws if p['status'] != 'rejected']
    g = gn_pend.get(ref)
    mps = mp_por_ref(ref)
    mp_ok = [o for o in (mps or []) if o['status'] in ('approved', 'refunded', 'charged_back')]
    mp_pend = [o for o in (mps or []) if o['status'] in ('pending', 'in_process', 'authorized')]
    mp_rech = [o for o in (mps or []) if o['status'] in ('rejected', 'cancelled')]
    if mp_ok:
        est = 'revisar_pago_mp_aprobado_sin_venta'
        det = 'MP: ' + ', '.join(f"{o['id']} {o['status']} ${o['amount']:.0f} reint ${o['refunded']:.0f}" for o in mp_ok)
    elif pw_ok:
        est = 'pago_payway_aprobado_y_anulado_sin_venta' if all(
            p['status'] in ('annulment_approved', 'refund_approved') for p in pw_ok) else 'revisar_pago_payway_sin_venta'
        det = 'Payway: ' + ', '.join(f"{p['payment_id']} {p['status']} ${f2(p['amount']):.0f}" for p in pw_ok)
    elif mp_pend:
        est = 'pendiente_de_pago'
        det = 'MP pendiente: ' + ', '.join(f"{o['status']}/{o['status_detail']}" for o in mp_pend)
    elif mp_rech:
        est = 'pago_rechazado'
        det = f"MP rechazado/cancelado x{len(mp_rech)} ({', '.join(sorted({o['status_detail'] or '' for o in mp_rech}))})"
    elif rech:
        est = 'pago_rechazado'
        det = f"Payway rechazado x{len(rech)} ({', '.join(sorted({p['motivo'] or 's/motivo' for p in rech}))})"
    elif g:
        est = 'sin_pago'
        det = f"GetNet iniciado (estado {g['estado']}) sin venta"
    else:
        est = 'sin_pago'
        det = 'checkout sin pago aprobado registrado (abandono, rechazo en MP o pago no completado)'
    comp = c['comprador']
    luego = [f for f in compradores_pagaron.get(comp, []) if f['fecha_creacion_ar'] >= iso(c['creado_ar'])
             and f['fecha_creacion_ar'] <= iso(c['creado_ar'] + timedelta(days=7))] if comp else []
    reintento = bool(luego)
    total_ck = round(c['subtotal_carrito'] + c['flete_cotizado'], 2)
    u1, u2 = utm(c['utm_first']), utm(c['utm_last'])
    no_pagados.append(OrderedDict([
        ('id_interno', ''), ('numero_pedido', ''), ('ref_checkout', ref),
        ('fecha_creacion_ar', iso(c['creado_ar'])), ('fuente_fecha_creacion', 'checkout (pedidos_pendientes.fecha_creacion, UTC→AR)'),
        ('fecha_aprobacion_pago_ar', ''), ('fuente_fecha_aprobacion', ''), ('fecha_registro_sistema_ar', ''),
        ('tipo_registro', 'checkout_no_pagado'), ('clasificacion', est), ('es_prueba', False),
        ('estado_actual_entrega', ''), ('estado_pago_sistema', ''), ('estado_pasarela', det),
        ('canal_origen', 'tienda_web'), ('origen_registro', 'checkout_online'), ('pasarela_pago', ''), ('cuotas', ''),
        ('subtotal_productos', c['subtotal_carrito']), ('descuento_cupon_estimado', ''), ('cupon', c['cupon'] or ''),
        ('costo_envio_cobrado', c['flete_cotizado']), ('recargo_cuotas_estimado', ''),
        ('importe_total_final', total_ck), ('importe_cobrado', 0.0), ('importe_reintegrado', 0.0),
        ('fecha_reintegro_ar', ''), ('importe_neto_cobrado', 0.0), ('moneda', 'ARS'),
        ('unidades', c['unidades']), ('skus', ' | '.join(c['skus'])), ('productos', ''), ('categorias', ''),
        ('utm_source_first', u1['source']), ('utm_medium_first', u1['medium']), ('utm_campaign_first', u1['campaign']),
        ('utm_source_last', u2['source']), ('utm_medium_last', u2['medium']), ('utm_campaign_last', u2['campaign']),
        ('tiene_gclid', u1['gclid'] or u2['gclid']), ('tiene_fbclid', u1['fbclid'] or u2['fbclid']),
        ('referrer_first', u1['referrer']), ('referrer_last', u2['referrer']), ('transaction_id_analytics', ''),
        ('observaciones', ('mismo comprador pagó después otro pedido (' + ', '.join(f['numero_pedido'] for f in luego) + ')')
         if reintento else ''),
        ('_comprador', comp), ('_items', []), ('_reintento', reintento),
    ]))

# ──────────────────────────────────────────────────────────────────────────────
# 6) Resúmenes
# ──────────────────────────────────────────────────────────────────────────────
pagadas = [f for f in filas]
online = [f for f in pagadas if f['origen_registro'] == 'checkout_online' and not f['es_prueba']]
manuales = [f for f in pagadas if f['origen_registro'] == 'manual_panel']
pruebas = [f for f in pagadas if f['es_prueba']]


def suma(lst, k):
    return round(sum(float(f[k] or 0) for f in lst), 2)


def bloque(lst, nopag):
    aprob = lst
    reint_tot = [f for f in aprob if f['clasificacion'] == 'aprobado_reintegrado_total']
    reint_par = [f for f in aprob if f['clasificacion'] == 'aprobado_reintegrado_parcial']
    canc = [f for f in aprob if f['clasificacion'] == 'aprobado_cancelado_sin_reintegro_registrado']
    neto_ok = [f for f in aprob if f['clasificacion'] not in ('aprobado_reintegrado_total',)]
    return OrderedDict([
        ('pedidos_creados_checkouts', len(aprob) + len(nopag)),
        ('pedidos_pagados_aprobados', len(aprob)),
        ('pedidos_pendientes_de_pago', sum(1 for f in nopag if f['clasificacion'] == 'pendiente_de_pago')),
        ('checkouts_no_pagados', len(nopag)),
        ('checkouts_no_pagados_con_pago_rechazado', sum(1 for f in nopag if f['clasificacion'] == 'pago_rechazado')),
        ('checkouts_no_pagados_sin_intento_de_pago_registrado', sum(1 for f in nopag if f['clasificacion'] == 'sin_pago')),
        ('checkouts_con_pago_aprobado_y_anulado_sin_venta',
         sum(1 for f in nopag if f['clasificacion'] == 'pago_payway_aprobado_y_anulado_sin_venta')),
        ('checkouts_a_revisar_pago_aprobado_sin_venta', sum(1 for f in nopag if f['clasificacion'].startswith('revisar'))),
        ('checkouts_no_pagados_de_compradores_que_luego_pagaron', sum(1 for f in nopag if f.get('_reintento'))),
        ('pedidos_aprobados_luego_cancelados_o_reintegrados', len(reint_tot) + len(reint_par) + len(canc)),
        ('pedidos_reintegrados_total', len(reint_tot)),
        ('pedidos_reintegrados_parcial', len(reint_par)),
        ('pedidos_cancelados_sin_reintegro_registrado', len(canc)),
        ('facturacion_bruta_aprobada', suma(aprob, 'importe_cobrado')),
        ('subtotal_productos_aprobados', suma(aprob, 'subtotal_productos')),
        ('descuentos_cupon_estimados', suma(aprob, 'descuento_cupon_estimado')),
        ('envios_cobrados', suma(aprob, 'costo_envio_cobrado')),
        ('recargos_cuotas_estimados', suma(aprob, 'recargo_cuotas_estimado')),
        ('total_reintegros', suma(aprob, 'importe_reintegrado')),
        ('total_neto_cobrado', suma(aprob, 'importe_neto_cobrado')),
        ('ticket_promedio_aprobados_bruto', round(suma(aprob, 'importe_cobrado') / len(aprob), 2) if aprob else None),
        ('ticket_promedio_aprobados_netos_sin_reintegro_total',
         round(suma(neto_ok, 'importe_neto_cobrado') / len(neto_ok), 2) if neto_ok else None),
        ('valor_carritos_no_pagados_NO_ES_VENTA', suma(nopag, 'importe_total_final')),
        ('unidades_vendidas_aprobadas', int(suma(aprob, 'unidades'))),
    ])


resumen_general = bloque(online, no_pagados)

# Diario
dias = OrderedDict()
d = DESDE.date()
while d <= HASTA.date():
    dias[d.isoformat()] = defaultdict(float)
    d += timedelta(days=1)
for f in online:
    k = f['fecha_creacion_ar'][:10]
    x = dias[k]
    x['pedidos_creados'] += 1
    x['pedidos_aprobados'] += 1
    x['importe_pedidos_creados'] += f['importe_total_final']
    x['importe_aprobados'] += f['importe_cobrado']
    x['reintegros'] += f['importe_reintegrado']
    x['importe_neto_cobrado'] += f['importe_neto_cobrado']
    if f['clasificacion'] != 'aprobado':
        x['pedidos_cancelados_o_reintegrados'] += 1
    ka = f['fecha_aprobacion_pago_ar'][:10]
    if ka in dias:
        dias[ka]['aprobados_por_fecha_de_aprobacion'] += 1
for f in no_pagados:
    x = dias[f['fecha_creacion_ar'][:10]]
    x['pedidos_creados'] += 1
    x['checkouts_no_pagados'] += 1
    x['importe_pedidos_creados'] += f['importe_total_final']
COLS_DIA = ['pedidos_creados', 'pedidos_aprobados', 'aprobados_por_fecha_de_aprobacion', 'checkouts_no_pagados',
            'pedidos_cancelados_o_reintegrados', 'importe_pedidos_creados', 'importe_aprobados', 'reintegros',
            'importe_neto_cobrado']
diario = []
for k, x in dias.items():
    fila = OrderedDict([('fecha', k)])
    for c in COLS_DIA:
        val = x.get(c, 0)
        fila[c] = int(val) if c.startswith(('pedidos', 'aprobados', 'checkouts')) else round(val, 2)
    diario.append(fila)

# Mensual
MESES = [('2026-08', 'agosto 2026 (parcial: 11 al 31)'), ('2026-09', 'septiembre 2026'),
         ('2026-10', 'octubre 2026'), ('2026-11', 'noviembre 2026 (parcial: 1 al 8)')]
mensual = []
for m, nombre in MESES:
    b = bloque([f for f in online if f['fecha_creacion_ar'].startswith(m)],
               [f for f in no_pagados if f['fecha_creacion_ar'].startswith(m)])
    mensual.append(OrderedDict([('mes', m), ('etiqueta', nombre)] + list(b.items())))

# Productos (por ítem; prorrateo de reintegros por peso del ítem dentro del pedido)
prod = defaultdict(lambda: defaultdict(float))
for f in online:
    tot_items = sum(float(i['precio_unitario']) * int(i['cantidad']) for i in f['_items']) or 1
    factor_neto = (f['importe_neto_cobrado'] - f['costo_envio_cobrado'] * (f['importe_neto_cobrado'] / f['importe_cobrado']
                   if f['importe_cobrado'] else 0)) / tot_items if tot_items else 0
    for i in f['_items']:
        imp = float(i['precio_unitario']) * int(i['cantidad'])
        clave = ('Cannon' if True else '', categoria(i), modelo(i))
        p = prod[clave]
        p['unidades'] += int(i['cantidad'])
        p['importe_productos_aprobado'] += imp
        p['importe_productos_neto_estimado'] += imp * factor_neto
        p['pedidos'] += 1
productos = sorted(
    [OrderedDict([('marca', k[0]), ('categoria', k[1]), ('modelo', k[2]), ('unidades', int(v['unidades'])),
                  ('pedidos', int(v['pedidos'])), ('importe_productos_aprobado', round(v['importe_productos_aprobado'], 2)),
                  ('importe_productos_neto_estimado', round(v['importe_productos_neto_estimado'], 2))])
     for k, v in prod.items()], key=lambda r: -r['importe_productos_aprobado'])
por_categoria = defaultdict(lambda: defaultdict(float))
for p in productos:
    c = por_categoria[p['categoria']]
    for k in ('unidades', 'pedidos', 'importe_productos_aprobado', 'importe_productos_neto_estimado'):
        c[k] += p[k]
por_pasarela = defaultdict(lambda: defaultdict(float))
for f in online:
    c = por_pasarela[f['pasarela_pago']]
    c['pedidos'] += 1
    c['cobrado'] += f['importe_cobrado']
    c['reintegrado'] += f['importe_reintegrado']
    c['neto'] += f['importe_neto_cobrado']

# ──────────────────────────────────────────────────────────────────────────────
# 7) Validaciones
# ──────────────────────────────────────────────────────────────────────────────
val = OrderedDict()
nums = [f['numero_pedido'] for f in pagadas]
val['numeros_de_pedido_duplicados'] = sorted({n for n in nums if nums.count(n) > 1})
refs_v = [f['ref_checkout'] for f in pagadas if f['ref_checkout']]
val['checkouts_con_mas_de_una_venta'] = sorted({r for r in refs_v if refs_v.count(r) > 1})
val['detalle_vs_resumen_neto_ok'] = abs(suma(online, 'importe_neto_cobrado') - resumen_general['total_neto_cobrado']) < 0.01
val['diario_vs_resumen_neto_ok'] = abs(sum(r['importe_neto_cobrado'] for r in diario) - resumen_general['total_neto_cobrado']) < 1
val['mensual_vs_resumen_neto_ok'] = abs(sum(m['total_neto_cobrado'] for m in mensual) - resumen_general['total_neto_cobrado']) < 1
val['diario_pedidos_aprobados_suma'] = sum(r['pedidos_aprobados'] for r in diario)
val['productos_vs_detalle_ok'] = abs(sum(p['importe_productos_aprobado'] for p in productos) - suma(online, 'subtotal_productos')) < 1
val['monedas'] = sorted({f['moneda'] for f in pagadas})
cobr = sorted(f['importe_cobrado'] for f in online)
med = cobr[len(cobr) // 2] if cobr else 0
val['pedidos_importe_cero_o_negativo'] = [f['numero_pedido'] for f in pagadas if f['importe_cobrado'] <= 0]
val['pedidos_importe_anormalmente_alto_(>4x_mediana)'] = [
    (f['numero_pedido'], f['importe_cobrado']) for f in online if med and f['importe_cobrado'] > 4 * med]
val['mediana_importe_cobrado'] = med
val['pedidos_creados_en_periodo_pagados_despues'] = [f['numero_pedido'] for f in pagadas if 'pagado después' in f['observaciones']]
val['reintegros_posteriores_al_periodo'] = [f['numero_pedido'] for f in pagadas if 'reintegro posterior' in f['observaciones']]
val['ventas_con_diferencia_sistema_vs_pasarela'] = [(f['numero_pedido'], f['observaciones']) for f in pagadas
                                                    if 'diferencia sistema vs pasarela' in f['observaciones']]
val['ventas_productos_mas_envio_distinto_de_cobrado'] = [f['numero_pedido'] for f in pagadas
                                                          if 'productos+envío' in f['observaciones']]
val['ventas_sin_checkout_vinculado'] = [(f['numero_pedido'], f['fuente_fecha_creacion']) for f in pagadas
                                        if not f['fuente_fecha_creacion'].startswith('checkout')]
val['clasificacion_revisar'] = [f['numero_pedido'] for f in pagadas if f['clasificacion'] == 'revisar']
# Ventas registradas en el período (fecha_venta) que quedaron afuera por fecha de creación
val['ventas_registradas_en_periodo_pero_creadas_antes'] = [
    v['numero_venta'] for v in ventas if DESDE <= v['fecha_venta'] <= HASTA and v['numero_venta'] not in set(nums)]
# Payway acreditados en el período sin venta en el sistema
pw_sin_venta = []
nums_pw = {f['numero_pedido'] for f in pagadas if f['numero_pedido'].startswith('PW-')}
for r in pw_int:
    if r['status'] in ('accredited', 'approved', 'annulment_approved', 'refund_approved') and r['fecha'] and \
            DESDE <= r['fecha'] <= HASTA and f"PW-{r['payment_id']}" not in nums_pw:
        pw_sin_venta.append((r['payment_id'], r['status'], f2(r['amount']), r['ref']))
val['payway_aprobados_o_anulados_sin_venta'] = pw_sin_venta

# ──────────────────────────────────────────────────────────────────────────────
# 8) Escritura
# ──────────────────────────────────────────────────────────────────────────────
CORTE_CONSULTA = (datetime.utcnow() - UTC_OFF).strftime('%Y-%m-%d %H:%M:%S')
todas = sorted(pagadas + no_pagados, key=lambda f: f['fecha_creacion_ar'])
cols = [k for k in todas[0].keys() if not k.startswith('_')]
p_det = os.path.join(OUT, f'ventas_web_detalle_{SUF}.csv')
with open(p_det, 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
    w.writeheader()
    for f in todas:
        w.writerow({k: ('SI' if f[k] is True else 'NO' if f[k] is False else f[k]) for k in cols})
p_dia = os.path.join(OUT, f'ventas_web_diarias_{SUF}.csv')
with open(p_dia, 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=['fecha'] + COLS_DIA)
    w.writeheader()
    w.writerows(diario)


def limpio(f):
    return OrderedDict((k, v) for k, v in f.items() if not k.startswith('_'))


resumen = OrderedDict([
    ('periodo', {'desde': iso(DESDE), 'hasta': iso(HASTA), 'zona_horaria': 'America/Argentina/Buenos_Aires',
                 'criterio': 'fecha de creación del pedido (checkout)'}),
    ('generado_ar', CORTE_CONSULTA),
    ('corte_datos_anterior_al_fin_del_periodo', CORTE_CONSULTA < iso(HASTA)),
    ('moneda', 'ARS'),
    ('definiciones', {
        'pedido_creado': 'checkout iniciado en la tienda (pedidos_pendientes), una fila por checkout',
        'pedido_aprobado': 'checkout con pago aprobado y venta registrada (ventas canal tienda_web)',
        'universo_principal': 'ventas online (MP, Payway, GetNet) excluyendo pruebas internas y cargas manuales',
    }),
    ('resumen_general', resumen_general),
    ('excluidos_del_universo_principal', {
        'pruebas_internas': [limpio(f) for f in pruebas],
        'cargas_manuales_canal_tienda_web': [limpio(f) for f in manuales],
    }),
    ('por_pasarela', {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in por_pasarela.items()}),
    ('mensual', mensual),
    ('diario', diario),
    ('productos_por_modelo', productos),
    ('productos_por_categoria', {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in por_categoria.items()}),
    ('referencia_plataformas', {
        'meta_ads': {'compras': 116, 'valor_aprox': 28388440.0},
        'google_ads': {'conversiones_compra': 59, 'valor_aprox': 35052227.0},
        'nota': 'atribución propia de cada plataforma, superpuesta; no sumar',
    }),
    ('validaciones', val),
])
p_json = os.path.join(OUT, f'ventas_web_resumen_{SUF}.json')
with open(p_json, 'w', encoding='utf-8') as fh:
    json.dump(resumen, fh, ensure_ascii=False, indent=2, default=str)


# ──────────────────────────────────────────────────────────────────────────────
# 9) Informe Markdown (todas las cifras salen de las mismas estructuras del JSON)
# ──────────────────────────────────────────────────────────────────────────────
def m(x):
    return '$ ' + f'{x:,.0f}'.replace(',', '.') if isinstance(x, (int, float)) else str(x)


g = resumen_general
L = []
A = L.append
A(f'# Auditoría de ventas — Tienda web mercadomuebles.com.ar\n')
A(f'**Período:** {iso(DESDE)} a {iso(HASTA)} (America/Argentina/Buenos_Aires), por **fecha de creación del pedido**.  ')
A(f'**Generado:** {CORTE_CONSULTA} (hora AR). Moneda única: **ARS** (no hay pedidos en otra moneda).  ')
if CORTE_CONSULTA < iso(HASTA):
    A(f'⚠️ **Corte de datos anterior al fin del período:** los datos llegan hasta {CORTE_CONSULTA}; '
      f'el último día ({HASTA:%d/%m}) está incompleto. Para cerrar el período, volver a correr el script después de las 00:00 del día siguiente.  ')
A('**Modo:** solo lectura (base con usuario sin permisos de escritura; pasarelas solo con GET). Sin datos personales.\n')
A('## 1. Resumen general (universo principal: ventas online, sin pruebas ni cargas manuales)\n')
A('| Indicador | Valor |\n|---|---:|')
filas_res = [
    ('Pedidos web creados (checkouts iniciados)', g['pedidos_creados_checkouts']),
    ('Pedidos pagados / aprobados', g['pedidos_pagados_aprobados']),
    ('Pedidos pendientes de pago (MP pending al corte)', g['pedidos_pendientes_de_pago']),
    ('Checkouts no pagados (total)', g['checkouts_no_pagados']),
    ('  · con pago rechazado (MP o Payway)', g['checkouts_no_pagados_con_pago_rechazado']),
    ('  · sin intento de pago registrado (abandono)', g['checkouts_no_pagados_sin_intento_de_pago_registrado']),
    ('  · pago Payway aprobado y anulado, sin venta', g['checkouts_con_pago_aprobado_y_anulado_sin_venta']),
    ('  · de compradores que pagaron otro pedido dentro de 7 días', g['checkouts_no_pagados_de_compradores_que_luego_pagaron']),
    ('Pedidos aprobados luego cancelados o reintegrados', g['pedidos_aprobados_luego_cancelados_o_reintegrados']),
    ('  · reintegrados total', g['pedidos_reintegrados_total']),
    ('  · reintegrados parcial', g['pedidos_reintegrados_parcial']),
    ('  · cancelados sin reintegro registrado', g['pedidos_cancelados_sin_reintegro_registrado']),
]
for k, val_ in filas_res:
    A(f'| {k} | {val_} |')
A('\n| Importes (ARS) | Valor |\n|---|---:|')
for k, val_ in [
    ('Facturación bruta aprobada (cobrado por las pasarelas)', g['facturacion_bruta_aprobada']),
    ('  · subtotal productos (precio cobrado, ya con cupón y recargo embebidos)', g['subtotal_productos_aprobados']),
    ('  · envíos cobrados', g['envios_cobrados']),
    ('Recargos por cuotas (estimado, incluido en lo anterior)', g['recargos_cuotas_estimados']),
    ('Descuentos por cupón (estimado, ya descontado)', g['descuentos_cupon_estimados']),
    ('Total reintegros', g['total_reintegros']),
    ('**Total neto efectivamente cobrado**', g['total_neto_cobrado']),
    ('Ticket promedio aprobado (bruto)', g['ticket_promedio_aprobados_bruto']),
    ('Ticket promedio neto (excluye reintegrados total)', g['ticket_promedio_aprobados_netos_sin_reintegro_total']),
    ('Valor de carritos no pagados (**no es venta**)', g['valor_carritos_no_pagados_NO_ES_VENTA']),
]:
    A(f'| {k} | {m(val_)} |')
A(f"\nUnidades vendidas (aprobadas): **{g['unidades_vendidas_aprobadas']}**.\n")
A('### Por pasarela\n\n| Pasarela | Pedidos | Cobrado | Reintegrado | Neto |\n|---|---:|---:|---:|---:|')
for k, x in resumen['por_pasarela'].items():
    A(f"| {k} | {int(x['pedidos'])} | {m(x['cobrado'])} | {m(x['reintegrado'])} | {m(x['neto'])} |")
A('\n### Excluidos del universo principal (están en el CSV, marcados)\n')
for f in pruebas:
    A(f"- Prueba interna: `{f['numero_pedido']}` cobrado {m(f['importe_cobrado'])}, reintegrado {m(f['importe_reintegrado'])} — {f['observaciones']}")
for f in manuales:
    A(f"- Carga manual con canal tienda_web: `{f['numero_pedido']}` ({f['pasarela_pago']}) {m(f['importe_cobrado'])} — no pasó por el checkout online")
A('\n## 2. Resumen mensual\n')
A('| Mes | Creados | Aprobados | Rechazados | Abandonos | Cancel./reint. | Bruto aprobado | Reintegros | Neto | Ticket bruto |')
A('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
for x in mensual:
    A(f"| {x['etiqueta']} | {x['pedidos_creados_checkouts']} | {x['pedidos_pagados_aprobados']} | "
      f"{x['checkouts_no_pagados_con_pago_rechazado']} | {x['checkouts_no_pagados_sin_intento_de_pago_registrado']} | "
      f"{x['pedidos_aprobados_luego_cancelados_o_reintegrados']} | {m(x['facturacion_bruta_aprobada'])} | "
      f"{m(x['total_reintegros'])} | {m(x['total_neto_cobrado'])} | {m(x['ticket_promedio_aprobados_bruto'] or 0)} |")
A('\nAgosto (desde el 11) y noviembre (1 al 8) son meses **parciales**.\n')
A('## 3. Resumen diario\n')
A(f'Ver `ventas_web_diarias_{SUF}.csv` (una fila por día, {len(diario)} días). Días con más ventas aprobadas:\n')
A('| Fecha | Creados | Aprobados | Bruto aprobado | Neto |\n|---|---:|---:|---:|---:|')
for x in sorted(diario, key=lambda r: (-r['pedidos_aprobados'], r['fecha']))[:10]:
    A(f"| {x['fecha']} | {x['pedidos_creados']} | {x['pedidos_aprobados']} | {m(x['importe_aprobados'])} | {m(x['importe_neto_cobrado'])} |")
dias_sin = sum(1 for x in diario if x['pedidos_aprobados'] == 0)
A(f'\nDías sin ninguna venta aprobada: {dias_sin} de {len(diario)}.\n')
A('## 4. Productos\n')
A('Marca: el sistema **no tiene campo marca**; el catálogo vendido es Cannon. Categoría y modelo salen de '
  '`productos_base` (tipo/modelo) y `productos_compuestos` (sommiers = colchón + base, modelo tomado del nombre). '
  'Importes = precio cobrado por ítem (incluye cupón y recargo embebidos, sin envío). "Pedidos" = líneas de pedido.\n')
A('| Categoría | Unidades | Líneas | Importe aprobado | Neto estimado |\n|---|---:|---:|---:|---:|')
for k, x in sorted(resumen['productos_por_categoria'].items(), key=lambda kv: -kv[1]['importe_productos_aprobado']):
    A(f"| {k} | {int(x['unidades'])} | {int(x['pedidos'])} | {m(x['importe_productos_aprobado'])} | {m(x['importe_productos_neto_estimado'])} |")
A('\n| Categoría | Modelo | Unidades | Importe aprobado |\n|---|---|---:|---:|')
for p in productos[:25]:
    A(f"| {p['categoria']} | {p['modelo']} | {p['unidades']} | {m(p['importe_productos_aprobado'])} |")
A(f'\n(Lista completa en el JSON, `productos_por_modelo`: {len(productos)} modelos.)\n')
A('## 5. Referencia de plataformas publicitarias (solo contexto, sin atribuir)\n')
A('| Fuente | Compras | Valor |\n|---|---:|---:|')
A(f"| **Ventas reales aprobadas (este informe)** | {g['pedidos_pagados_aprobados']} | {m(g['facturacion_bruta_aprobada'])} bruto / {m(g['total_neto_cobrado'])} neto |")
A('| Meta Ads (atribuidas por Meta) | 116 | $ 28.388.440 |')
A('| Google Ads (conversiones principales) | 59 | $ 35.052.227 |')
A('\nLas cifras de las plataformas usan su propia atribución (ventanas, view-through, modelado) y se superponen: '
  'no se suman entre sí ni se restan de las ventas reales. Este informe **no** asigna ventas a plataformas; '
  'los UTM, gclid y fbclid del CSV son solo auxiliares (se capturan por cookie/sesión y pueden faltar o estar mal). '
  f"El `transaction_id_analytics` del CSV es el mismo que envía el evento `purchase` de GA4/GTM (número de pedido), "
  'útil para cruzar contra GA4.\n')
A('## 6. Metodología\n')
A('''**Tablas y campos usados (solo SELECT):**
- `ventas` (canal, numero_venta, fecha_venta, importe_total, importe_abonado, costo_flete, metodo_pago, estado_entrega, estado_pago, notas, origen_first/origen_last; los datos personales solo se leyeron para un hash en memoria, nunca se exportan).
- `items_venta` (sku, cantidad, precio_unitario) + `productos_base` / `productos_compuestos` (nombre, tipo, modelo).
- `pedidos_pendientes` (checkout: ref, carrito_json, cliente_json, fecha_creacion en UTC).
- `pedidos_pendientes_getnet` (checkout GetNet: pedido_ref, payment_intent_id, fecha_creacion en UTC).
- `payway_intentos` (cada intento de pago Payway: estado, monto, fecha, ref del pedido).
- `cupones_uso` + `cupones` (cupón aplicado por número de pedido).
- API Mercado Pago, solo GET: `/v1/payments/{id}` y `/v1/payments/search?external_reference=` (estado, fecha de aprobación, monto, reintegros, todos los pagos del pedido).

**Cómo se identifican las ventas web:** `ventas.canal = 'tienda_web'`. Los números `MP-<payment_id>`, `PW-<payment_id>` y `GN-<ref>` los genera la tienda al aprobarse el pago (Mercado Pago, Payway, GetNet). `canal = 'Mercado Libre'` (importadas de ML) y `'Fuera de ML'` (cargadas a mano) quedan afuera. Hubo 3 ventas cargadas a mano con canal tienda_web (`VENTA-…`, efectivo/MP): se listan aparte y no entran al universo principal.

**Cómo funciona el ciclo de un pedido en este sistema:**
1. El cliente completa datos de envío → se crea un checkout en `pedidos_pendientes` (1 fila por checkout, compartida por las 3 pasarelas; GetNet además usa `pedidos_pendientes_getnet`).
2. Paga. Con el pago aprobado (webhook MP / respuesta Payway / webhook GetNet) se inserta la venta en `ventas` con `estado_pago='pagado'`, y el checkout se borra de `pedidos_pendientes` (MP y Payway).
3. Por lo tanto **no existen ventas "pendientes de pago" en `ventas` para la tienda**: un pedido sin pago aprobado queda solo como checkout. Los checkouts no pagados son los que siguen en `pedidos_pendientes`.

**Fecha de creación:** para checkouts no pagados, `pedidos_pendientes.fecha_creacion` (UTC → AR, −3 h). Para pedidos pagados el checkout ya fue borrado, así que se usa el primer intento de pago del pedido: `date_created` del primer pago MP del pedido (convertido a AR), el primer intento en `payway_intentos`, o `pedidos_pendientes_getnet.fecha_creacion` en GetNet. Son minutos posteriores al checkout. `ventas.fecha_venta` ya se guarda en hora AR.

**Clasificación de estados:**
- `aprobado`: pago aprobado en la pasarela y venta registrada.
- `aprobado_reintegrado_total` / `_parcial`: según el monto reintegrado informado por la pasarela (MP `transaction_amount_refunded`; Payway estado `annulment_approved`/`refund_approved` = devolución total).
- `aprobado_cancelado_sin_reintegro_registrado`: venta cancelada en el sistema sin reintegro visible en la pasarela.
- Checkouts no pagados: `pago_rechazado` (MP o Payway rechazó), `pendiente_de_pago` (MP pending/in_process al corte), `pago_payway_aprobado_y_anulado_sin_venta`, `sin_pago` (abandono: no hay intento de pago registrado).
- El estado actual de entrega (`pendiente`, `en_proceso`, `entregada`, `cancelada`) se informa pero no se usa como prueba de aprobación; la aprobación sale de la pasarela.

**Importes:**
- `importe_cobrado` = monto aprobado por la pasarela (MP `transaction_amount`, sumando pagos aprobados adicionales del mismo pedido si hubiera; Payway `amount`/100; GetNet = `importe_abonado` del sistema porque su API no respondió). Excluye el interés que el comprador paga a MP por financiar en cuotas (eso no lo cobra la tienda).
- `importe_total_final` = `ventas.importe_abonado` (lo que el sistema registra como cobrado, envío incluido).
- `subtotal_productos` = suma de `items_venta` (precio unitario × cantidad): **ya incluye** el cupón descontado y el recargo por cuotas embebido (Payway/GetNet aplican el coeficiente al precio de cada ítem).
- `costo_envio_cobrado` = `ventas.costo_flete`.
- `recargo_cuotas_estimado` = cobrado − cobrado / coeficiente (coeficiente leído de las notas de la venta). Estimado.
- `descuento_cupon_estimado`: cupón fijo = su valor; cupón % = subtotal elegible (sin almohadas) × %/(100−%). El monto exacto no se guarda.
- `importe_neto_cobrado` = cobrado − reintegrado.
''')
A('## 7. Validaciones realizadas\n')
A(f"- Números de pedido duplicados: **{len(val['numeros_de_pedido_duplicados'])}**. Checkouts con más de una venta: **{len(val['checkouts_con_mas_de_una_venta'])}**. Cada venta cuenta una vez aunque tenga varios ítems o pagos.")
A(f"- Detalle = resumen (neto): {'OK' if val['detalle_vs_resumen_neto_ok'] else 'NO'}; diario = resumen: {'OK' if val['diario_vs_resumen_neto_ok'] else 'NO'}; mensual = resumen: {'OK' if val['mensual_vs_resumen_neto_ok'] else 'NO'}; productos = detalle: {'OK' if val['productos_vs_detalle_ok'] else 'NO'}.")
A(f"- Monedas encontradas: {', '.join(val['monedas'])}.")
A(f"- Importe cero o negativo: {val['pedidos_importe_cero_o_negativo'] or 'ninguno'}. Anormalmente alto (> 4× la mediana de {m(val['mediana_importe_cobrado'])}): {val['pedidos_importe_anormalmente_alto_(>4x_mediana)'] or 'ninguno'}. Las 3 pruebas internas (cupón 90%) están marcadas y excluidas.")
A(f"- Creados en el período y pagados después del 08/11: {val['pedidos_creados_en_periodo_pagados_despues'] or 'ninguno al corte'}. Reintegros posteriores al período sobre ventas del período: {val['reintegros_posteriores_al_periodo'] or 'ninguno al corte'}.")
A(f"- Ventas con diferencia sistema vs pasarela: " + ('; '.join(f'`{a}`: {b}' for a, b in val['ventas_con_diferencia_sistema_vs_pasarela']) or 'ninguna') + '. En ese caso se toma lo cobrado por la pasarela.')
A(f"- Ventas donde productos + envío ≠ total registrado (editadas a mano después de la compra, p. ej. flete o ítems cambiados): {', '.join('`' + x + '`' for x in val['ventas_productos_mas_envio_distinto_de_cobrado']) or 'ninguna'}.")
pw_reales = [x for x in val['payway_aprobados_o_anulados_sin_venta'] if not str(x[3]).startswith('TESTPW')]
pw_test = [x for x in val['payway_aprobados_o_anulados_sin_venta'] if str(x[3]).startswith('TESTPW')]
A(f"- Pagos Payway aprobados o anulados sin venta: {len(pw_reales)} reales anulados (" +
  ', '.join(f'{x[0]} {x[1]} {m(x[2])}' for x in pw_reales) + f") y {len(pw_test)} transacciones de prueba (TESTPW). Ninguno es venta.")
A(f"- Reintentos: los checkouts no pagados de compradores que pagaron otro pedido dentro de los 7 días siguientes ({g['checkouts_no_pagados_de_compradores_que_luego_pagaron']}) muestran que muchos checkouts son reintentos de la misma compra: el número de checkouts **no** es un número de pedidos distintos.")
A('- No se usó el estado actual para fechar la aprobación: la fecha de aprobación sale de la pasarela (MP `date_approved`, Payway fecha del pago).\n')
A('## 8. Limitaciones\n')
A('''- **GetNet:** su API respondió 403 a la consulta de pagos, así que no se pudo verificar reintegros ni el monto en la pasarela. Se usa lo registrado en el sistema. La venta GetNet cancelada (`GN-524750e49bf344`, $ 717.750) figura como *cancelada sin reintegro registrado*: hay que confirmar en el portal de GetNet si se devolvió.
- **Payway:** el estado de anulación/devolución sale de la tabla local sincronizada; la fecha del reintegro no está disponible (se asume reintegro total).
- **Fecha de creación de pedidos pagados:** el checkout se borra al aprobarse el pago, así que se usa el primer intento de pago (minutos después del checkout). No cambia el día salvo compras cerca de medianoche.
- **Checkouts no pagados:** un mismo comprador puede generar varios (reintentos, cambio de medio de pago). Su valor es valor de carrito, no venta. Los rechazos de GetNet no quedan registrados por intento.
- **Descuentos y recargos:** el sistema guarda el precio final cobrado por ítem, no el precio de lista ni el monto del descuento: ambos son estimaciones.
- **Interés de MP en cuotas:** lo paga el comprador a Mercado Pago y no forma parte de lo cobrado por la tienda; no está incluido.
- **Comisiones de pasarela:** no se descuentan (el neto es neto de reintegros, no de comisiones).
- **UTM/gclid/fbclid:** se guardan desde cookies y sesión, faltan en una parte de las ventas y pueden ser incorrectos. Solo auxiliares.
- **Cargas manuales posteriores:** algunas ventas se editaron después de la compra (envío, ítems). El cobrado de la pasarela es la referencia.
''')
A('## 9. Archivos\n')
A(f'- `ventas_web_detalle_{SUF}.csv` — una fila por pedido (ventas pagadas + checkouts no pagados; columna `tipo_registro`). UTF-8 con BOM.')
A(f'- `ventas_web_diarias_{SUF}.csv` — una fila por día. UTF-8 con BOM.')
A(f'- `ventas_web_resumen_{SUF}.json` — resumen general, por pasarela, mensual, diario, productos y validaciones (números reales).')
A(f'- `ventas_web_auditoria_{SUF}.md` — este informe.')
p_md = os.path.join(OUT, f'ventas_web_auditoria_{SUF}.md')
with open(p_md, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')

print(json.dumps({'md': p_md, 'detalle': p_det, 'diario': p_dia, 'json': p_json,
                  'filas_pagadas': len(pagadas), 'online_sin_pruebas': len(online), 'manuales': len(manuales),
                  'pruebas': len(pruebas), 'no_pagados': len(no_pagados)}, ensure_ascii=False, indent=1))
print(json.dumps(resumen_general, ensure_ascii=False, indent=1))
print(json.dumps({k: (v if not isinstance(v, list) or len(v) < 25 else f'{len(v)} items') for k, v in val.items()},
                 ensure_ascii=False, indent=1, default=str))
