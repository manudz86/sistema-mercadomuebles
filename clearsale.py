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
import uuid
import time
from datetime import datetime

import pymysql
import requests as req_lib

logger = None   # lo setea tienda_bp al importar, para compartir el logger


def _db():
    """Conexión propia. No la importamos de tienda_bp para no crear una
    dependencia circular, y abrir una por llamada es seguro desde los hilos."""
    return pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        user=os.environ.get('DB_USER', 'cannon'),
        password=os.environ.get('DB_PASSWORD', ''),
        database=os.environ.get('DB_NAME', 'inventario_cannon'),
        cursorclass=pymysql.cursors.DictCursor,
        charset='utf8mb4',
    )


# ── Configuración ────────────────────────────────────────────────────────────
def _base():
    """URL base de la API. CLEARSALE_API_URL manda; si no está, se usa
    CLEARSALE_SANDBOX_URL y por último el sandbox. Para pasar a producción
    alcanza con definir CLEARSALE_API_URL=https://integration.clear.sale
    (confirmada por ClearSale el 27/10/2026) junto con las credenciales
    productivas, sin tocar código."""
    return (os.getenv('CLEARSALE_API_URL')
            or os.getenv('CLEARSALE_SANDBOX_URL')
            or 'https://sandbox.clear.sale').rstrip('/')


def client_id():
    """El ClientId es además el AppID del script de Behavior Analytics, que
    se inyecta en el HTML del checkout. No es un secreto."""
    return os.getenv('CLEARSALE_CLIENT_ID', '').strip()


def nuevo_session_id(numero_venta=''):
    """SessionID para el fingerprint. ClearSale exige entre 7 y 128
    caracteres y que sea EL MISMO que viaja en la orden."""
    base = re.sub(r'[^A-Za-z0-9]', '', str(numero_venta or '')) or 'mm'
    return f'{base}-{uuid.uuid4().hex}'[:128]


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

# CustomFields. El "Type" NO es el ID del campo en el catálogo de ClearSale
# (planilla customfields_types.xlsx): es un enum chico de tipo de dato, y 1 es
# texto. Mandar el ID del catálogo como Type (34, 29, 21, 30...) hace que
# ClearSale DESCARTE la orden entera en silencio: responde 200/NVO y después
# la orden no existe. Así se perdieron las ventas 25516 y 25524.
#
# Comprobado uno por uno contra el sandbox (scripts/clearsale_prod_diag.py --cf
# y scripts/clearsale_probe.py cfnuevos): con Type 1 entran los doce nombres de
# abajo. Los ocho que antes parecían deshabilitados fallaban por el Type, no
# por el nombre — no hay nada que pedirle a ClearSale.
CF_TIPO_TEXTO = 1
CF = (
    'AVS_RESPONSE', 'IS_GUEST', 'CVV_RESULT_CODE', 'SHIPPING_METHOD',
    'SHIPPING_TYPE', 'REQUIRES_SHIPPING', 'GATEWAY', 'TRANSACTION_ID',
    'MONTHS_WITHOUT_INTEREST', 'TOTALORDERS', 'FIRSTORDERDATE',
    'DECLINED_ATTEMPTS', 'BANK_RESULT_CODE', 'BANK_RESULT_DESCRIPTION',
)


def _cf(nombre, valor):
    """Arma un CustomField. Devuelve None si el valor está vacío o el nombre
    no está en la lista verificada (así nunca mandamos uno inválido que tire
    abajo la orden)."""
    if nombre not in CF or valor in (None, '', []):
        return None
    return {'Name': nombre, 'Type': CF_TIPO_TEXTO, 'Value': str(valor)[:1000]}


MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre')


def _fecha_en_letras(iso):
    """'1986-06-04' -> '4 de junio de 1986'. El mes con nombre saca la
    ambigüedad dd/mm vs mm/dd para el analista que lee las observaciones."""
    try:
        a, m, d = str(iso)[:10].split('-')
        return f'{int(d)} de {MESES[int(m) - 1]} de {a}'
    except (ValueError, IndexError):
        return str(iso or '')


