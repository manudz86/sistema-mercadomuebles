"""Integración con ClearSale (antifraude) para las ventas de Payway.

Diseño, y por qué:

* **Nunca rompe el cobro.** Todo lo de acá corre en un hilo aparte y con
  try/except: si ClearSale está caído, lento o devuelve basura, la venta ya
  quedó registrada y el cliente ya vio su pantalla de éxito. Un antifraude
  que voltea cobros es peor que no tener antifraude.

* **Se verifica lo enviado.** ClearSale responde 200 con estado NVO aunque
  después descarte la orden (comprobado en sandbox: payload con un
  CustomField de nombre no permitido). Por eso después de enviar se
  consulta: si la orden no existe, queda registrado como error en vez de
  dejar la venta esperando un webhook que nunca va a llegar.

* **Una orden por llamada.** Si un lote tiene una orden inválida, ClearSale
  descarta el lote entero y responde 200 para todas.

El interruptor es la clave `clearsale_enabled` de `configuracion`:
    '0'       apagado — no se envía nada (default)
    'sombra'  se envía y se registra, pero la venta sigue el flujo de hoy
    '1'       flujo completo con estado intermedio
"""
import json
import os
import re
import threading
import time
from datetime import datetime

import requests as req_lib

logger = None   # lo setea tienda_bp al importar, para compartir el logger


# ── Configuración ────────────────────────────────────────────────────────────
def _base():
    return (os.getenv('CLEARSALE_SANDBOX_URL') or 'https://sandbox.clear.sale').rstrip('/')


def _creds():
    return (os.getenv('CLEARSALE_API_KEY', ''),
            os.getenv('CLEARSALE_CLIENT_ID', ''),
            os.getenv('CLEARSALE_CLIENT_SECRET', ''))


LOCATION = 'ARG'          # confirmado con ClearSale: ISO-3
TIMEOUT = 20

# Address.State se trunca a 2 caracteres (comprobado: "Buenos Aires" -> "BU").
PROVINCIAS = {
    'capital federal': 'CF', 'caba': 'CF', 'ciudad autonoma de buenos aires': 'CF',
    'buenos aires': 'BA', 'catamarca': 'CT', 'chaco': 'CH', 'chubut': 'CU',
    'cordoba': 'CB', 'corrientes': 'CR', 'entre rios': 'ER', 'formosa': 'FO',
    'jujuy': 'JU', 'la pampa': 'LP', 'la rioja': 'LR', 'mendoza': 'MZ',
    'misiones': 'MI', 'neuquen': 'NQ', 'rio negro': 'RN', 'salta': 'SA',
    'san juan': 'SJ', 'san luis': 'SL', 'santa cruz': 'SC', 'santa fe': 'SF',
    'santiago del estero': 'SE', 'tierra del fuego': 'TF', 'tucuman': 'TU',
}

# payment_method_id de Payway -> Credit Card Type de ClearSale
MARCAS_PW = {1: 3, 104: 2, 65: 4, 63: 4}       # Visa, Mastercard, resto "otros"

# CustomFields: el "Type" NO es un flag, es el ID del campo en el catálogo de
# ClearSale (planilla customfields_types.xlsx, 112 nombres). Mandar un nombre
# que no está en la lista hace que descarten la orden entera sin avisar, y
# mandar el Type equivocado la asocia al campo que no es.
CF = {
    'AVS_RESPONSE':            1,
    'IS_GUEST':                3,
    'TRANSACTION_ID':         21,
    'REQUIRES_SHIPPING':      22,
    'SHIPPING_METHOD':        29,
    'GATEWAY':                30,
    'SHIPPING_TYPE':          34,
    'FIRSTORDERDATE':         51,
    'TOTALORDERS':            54,
    'MONTHS_WITHOUT_INTEREST': 62,
    'DECLINED_ATTEMPTS':      72,
    'BANK_RESULT_CODE':       91,
    'BANK_RESULT_DESCRIPTION': 92,
}


