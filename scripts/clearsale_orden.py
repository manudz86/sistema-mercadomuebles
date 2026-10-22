#!/usr/bin/env python3
"""Arma la orden de ClearSale a partir de una venta REAL del sistema y,
opcionalmente, la manda al sandbox.

Sirve para dos cosas:
  1) ver que campos de ClearSale podemos completar con los datos que ya
     tenemos, y cuales faltan capturar (lo imprime como informe);
  2) validar el payload contra el sandbox antes de escribir la integracion
     de verdad, que es el paso 5 del proceso de ClearSale.

Uso:
    venv/bin/python3 scripts/clearsale_orden.py <venta_id>
    venv/bin/python3 scripts/clearsale_orden.py <venta_id> --enviar

Sin --enviar no sale ninguna peticion: solo arma el payload y lo muestra.
No escribe en la base. Nunca imprime credenciales.

OJO: en una venta historica ya no existe el pedido en pedidos_pendientes
(se limpia al concretarse), asi que la IP y el user-agent no estan. En el
flujo real se arman dentro de pago_payway, donde esos datos estan en memoria.
"""
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests as req_lib  # noqa: E402
from _common import cargar_env, conectar_db  # noqa: E402

ENV = cargar_env()
BASE = (ENV.get('CLEARSALE_SANDBOX_URL') or 'https://sandbox.clear.sale').rstrip('/')
API_KEY = ENV.get('CLEARSALE_API_KEY', '')
CLIENT_ID = ENV.get('CLEARSALE_CLIENT_ID', '')
CLIENT_SECRET = ENV.get('CLEARSALE_CLIENT_SECRET', '')
LOCATION = 'ARG'

# El campo Address.State se trunca a 2 caracteres (comprobado: "Buenos Aires"
# quedo como "BU"). Hasta que ClearSale confirme su tabla, usamos las
# abreviaturas postales de uso corriente en Argentina.
PROVINCIAS = {
    'capital federal': 'CF', 'caba': 'CF', 'ciudad autonoma de buenos aires': 'CF',
    'buenos aires': 'BA', 'catamarca': 'CT', 'chaco': 'CH', 'chubut': 'CU',
    'cordoba': 'CB', 'corrientes': 'CR', 'entre rios': 'ER', 'formosa': 'FO',
    'jujuy': 'JU', 'la pampa': 'LP', 'la rioja': 'LR', 'mendoza': 'MZ',
    'misiones': 'MI', 'neuquen': 'NQ', 'rio negro': 'RN', 'salta': 'SA',
    'san juan': 'SJ', 'san luis': 'SL', 'santa cruz': 'SC', 'santa fe': 'SF',
    'santiago del estero': 'SE', 'tierra del fuego': 'TF', 'tucuman': 'TU',
}

# card_brand de Payway -> Credit Card Type de ClearSale
MARCAS = {'visa': 3, 'mastercard': 2, 'master': 2, 'amex': 5,
          'american express': 5, 'diners': 1, 'cabal': 4, 'naranja': 4}

faltantes = []   # (campo, motivo)


def _sin_acentos(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', s or '')
                   if unicodedata.category(c) != 'Mn')


def cod_provincia(nombre):
    k = _sin_acentos(str(nombre or '')).strip().lower()
    cod = PROVINCIAS.get(k)
    if not cod:
        faltantes.append(('Address.State', f'provincia sin mapear: {nombre!r}'))
        return (str(nombre or 'XX')[:2]).upper()
    return cod


def partir_direccion(texto, provincia_venta):
    """'Rivadavia 8916 3 A, Floresta, Capital Federal CP 1407'
       -> (calle, altura, ciudad, provincia, cp)"""
    txt = (texto or '').strip()
    cp = ''
    m = re.search(r'\bCP\s*([0-9A-Za-z]+)\s*$', txt)
    if m:
        cp = m.group(1)
        txt = txt[:m.start()].rstrip(' ,')
    partes = [p.strip() for p in txt.split(',') if p.strip()]
    calle_full = partes[0] if partes else ''
    ciudad = partes[1] if len(partes) > 1 else ''
    provincia = partes[2] if len(partes) > 2 else (provincia_venta or '')
    # AddressLine1 = calle + altura (es lo que geolocaliza ClearSale; mandando
    # la altura aparte el pin caia en otra cuadra). AddressLine2 = piso/depto.
    m2 = re.match(r'^(.*?\s+\d+)\s*(.*)$', calle_full)
    calle, altura = (m2.group(1).strip(), m2.group(2).strip()) if m2 else (calle_full, '')
    if not cp:
        faltantes.append(('Address.ZipCode', 'no se pudo extraer de direccion_entrega'))
    if not re.search(r'\d', calle):
        faltantes.append(('Address.AddressLine1', f'sin altura en la direccion: {calle!r}'))
    return calle, altura, ciudad, provincia, cp