def _mismo_nombre(a, b):
    """¿Son la misma persona? Ignora mayúsculas, acentos, puntos y el orden
    ('DZIENCIELSKY, Matias' == 'matias dziencielsky'), y toma como iguales los
    nombres donde uno contiene al otro: la tarjeta suele traer el segundo
    nombre ('FULVIA DANI LORENZI' es la misma que 'FULVIA LORENZI'). Solo da
    distinto cuando no hay forma de que sea la misma persona, que es cuando
    vale la pena avisarle al analista."""
    def _norm(s):
        s = _sin_acentos(str(s or '')).lower()
        return {p for p in re.split(r'[^a-z0-9]+', s) if p}
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return True          # sin dato para comparar, no inventamos un aviso
    return na <= nb or nb <= na


# ── Estados y qué habilitan ──────────────────────────────────────────────────
# Clasificación de los códigos de ClearSale. De esto depende qué se puede
# despachar, así que cualquier cambio acá se mira dos veces.
CS_APRUEBAN = {'APA', 'APM', 'APG'}            # aprobada: se puede entregar
CS_RECHAZAN = {'RPA', 'RPM', 'RPP', 'FRD'}     # rechazada / fraude confirmado
CS_EN_CURSO = {'NVO', 'AMA', 'SUS'}            # todavía analizando
CS_REVISAR  = {'ERR', 'CAN'}                   # error de envío o cancelada

CS_ETIQUETAS = {
    'NVO': 'Nueva, sin analizar',   'AMA': 'En análisis',
    'SUS': 'Suspendida',            'APA': 'Aprobada automáticamente',
    'APM': 'Aprobada por analista', 'APG': 'Aprobada por regla',
    'RPA': 'Rechazada automáticamente', 'RPM': 'Rechazada por analista',
    'RPP': 'Rechazada por política',    'FRD': 'Fraude confirmado',
    'CAN': 'Cancelada',             'ERR': 'Error al enviar a ClearSale',
}


def bloquea_entrega(clearsale_estado, modo_actual):
    """¿Hay que frenar el despacho de esta venta? Devuelve (bloquea, motivo).

    Dos reglas que importan:

    * En modo '0' y 'sombra' NUNCA bloquea. Sombra existe justamente para
      observar sin cambiar la operación; si frenara entregas dejaría de ser
      sombra.

    * Una venta SIN estado de ClearSale nunca se bloquea. Son todas las de
      Mercado Pago, Mercado Libre, las de retiro y las de Payway anteriores
      a la integración. Bloquearlas frenaría el negocio entero.
    """
    if str(modo_actual or '0') != '1':
        return False, ''
    e = str(clearsale_estado or '').strip().upper()
    if not e or e in CS_APRUEBAN:
        return False, ''
    if e in CS_RECHAZAN:
        return True, f'ClearSale rechazó la operación ({e} — {CS_ETIQUETAS.get(e, e)}).'
    if e in CS_EN_CURSO:
        return True, f'ClearSale todavía está analizando ({e} — {CS_ETIQUETAS.get(e, e)}).'
    # ERR, CAN y cualquier código que no conozcamos: frenar y que lo mire
    # una persona. Preferimos una entrega demorada a una entrega indebida.
    return True, f'Estado de ClearSale sin resolver ({e} — {CS_ETIQUETAS.get(e, e)}): revisalo a mano.'


def _log(nivel, msg):
    if logger:
        getattr(logger, nivel, logger.info)(f'[clearsale] {msg}')
    else:
        print(f'[clearsale] {msg}', flush=True)