def _cf(nombre, valor):
    """Arma un CustomField con el Type correcto. Devuelve None si el valor
    está vacío o el nombre no está en el catálogo (así nunca mandamos uno
    inválido que tire abajo la orden)."""
    if nombre not in CF or valor in (None, '', []):
        return None
    return {'Name': nombre, 'Type': CF[nombre], 'Value': str(valor)[:1000]}


def _log(nivel, msg):
    if logger:
        getattr(logger, nivel, logger.info)(f'[clearsale] {msg}')
    else:
        print(f'[clearsale] {msg}', flush=True)


def modo():
    """Lee el interruptor. Devuelve '0', 'sombra' o '1'."""
    try:
        from app import get_db
        db = get_db(); cur = db.cursor()
        cur.execute("SELECT valor FROM configuracion WHERE clave='clearsale_enabled'")
        row = cur.fetchone()
        cur.close(); db.close()
        v = (str(row['valor']).strip().lower() if row else '0')
        return v if v in ('0', 'sombra', '1') else '0'
    except Exception as e:
        _log('warning', f'no pude leer clearsale_enabled, asumo apagado: {e}')
        return '0'


# ── Auth ─────────────────────────────────────────────────────────────────────
_token = {'valor': None, 'vence': 0}
_token_lock = threading.Lock()


def _login():
    """Token cacheado. ClearSale lo da con 24h de vigencia; renovamos a las 12h."""
    with _token_lock:
        if _token['valor'] and time.time() < _token['vence']:
            return _token['valor']
        api_key, client_id, client_secret = _creds()
        r = req_lib.post(f'{_base()}/api/auth/login',
                         json={'Login': {'ApiKey': api_key, 'ClientId': client_id,
                                         'ClientSecret': client_secret}},
                         headers={'Content-Type': 'application/json'}, timeout=TIMEOUT)
        r.raise_for_status()
        val = ((r.json() or {}).get('Token') or {}).get('Value')
        if not val:
            raise RuntimeError('ClearSale no devolvió token')
        _token['valor'] = val
        _token['vence'] = time.time() + 12 * 3600
        return val


# ── Armado de la orden ───────────────────────────────────────────────────────
def _sin_acentos(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', s or '')
                   if unicodedata.category(c) != 'Mn')


def cod_provincia(nombre):
    return PROVINCIAS.get(_sin_acentos(str(nombre or '')).strip().lower(),
                          (str(nombre or 'XX')[:2]).upper())


def partir_telefono(tel):
    """'1126940003' -> ('11', '26940003')."""
    d = re.sub(r'\D', '', str(tel or ''))
    if d.startswith('54'):
        d = d[2:]
    if d.startswith('9'):
        d = d[1:]
    return (d[:2], d[2:]) if len(d) > 4 else ('', d)


def historial_cliente(dni, email):
    """Compras previas y rechazos del comprador. Es de los datos que más pesan
    en un análisis de fraude y lo tenemos en casa. Fail-safe: si la consulta
    falla, devuelve vacío y la orden viaja igual."""
    vacio = {'compras': None, 'primera': None, 'rechazos': None}
    if not (dni or email):
        return vacio
    try:
        from app import get_db
        db = get_db(); cur = db.cursor()
        cur.execute("""SELECT COUNT(*) AS n, MIN(fecha_venta) AS primera
                       FROM ventas
                       WHERE estado <> 'CANCELADA'
                         AND ((%s <> '' AND dni_cliente = %s)
                              OR (%s <> '' AND email_cliente = %s))""",
                    (dni or '', dni or '', email or '', email or ''))
        v = cur.fetchone() or {}
        # Intentos rechazados previos con el mismo comprador (señal de fraude)
        cur.execute("""SELECT COUNT(*) AS n FROM payway_intentos
                       WHERE status = 'rejected'
                         AND JSON_UNQUOTE(JSON_EXTRACT(raw_json,'$.customer.email')) = %s""",
                    (email or '',))
        r = cur.fetchone() or {}
        cur.close(); db.close()
        prim = v.get('primera')
        return {'compras': v.get('n') or 0,
                'primera': prim.strftime('%Y-%m-%d') if prim else None,
                'rechazos': r.get('n') or 0}
    except Exception as e:
        _log('warning', f'no pude armar el historial del cliente: {e}')
        return vacio