def partir_telefono(tel):
    """'1126940003' -> ('11', '26940003'). Heuristica simple para AR."""
    d = re.sub(r'\D', '', str(tel or ''))
    if d.startswith('54'):
        d = d[2:]
    if d.startswith('9'):
        d = d[1:]
    if len(d) >= 10:
        return d[:2], d[2:]
    if len(d) > 4:
        return d[:2], d[2:]
    faltantes.append(('Phone.AreaCode', f'telefono corto o invalido: {tel!r}'))
    return '', d


def traer_venta(venta_id):
    db = conectar_db(solo_lectura=True)
    cur = db.cursor()
    cur.execute("SELECT * FROM ventas WHERE id = %s", (venta_id,))
    venta = cur.fetchone()
    if not venta:
        cur.close(); db.close()
        raise SystemExit(f'No existe la venta {venta_id}')
    # El nombre real del producto sale del catalogo: items_venta solo guarda el SKU,
    # y un titulo descriptivo le sirve al analista de ClearSale.
    cur.execute("""SELECT iv.sku, iv.cantidad, iv.precio_unitario,
                          COALESCE(pb.nombre, iv.sku) AS nombre
                   FROM items_venta iv
                   LEFT JOIN productos_base pb ON pb.sku = iv.sku
                   WHERE iv.venta_id = %s""", (venta_id,))
    items = cur.fetchall()

    # payment_id de Payway desde las notas: "PWID: 1020349403"
    pw = {}
    m = re.search(r'PWID:\s*(\d+)', venta.get('notas') or '')
    if m:
        cur.execute("""SELECT payment_id, bin, last4, card_brand, installments, tid, raw_json
                       FROM payway_intentos WHERE payment_id = %s""", (int(m.group(1)),))
        pw = cur.fetchone() or {}
    cur.close(); db.close()
    return venta, items, pw