def modo():
    """Lee el interruptor. Devuelve '0', 'sombra' o '1'."""
    try:
        db = _db(); cur = db.cursor()
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
        db = _db(); cur = db.cursor()
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

    def _persona(linea, ciudad, prov, cp, piso=''):
        p = {
            'ID': f"CLI-{cli.get('dni') or 'SD'}",
            'Type': 1,
            'Name': (cli.get('nombre') or '')[:500],
            'Email': (cli.get('email') or '')[:150],
            'LegalDocument': str(cli.get('dni') or ''),
            'Address': {
                'AddressLine1': str(linea)[:250],
                'AddressLine2': str(piso or '')[:250],
                'City': str(ciudad or '')[:150],
                'State': cod_provincia(prov),
                'ZipCode': str(cp or '')[:10],
                'Country': 'ARG',   # ISO-3, pedido por ClearSale
            },
            'Phones': [{'Type': 6, 'AreaCode': area, 'Number': numero}],
        }
        if cli.get('_birth_date'):
            p['BirthDate'] = f"{cli['_birth_date']}T00:00:00"
        return p

    envio = _persona(linea1, cli.get('ciudad'), cli.get('provincia'),
                     cli.get('cp'), cli.get('piso_depto'))
    # BillingData solo es distinto si el comprador declaró otro domicilio de
    # resumen. Si no lo declaró es una copia del de envío: no sabemos el real.
    bl = cli.get('_billing')
    factura = _persona(bl['calle'], bl['ciudad'], bl['provincia'], bl['cp']) if bl else envio

    # BillingData es el TITULAR de la tarjeta, no el comprador: que un tercero
    # pague es justo lo que ClearSale tiene que poder ver. Del titular sabemos
    # nombre y domicilio; el DNI no lo pedimos, así que cuando el titular es
    # otra persona se omite LegalDocument en vez de mandarle el del comprador,
    # que sería un dato falso (comprobado: ClearSale acepta la persona sin él).
    titular = str(pago.get('holder_name') or '').strip()
    doc_titular = re.sub(r'\D', '', str(pago.get('holder_doc') or ''))
    dni_comprador = re.sub(r'\D', '', str(cli.get('dni') or ''))

    # ¿El que paga es el que recibe? El documento manda sobre el nombre: es el
    # único dato que identifica sin ambigüedad. Si no lo tenemos (ventas de
    # antes de capturarlo) se cae a comparar los nombres.
    if doc_titular and dni_comprador:
        otra_persona = doc_titular != dni_comprador
    else:
        otra_persona = bool(titular) and not _mismo_nombre(titular, cli.get('nombre'))

    if titular:
        factura = dict(factura, Name=titular[:500])
    if doc_titular:
        factura = dict(factura, LegalDocument=doc_titular, ID=f'CLI-{doc_titular}')
    elif otra_persona:
        # Sin el documento del titular, mejor que falte a mandarle el del
        # comprador: sería atribuirle a una persona un documento que no es suyo.
        factura = dict(factura)
        factura.pop('LegalDocument', None)
    if otra_persona:
        # El formulario pide la fecha de nacimiento DEL TITULAR, así que queda
        # en factura; de quien recibe el envío no sabemos la fecha.
        envio = dict(envio)
        envio.pop('BirthDate', None)

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
    # Solo los cinco que ClearSale confirmó como funcionales para su algoritmo
    # (mail de Mauricio Cortes, 27/10/2026). Pidió mantener el conjunto mínimo:
    # el detalle de la pasarela no les aporta porque trabajan con muchas. Lo
    # que sacamos de acá no se pierde, va a Obs, que es texto libre que lee el
    # analista.
    #
    # MONTHS_WITHOUT_INTEREST queda afuera por dos razones: ClearSale lo pide
    # "sólo en caso de que no se comparta en el Payments array" y nosotros ya
    # mandamos QtyInstallments ahí; y además nuestras cuotas llevan coeficiente
    # (3 cuotas = 1,116), así que no son sin interés salvo en la promo de
    # miércoles y sábado — declararlas ahí sería un dato falso.
    custom = [c for c in [
        _cf('SHIPPING_TYPE',    tipo_entrega),
        _cf('IS_GUEST',         'true'),          # la tienda no tiene cuentas
        _cf('TOTALORDERS',      hist.get('compras')),
        _cf('FIRSTORDERDATE',   hist.get('primera')),
        _cf('DECLINED_ATTEMPTS', hist.get('rechazos')),
    ] if c]

    # Obs duplica parte de lo anterior a propósito: es texto libre que el
    # analista ve de un vistazo, y suma lo que no tiene CustomField propio.
    obs = ' | '.join(x for x in [
        f"gateway=Payway",
        f"nacimiento_titular={_fecha_en_letras(cli['_birth_date'])}"
        if cli.get('_birth_date') else '',
        # Dejarlo explícito en el texto libre: es lo primero que mira el
        # analista cuando el que paga no es el que recibe.
        f"PAGA UN TERCERO: titular={titular or 'sin dato'}"
        f" doc={doc_titular or 'sin dato'}"
        f" | comprador={cli.get('nombre')} doc={dni_comprador or 'sin dato'}"
        if otra_persona else '',
        f"transaction_id={pago.get('payment_id')}" if pago.get('payment_id') else '',
        f"auth_code={pago.get('auth_code')}" if pago.get('auth_code') else '',
        f"cupon={pago.get('cupon')}" if pago.get('cupon') else '',
        f"tid={pago.get('tid')}" if pago.get('tid') else '',
        f"cuotas={pago.get('installments')}" if pago.get('installments') else '',
        f"banco={pago.get('bank_code')}/{pago.get('bank_desc')}" if pago.get('bank_code') else '',
        # Estos tres salieron de CustomFields a pedido de ClearSale, pero el
        # envío y la validación de domicilio del emisor sí le sirven al
        # analista, así que quedan en el texto libre.
        f"envio={'Pick up' if tipo_entrega == 'retiro' else (totales.get('metodo_envio') or 'sin especificar')}",
        f"avs_visa={pago.get('valdom')}" if pago.get('valdom') else '',
        f"compras_previas={hist.get('compras')}" if hist.get('compras') is not None else '',
        f"primera_compra={hist.get('primera')}" if hist.get('primera') else '',
        f"rechazos_previos={hist.get('rechazos')}" if hist.get('rechazos') is not None else '',
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
        'BillingData': factura,
        'ShippingData': envio,
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
    db = _db(); cur = db.cursor()
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


# ── Autoprueba ───────────────────────────────────────────────────────────────
# `venv/bin/python3 clearsale.py` verifica que el módulo pueda hablar con la
# base y con ClearSale. Es de solo lectura: no envía ninguna orden.
if __name__ == '__main__':
    import sys
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'config', '.env'))
    print(f'modo .............. {modo()}')
    try:
        tok = _login()
        print(f'login ClearSale ... OK ({len(tok)} chars)')
    except Exception as e:
        print(f'login ClearSale ... FALLO: {type(e).__name__}: {e}')
        sys.exit(1)
    dni = sys.argv[1] if len(sys.argv) > 1 else '41395583'
    mail = sys.argv[2] if len(sys.argv) > 2 else 'nahirazar413@gmail.com'
    print(f'historial ......... {historial_cliente(dni, mail)}')

    # Armado de la orden en los dos casos: con y sin domicilio de resumen
    base = {'nombre': 'Juan Perez', 'dni': dni, 'email': mail,
            'telefono': '1126940003', 'calle': 'Rivadavia', 'altura': '8916',
            'piso_depto': '3 A', 'ciudad': 'Floresta', 'cp': '1407',
            'provincia': 'Capital Federal', 'tipo_entrega': 'envio',
            '_capi_ip': '181.47.1.1', '_birth_date': '1986-04-12'}
    tot = {'productos': 100.0, 'total': 120.0, 'flete': 20.0,
           'metodo_envio': 'Flete Propio'}
    pg = {'bin': '450815', 'last4': '1234', 'payment_method_id': 1,
          'installments': 3, 'holder_name': 'JUAN PEREZ',
          'expiration': '12/2030', 'payment_id': '999', 'valdom': 'VTE0011'}
    items = [{'sku': 'SEX200', 'nombre': 'Sommier Exclusive', 'precio': 100, 'cantidad': 1}]

    o1 = armar_orden('PW-TEST', base, items, tot, pg)
    igual = o1['BillingData']['Address'] == o1['ShippingData']['Address']
    print(f'orden sin billing . BillingData == ShippingData: {igual} · '
          f'BirthDate: {o1["BillingData"].get("BirthDate")}')

    con = dict(base, _billing={'calle': 'Corrientes 1500', 'ciudad': 'San Isidro',
                               'cp': '1642', 'provincia': 'Buenos Aires'})
    o2 = armar_orden('PW-TEST2', con, items, tot, pg)
    print(f'orden con billing . billing={o2["BillingData"]["Address"]["AddressLine1"]}'
          f'/{o2["BillingData"]["Address"]["State"]} · '
          f'envio={o2["ShippingData"]["Address"]["AddressLine1"]}'
          f'/{o2["ShippingData"]["Address"]["State"]}')
    print(f'customfields ...... {[c["Name"] for c in o2["CustomFields"]]}')