def armar_orden(numero_venta, cli, cart_items, totales, pago, fecha=None):
    """Construye el payload. `totales` y `pago` son dicts planos; ver
    tienda_bp.pago_payway para los valores que se le pasan."""
    f = fecha or datetime.now()
    fecha_iso = f.strftime('%Y-%m-%dT%H:%M:%S-03:00')

    calle = (cli.get('calle') or '').strip()
    altura = str(cli.get('altura') or '').strip()
    linea1 = f'{calle} {altura}'.strip() or (cli.get('direccion') or 'Sin direccion')
    area, numero = partir_telefono(cli.get('telefono'))

    persona = {
        'ID': f"CLI-{cli.get('dni') or 'SD'}",
        'Type': 1,
        'Name': (cli.get('nombre') or '')[:500],
        'Email': (cli.get('email') or '')[:150],
        'LegalDocument': str(cli.get('dni') or ''),
        'Address': {
            'AddressLine1': linea1[:250],
            'AddressLine2': (cli.get('piso_depto') or '')[:250],
            'City': (cli.get('ciudad') or '')[:150],
            'State': cod_provincia(cli.get('provincia')),
            'ZipCode': str(cli.get('cp') or '')[:10],
            'Country': 'ARG',   # ISO-3, pedido por ClearSale
        },
        'Phones': [{'Type': 6, 'AreaCode': area, 'Number': numero}],
    }

    p = {
        'Date': fecha_iso[:10],
        'Type': 1,                                   # CREDIT CARD
        'Amount': float(totales['total']),
        'CardBin': str(pago.get('bin') or '')[:6],
        'CardEndNumber': str(pago.get('last4') or '')[:4],
        'CardType': MARCAS_PW.get(int(pago.get('payment_method_id') or 0), 4),
    }
    if pago.get('installments'):
        p['QtyInstallments'] = int(pago['installments'])
    if pago.get('holder_name'):
        p['CardHolderName'] = str(pago['holder_name'])[:150]
    if pago.get('expiration'):
        p['CardExpirationDate'] = str(pago['expiration'])[:50]
    if pago.get('cupon'):
        p['Nsu'] = str(pago['cupon'])[:50]

    tipo_entrega = str(cli.get('tipo_entrega') or 'envio')
    hist = historial_cliente(cli.get('dni'), cli.get('email'))
    custom = [c for c in [
        _cf('SHIPPING_TYPE',    tipo_entrega),
        _cf('SHIPPING_METHOD',  totales.get('metodo_envio')),
        _cf('REQUIRES_SHIPPING', 'true' if tipo_entrega == 'envio' else 'false'),
        _cf('IS_GUEST',         'true'),          # la tienda no tiene cuentas
        _cf('GATEWAY',          'Payway'),
        _cf('TRANSACTION_ID',   pago.get('payment_id')),
        # El código VTE de Payway es la validación de domicilio de Visa.
        _cf('AVS_RESPONSE',     pago.get('valdom')),
        _cf('BANK_RESULT_CODE',   pago.get('bank_code')),
        _cf('BANK_RESULT_DESCRIPTION', pago.get('bank_desc')),
        _cf('MONTHS_WITHOUT_INTEREST', pago.get('installments')),
        _cf('TOTALORDERS',      hist.get('compras')),
        _cf('FIRSTORDERDATE',   hist.get('primera')),
        _cf('DECLINED_ATTEMPTS', hist.get('rechazos')),
    ] if c]

    # Lo que no entra en ningún campo del catálogo va al texto libre.
    obs = ' | '.join(x for x in [
        f"auth_code={pago.get('auth_code')}" if pago.get('auth_code') else '',
        f"cupon={pago.get('cupon')}" if pago.get('cupon') else '',
        f"tid={pago.get('tid')}" if pago.get('tid') else '',
    ] if x)

    orden = {
        'ID': str(numero_venta).upper()[:50],        # ClearSale normaliza a mayúsculas
        'Date': fecha_iso,
        'Email': (cli.get('email') or '')[:150],
        'TotalItems': float(totales['productos']),
        'TotalOrder': float(totales['total']),
        'TotalShipping': float(totales.get('flete') or 0),
        'Currency': 'ARS',
        'IP': str(cli.get('_capi_ip') or '')[:50],
        'Origin': 'Mobile' if 'Mobile' in str(cli.get('_capi_ua') or '') else 'Web',
        'Payments': [p],
        'BillingData': persona,
        'ShippingData': persona,
        'Items': [{
            'ProductId': str(it.get('sku') or '')[:50],
            'ProductTitle': str(it.get('nombre') or it.get('sku') or '')[:150],
            'Price': str(float(it.get('precio') or 0)),
            'Quantity': int(it.get('cantidad') or 1),
            'Category': 'Colchones y Sommiers',
        } for it in cart_items],
        'CustomFields': custom,
        'Obs': obs[:8000],
        'Reanalysis': False,
    }
    if cli.get('_cs_session'):
        orden['SessionID'] = str(cli['_cs_session'])[:200]
    return orden