def armar_orden(venta, items, pw):
    raw = {}
    if pw.get('raw_json'):
        raw = pw['raw_json'] if isinstance(pw['raw_json'], dict) else json.loads(pw['raw_json'])
    det = (raw.get('status_details') or {})

    calle, altura, ciudad, prov, cp = partir_direccion(
        venta.get('direccion_entrega'), venta.get('provincia_cliente'))
    area, numero = partir_telefono(venta.get('telefono_cliente'))

    # Con --hoy se reemplaza la fecha original por la actual. ClearSale acepto
    # (200 / NVO) una orden fechada 8 dias atras pero despues no existia: el
    # flag sirve para aislar si la fecha vieja es el motivo.
    if '--hoy' in sys.argv:
        fecha = datetime.now()
    else:
        fecha = venta.get('fecha_venta')
    if isinstance(fecha, datetime):
        fecha_iso = fecha.strftime('%Y-%m-%dT%H:%M:%S-03:00')   # hora local, como pidieron
    else:
        fecha_iso = str(fecha)

    total_items = float(venta.get('importe_total') or 0)
    flete = float(venta.get('costo_flete') or 0)
    total = float(venta.get('importe_abonado') or 0) or (total_items + flete)

    persona = {
        'ID': f"CLI-{venta.get('dni_cliente') or 'SD'}",
        'Type': 1,
        'Name': venta.get('nombre_cliente') or '',
        'Email': venta.get('email_cliente') or '',
        'LegalDocument': venta.get('dni_cliente') or '',
        'Address': {
            'AddressLine1': calle,
            'AddressLine2': altura,
            'City': ciudad,
            'State': cod_provincia(prov),
            'ZipCode': cp,
            'Country': 'Argentina',
        },
        'Phones': [{'Type': 6, 'AreaCode': area, 'Number': numero}],
    }

    marca = str(pw.get('card_brand') or '').strip().lower()
    cuotas = int(pw.get('installments') or 0) or None

    pago = {
        'Date': fecha_iso[:10],
        'Type': 1,                                   # CREDIT CARD
        'Amount': total,
        'CardBin': pw.get('bin') or '',
        'CardEndNumber': pw.get('last4') or '',
        'CardType': MARCAS.get(marca, 4),
    }
    if cuotas:
        pago['QtyInstallments'] = cuotas
    if det.get('ticket'):
        pago['Nsu'] = str(det['ticket'])             # numero de cupon
    if not pw.get('last4'):
        faltantes.append(('Payments.CardEndNumber', 'payway_intentos no tiene last4'))
    # Estos dos quedan en el navegador y hoy no llegan al backend
    faltantes.append(('Payments.CardHolderName', 'el JS del checkout no lo envia al backend'))
    faltantes.append(('Payments.CardExpirationDate', 'el JS del checkout no lo envia al backend'))

    # CustomFields: ClearSale pidio el tipo de envio; sumamos la traza de Payway
    custom = [{'Name': 'SHIPPING_TYPE', 'Type': 1,
               'Value': venta.get('tipo_entrega') or 'envio'},
              {'Name': 'SHIPPING_METHOD', 'Type': 1,
               'Value': venta.get('metodo_envio') or 'sin especificar'}]
    # Los nombres de CustomFields estan en lista blanca: SHIPPING_TYPE y
    # SHIPPING_METHOD pasan, cualquier nombre inventado hace que ClearSale
    # DESCARTE la orden entera sin avisar (devuelve 200/NVO igual). Hasta que
    # nos pasen la lista valida, la traza de Payway va en Obs, que es texto
    # libre de 8000 caracteres.
    # El codigo VTE de Payway es la validacion de domicilio de Visa, o sea el
    # equivalente del AVS: AVS_RESPONSE esta en la lista blanca y le calza.
    if det.get('address_validation_code'):
        custom.append({'Name': 'AVS_RESPONSE', 'Type': 1,
                       'Value': str(det['address_validation_code'])})

    cs_dec = (((raw.get('fraud_detection') or {}).get('status') or {}).get('decision'))
    obs = ' | '.join(p for p in [
        f"payway_payment_id={raw.get('id')}" if raw.get('id') else '',
        f"auth_code={det.get('card_authorization_code')}" if det.get('card_authorization_code') else '',
        f"cupon={det.get('ticket')}" if det.get('ticket') else '',
        f"tid={pw.get('tid')}" if pw.get('tid') else '',
        f"cybersource={cs_dec}" if cs_dec else '',
        f"visa_valdom={det.get('address_validation_code')}" if det.get('address_validation_code') else '',
    ] if p)

    # IP y SessionID: el manual los marca obligatorios. En una venta historica
    # no los tenemos (el pedido pendiente ya se borro), asi que para la prueba
    # van valores de relleno. En vivo salen de cli._capi_ip y del Mapper.
    ip = ENV.get('CLEARSALE_TEST_IP') or '181.47.1.1'
    session_id = 'mm-' + (venta.get('numero_venta') or 'sd').lower().replace('-', '') \
                 + '-' + datetime.now().strftime('%Y%m%d%H%M%S')
    faltantes.append(('IP', f'venta historica: se usa {ip} de relleno; en vivo, cli._capi_ip'))
    faltantes.append(('SessionID', 'generado para la prueba; en vivo lo define el Mapper (A2)'))

    orden = {
        # --unico agrega un sufijo aleatorio: reenviar el mismo ID pisa la
        # orden anterior en vez de crear una nueva, asi que para comparar
        # payloads entre si conviene que cada envio tenga su propio ID.
        'ID': f"TEST-{(venta.get('numero_venta') or '').upper()}"
              + ('-HOY' if '--hoy' in sys.argv else '')
              + ('-' + __import__('uuid').uuid4().hex[:6].upper()
                 if '--unico' in sys.argv else ''),
        'Date': fecha_iso,
        'Email': venta.get('email_cliente') or '',
        'TotalItems': total_items,
        'TotalOrder': total,
        'TotalShipping': flete,
        'Currency': 'ARS',
        'IP': ip,
        'Origin': 'Web',
        'SessionID': session_id,
        'Payments': [pago],
        'BillingData': persona,
        'ShippingData': persona,
        'Items': [{
            'ProductId': it['sku'],
            'ProductTitle': it.get('nombre') or it['sku'],
            'Price': str(float(it['precio_unitario'])),
            'Quantity': int(it['cantidad']),
            'Category': 'Colchones y Sommiers',
        } for it in items],
        'CustomFields': custom,
        'Obs': obs,
        'Reanalysis': False,
    }
    if cuotas:
        orden['QtyInstallments'] = cuotas
    return orden


def bisect(orden):
    """Manda varias copias de la orden, cada una sin UNO de los bloques
    sospechosos, para ver cual hace que ClearSale la descarte en silencio.
    La API acepta varias ordenes por llamada, asi que va todo en una sola."""
    import copy
    variantes = []

    def _v(sufijo, fn):
        o = copy.deepcopy(orden)
        o['ID'] = orden['ID'] + sufijo
        fn(o)
        variantes.append((o['ID'], sufijo, o))

    _v('-V1-FULL',      lambda o: None)
    _v('-V2-SINCUSTOM', lambda o: o.pop('CustomFields', None))
    _v('-V3-SINQTY',    lambda o: o.pop('QtyInstallments', None))
    _v('-V4-SINNSU',    lambda o: o['Payments'][0].pop('Nsu', None))
    _v('-V5-CONLAST4',  lambda o: o['Payments'][0].update({'CardEndNumber': '0000'}))
    _v('-V6-MINIMO',    lambda o: (o.pop('CustomFields', None),
                                   o.pop('QtyInstallments', None),
                                   o['Payments'][0].pop('Nsu', None),
                                   o['Payments'][0].update({'CardEndNumber': '0000'})))

    token = login()
    if not token:
        print('No se pudo obtener el token.')
        return
    # Una por llamada: un lote con una orden invalida se descarta entero.
    print(f'\nENVIANDO {len(variantes)} variantes, de a una:')
    for oid, sufijo, o in variantes:
        r = req_lib.post(f'{BASE}/api/order/send',
                         json={'ApiKey': API_KEY, 'LoginToken': token,
                               'AnalysisLocation': LOCATION, 'Orders': [o]},
                         headers={'Content-Type': 'application/json',
                                  'analysisLocation': LOCATION}, timeout=40)
        print(f'    {oid:<44} HTTP {r.status_code}')
    print('\n  Consultalas con:')
    print('  venv/bin/python3 scripts/clearsale_probe.py get ' +
          ' '.join(i for i, _, _ in variantes))


def bisect_grupos(orden):
    """Al reves del anterior: parte del payload conocido-bueno de
    clearsale_probe y le mete UN grupo de la venta real por vez."""
    import copy
    from clearsale_probe import _orden as orden_base, ITEMS_EJEMPLO
    import uuid as _uuid

    suf = _uuid.uuid4().hex[:6]
    casos = []

    def _v(nombre, fn):
        o = orden_base(f'GRUPO-{nombre}-{suf}', ITEMS_EJEMPLO)
        fn(o)
        casos.append((o['ID'], nombre, o))

    _v('BASE',     lambda o: None)
    _v('ITEMS',    lambda o: o.update({'Items': orden['Items']}))
    _v('PERSONA',  lambda o: o.update({'BillingData': orden['BillingData'],
                                       'ShippingData': orden['ShippingData']}))
    _v('TOTALES',  lambda o: o.update({'TotalItems': orden['TotalItems'],
                                       'TotalOrder': orden['TotalOrder'],
                                       'TotalShipping': orden['TotalShipping']}))
    _v('PAGO',     lambda o: o.update({'Payments': orden['Payments']}))
    _v('CABECERA', lambda o: o.update({'Email': orden['Email'],
                                       'Date': orden['Date'],
                                       'SessionID': orden['SessionID'],
                                       'IP': orden['IP']}))

    # La orden real completa, pero con un ID del formato que sabemos que anda.
    # Si esta existe y la original no, el problema era el identificador.
    o_full = copy.deepcopy(orden)
    o_full['ID'] = f'GRUPO-FULL-{suf}'
    casos.append((o_full['ID'], 'FULL', o_full))

    token = login()
    if not token:
        print('No se pudo obtener el token.')
        return
    # UNA POR LLAMADA: si una orden del lote es invalida, ClearSale descarta
    # el lote completo y responde 200/NVO para todas igual. Mandarlas juntas
    # invalida la biseccion.
    print(f'\nENVIANDO {len(casos)} grupos, de a uno:')
    for oid, nombre, o in casos:
        r = req_lib.post(f'{BASE}/api/order/send',
                         json={'ApiKey': API_KEY, 'LoginToken': token,
                               'AnalysisLocation': LOCATION, 'Orders': [o]},
                         headers={'Content-Type': 'application/json',
                                  'analysisLocation': LOCATION}, timeout=40)
        print(f'    {oid:<26} base + {nombre:<9} HTTP {r.status_code}')
    print('\n  Consultalos con:')
    print('  venv/bin/python3 scripts/clearsale_probe.py get ' +
          ' '.join(i for i, _, _ in casos))