# ── Envío y verificación ─────────────────────────────────────────────────────
def _enviar(token, orden):
    api_key, _, _ = _creds()
    r = req_lib.post(f'{_base()}/api/order/send',
                     json={'ApiKey': api_key, 'LoginToken': token,
                           'AnalysisLocation': LOCATION, 'Orders': [orden]},
                     headers={'Content-Type': 'application/json',
                              'analysisLocation': LOCATION}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json() or {}


def consultar(ids):
    """Devuelve {ID_MAYUSCULAS: estado}. Los IDs que no existen no vienen."""
    if not ids:
        return {}
    api_key, _, _ = _creds()
    token = _login()
    r = req_lib.post(f'{_base()}/api/order/get',
                     json={'ApiKey': api_key, 'LoginToken': token,
                           'Orders': list(ids), 'AnalysisLocation': LOCATION},
                     headers={'Content-Type': 'application/json',
                              'analysisLocation': LOCATION}, timeout=TIMEOUT)
    if r.status_code == 404:
        return {}
    r.raise_for_status()
    return {o.get('ID'): o.get('Status') for o in (r.json() or {}).get('Orders', [])}


def _guardar(venta_id, estado, order_id, score=None):
    from app import get_db
    db = get_db(); cur = db.cursor()
    cur.execute("""UPDATE ventas SET clearsale_estado=%s, clearsale_order_id=%s,
                          clearsale_score=%s, clearsale_actualizado=NOW()
                   WHERE id=%s""", (estado, order_id, score, venta_id))
    db.commit(); cur.close(); db.close()


def _procesar(venta_id, orden):
    """Corre en un hilo: envía, verifica y guarda el resultado."""
    oid = orden['ID']
    try:
        token = _login()
        resp = _enviar(token, orden)
        _log('info', f'venta {venta_id} enviada como {oid}: {json.dumps(resp)[:200]}')
        # Verificación obligatoria: el 200 no garantiza que la orden exista.
        time.sleep(3)
        estados = consultar([oid])
        est = estados.get(oid.upper()) or estados.get(oid)
        if not est:
            _log('error', f'venta {venta_id}: ClearSale respondió OK pero la orden '
                          f'{oid} NO existe — payload rechazado en silencio')
            _guardar(venta_id, 'ERR', oid)
            return
        _guardar(venta_id, est, oid)
        _log('info', f'venta {venta_id} -> {est}')
    except Exception as e:
        _log('error', f'venta {venta_id} ({oid}): {type(e).__name__}: {e}')
        try:
            _guardar(venta_id, 'ERR', oid)
        except Exception:
            pass


def enviar_async(venta_id, orden):
    """Dispara el envío sin bloquear el checkout."""
    threading.Thread(target=_procesar, args=(venta_id, orden), daemon=True).start()