def probar_customfields(orden):
    """CustomFields hace que ClearSale descarte la orden en silencio.
    Probamos variantes de la estructura, una por llamada."""
    import copy
    from clearsale_probe import _orden as orden_base, ITEMS_EJEMPLO
    import uuid as _uuid

    suf = _uuid.uuid4().hex[:6]
    casos = []

    def _v(nombre, cf):
        o = orden_base(f'CF-{nombre}-{suf}', ITEMS_EJEMPLO)
        if cf is not None:
            o['CustomFields'] = cf
        casos.append((o['ID'], nombre, o))

    # Ya sabemos: Type es obligatorio, Type 0 no vale, y un campo suelto con
    # Type 1 anda. Falta ver cual de los nuestros rompe -> uno por variante.
    # SHIPPING_TYPE y SHIPPING_METHOD pasan; los nombres inventados no.
    # Estas dos variantes separan si manda el NOMBRE o el VALOR.
    # Sabemos que SHIPPING_TYPE y SHIPPING_METHOD pasan y FOO no. Falta ver
    # si la lista es por prefijo o por nombre exacto, y si valen los nombres
    # del propio ejemplo de la documentacion de ClearSale.
    _v('SINCF',    None)                                   # control
    _v('SHIPFOO',  [{'Name': 'SHIPPING_FOO', 'Type': 1, 'Value': 'envio'}])
    _v('AVS',      [{'Name': 'AVS_RESPONSE', 'Type': 1, 'Value': 'Q'}])
    _v('CVV',      [{'Name': 'CVV_RESULT_CODE', 'Type': 1, 'Value': 'M'}])
    _v('MINUSC',   [{'Name': 'shipping_type', 'Type': 1, 'Value': 'envio'}])

    token = login()
    if not token:
        print('No se pudo obtener el token.')
        return
    print(f'\nENVIANDO {len(casos)} variantes de CustomFields, de a una:')
    for oid, nombre, o in casos:
        r = req_lib.post(f'{BASE}/api/order/send',
                         json={'ApiKey': API_KEY, 'LoginToken': token,
                               'AnalysisLocation': LOCATION, 'Orders': [o]},
                         headers={'Content-Type': 'application/json',
                                  'analysisLocation': LOCATION}, timeout=40)
        print(f'    {oid:<24} {nombre:<9} HTTP {r.status_code}')
    print('\n  Consultalas con:')
    print('  venv/bin/python3 scripts/clearsale_probe.py get ' +
          ' '.join(i for i, _, _ in casos))


def login():
    r = req_lib.post(f'{BASE}/api/auth/login',
                     json={'Login': {'ApiKey': API_KEY, 'ClientId': CLIENT_ID,
                                     'ClientSecret': CLIENT_SECRET}},
                     headers={'Content-Type': 'application/json'}, timeout=25)
    r.raise_for_status()
    return ((r.json() or {}).get('Token') or {}).get('Value')


def enviar(orden):
    token = login()
    if not token:
        print('No se pudo obtener el token.')
        return
    r = req_lib.post(f'{BASE}/api/order/send',
                     json={'ApiKey': API_KEY, 'LoginToken': token,
                           'AnalysisLocation': LOCATION, 'Orders': [orden]},
                     headers={'Content-Type': 'application/json',
                              'analysisLocation': LOCATION}, timeout=40)
    print(f'\nENVIO  HTTP {r.status_code}')
    print('  ' + (r.text or '')[:900])


def main():
    if len(sys.argv) < 2 or not sys.argv[1].isdigit():
        print(__doc__)
        return 1
    venta_id = int(sys.argv[1])
    venta, items, pw = traer_venta(venta_id)
    orden = armar_orden(venta, items, pw)

    print(f'VENTA {venta_id} · {venta.get("numero_venta")} · {venta.get("metodo_pago")}')
    print(f'ORDEN ClearSale: {orden["ID"]}\n')
    print(json.dumps(orden, ensure_ascii=False, indent=2, default=str))

    print('\n' + '=' * 62)
    print('CAMPOS QUE NO PUDIMOS COMPLETAR')
    print('=' * 62)
    if not faltantes:
        print('  (ninguno)')
    for campo, motivo in faltantes:
        print(f'  {campo:<32} {motivo}')

    if '--custom' in sys.argv:
        probar_customfields(orden)
    elif '--grupos' in sys.argv:
        bisect_grupos(orden)
    elif '--bisect' in sys.argv:
        bisect(orden)
    elif '--enviar' in sys.argv:
        enviar(orden)
    else:
        print('\n(no se envio nada — agregá --enviar para mandarlo al sandbox)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
