#!/usr/bin/env python3
"""Reconstruye el payload EXACTO que clearsale.armar_orden le manda a
ClearSale para una venta real, y busca por biseccion qué parte hace que
ClearSale la descarte en silencio (responde 200/NVO y después la orden no
existe).

A diferencia de scripts/clearsale_orden.py, que arma su propio payload,
este importa el módulo productivo: lo que se prueba es el código que corre
en la tienda, no una reconstrucción parecida.

Uso:
    venv/bin/python3 scripts/clearsale_prod_diag.py <venta_id>
    venv/bin/python3 scripts/clearsale_prod_diag.py <venta_id> --enviar

Sin --enviar no sale ninguna petición: solo imprime el payload.
No escribe nada en la base.
"""
import json
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests as req_lib  # noqa: E402
from _common import cargar_env, conectar_db  # noqa: E402

# clearsale.py lee credenciales y base de datos de os.environ, que a Gunicorn
# se lo inyecta systemd. Para que el modulo se comporte igual que en vivo hay
# que poblar el entorno ANTES de importarlo.
for _k, _v in (cargar_env() or {}).items():
    os.environ.setdefault(_k, _v)

import clearsale  # el módulo productivo  # noqa: E402
from clearsale_probe import _orden as orden_base, ITEMS_EJEMPLO  # noqa: E402


# Las notas son una sola linea con etiquetas pegadas ("Titular: X Vencimiento:
# Y ..."), asi que el corte de cada valor tiene que ser la etiqueta siguiente
# y no una heuristica: "Domicilio resumen" tiene dos palabras y la rompia.
ETIQUETAS = ['PWID', 'OP_PAYWAY', 'Cuotas', 'Coeficiente', 'Coef',
             'Titular', 'Doc titular', 'Vencimiento', 'Nacimiento',
             'Domicilio resumen', 'Cupon', 'Autorizacion']


def _nota(notas, campo):
    otras = '|'.join(re.escape(e) for e in ETIQUETAS if e != campo)
    m = re.search(rf'{re.escape(campo)}:\s*(.+?)\s*(?:(?:{otras}):|$)',
                  notas or '', re.S)
    return m.group(1).strip() if m else ''


def reconstruir(venta_id):
    """Rearma los dicts cli/cart_items/totales/pago tal como los tenía
    pago_payway en memoria, a partir de lo que quedó guardado."""
    db = conectar_db(solo_lectura=True)
    cur = db.cursor()
    cur.execute("SELECT * FROM ventas WHERE id=%s", (venta_id,))
    v = cur.fetchone()
    if not v:
        raise SystemExit(f'No existe la venta {venta_id}')
    # El nombre sale de las DOS tablas de producto, como en el detalle de la
    # venta (app.py): los sommiers y combos no estan en productos_base sino en
    # productos_compuestos. Joineando solo contra base, un SEX160 llegaba a
    # ClearSale como "SEX160" pelado, que al analista no le dice nada.
    # (El flujo productivo de Payway no pasa por aca: el nombre ya viene en el
    # carrito. Esto es solo para rearmar una venta ya cerrada.)
    cur.execute("""SELECT iv.sku, iv.cantidad, iv.precio_unitario,
                          COALESCE(pb.nombre, pc.nombre, iv.sku) AS nombre
                   FROM items_venta iv
                   LEFT JOIN productos_base pb       ON pb.sku = iv.sku
                   LEFT JOIN productos_compuestos pc ON pc.sku = iv.sku
                   WHERE iv.venta_id=%s""", (venta_id,))
    items = cur.fetchall()
    notas = v.get('notas') or ''
    pw = {}
    m = re.search(r'PWID:\s*(\d+)', notas)
    if m:
        cur.execute("""SELECT payment_id, bin, last4, card_brand, installments,
                              tid, raw_json
                       FROM payway_intentos WHERE payment_id=%s""", (int(m.group(1)),))
        pw = cur.fetchone() or {}
    cur.close(); db.close()

    raw = {}
    if pw.get('raw_json'):
        raw = (pw['raw_json'] if isinstance(pw['raw_json'], dict)
               else json.loads(pw['raw_json']))
    det = raw.get('status_details') or {}

    # cli: mismo shape que el dict de sesión que usa pago_payway
    calle, altura, ciudad, prov, cp = _partir(v.get('direccion_entrega'),
                                              v.get('provincia_cliente'))
    cli = {
        'nombre': v.get('nombre_cliente'), 'email': v.get('email_cliente'),
        'dni': v.get('dni_cliente'), 'telefono': v.get('telefono_cliente'),
        'calle': calle, 'altura': altura, 'ciudad': ciudad,
        'provincia': prov, 'cp': cp, 'piso_depto': '',
        'tipo_entrega': v.get('tipo_entrega'),
        '_capi_ip': '181.47.1.1', '_capi_ua': 'Mozilla/5.0',
        # En vivo lo genera checkout() y lo inyecta en el script csdp; acá se
        # genera igual para que el payload de prueba tenga la misma forma.
        '_cs_session': clearsale.nuevo_session_id(v.get('numero_venta')),
    }
    nac = _nota(notas, 'Nacimiento')
    if nac:
        cli['_birth_date'] = nac
    resumen = _nota(notas, 'Domicilio resumen')
    if resumen:
        bc, ba, bci, bpr, bcp = _partir(resumen, v.get('provincia_cliente'))
        cli['_billing'] = {'calle': f'{bc} {ba}'.strip(), 'ciudad': bci,
                           'cp': bcp, 'provincia': bpr}

    flete = float(v.get('costo_flete') or 0)
    total = float(v.get('importe_abonado') or 0)
    totales = {'productos': total - flete, 'total': total, 'flete': flete,
               'metodo_envio': v.get('metodo_envio')}
    # Ventas de Mercado Pago: no hay tabla de intentos, los datos de tarjeta
    # viven en la API de MP. Se traen con el MPID de las notas. Sirve para
    # probar el payload de ClearSale con una venta real cuando no entro
    # ninguna de Payway; la integracion productiva sigue siendo solo Payway.
    m_mp = re.search(r'MPID:\s*(\d+)', notas)
    if m_mp:
        pago = _pago_desde_mp(m_mp.group(1))
        pago['metodo'] = 'Mercado Pago'
        return v, cli, _cart(items), totales, pago

    err = (det.get('error') or {}).get('reason') or {}
    pago = {
        'bin': pw.get('bin'), 'last4': pw.get('last4'),
        'payment_method_id': raw.get('payment_method_id'),
        'installments': pw.get('installments'),
        'holder_name': _nota(notas, 'Titular'),
        # "Doc titular: DNI 12345678". Con --doc N se fuerza, para probar el
        # payload en ventas anteriores a que empezaramos a capturarlo.
        'holder_doc': (sys.argv[sys.argv.index('--doc') + 1]
                       if '--doc' in sys.argv else
                       re.sub(r'\D', '', _nota(notas, 'Doc titular'))),
        'expiration': _nota(notas, 'Vencimiento'),
        'payment_id': raw.get('id') or pw.get('payment_id'),
        'auth_code': det.get('card_authorization_code'),
        'cupon': det.get('ticket'), 'tid': pw.get('tid'),
        'valdom': det.get('address_validation_code'),
        'bank_code': err.get('id'), 'bank_desc': err.get('description'),
    }
    return v, cli, _cart(items), totales, pago


def _cart(items):
    return [{'sku': it['sku'], 'nombre': it['nombre'],
             'precio': float(it['precio_unitario']),
             'cantidad': int(it['cantidad'])} for it in items]


# Brand de Mercado Pago -> payment_method_id de Payway, que es lo que
# clearsale.armar_orden traduce a Credit Card Type. Asi no hay que tocar el
# modulo productivo para una prueba.
MP_A_PW = {'visa': 1, 'visa_debit': 1, 'debvisa': 1,
           'master': 104, 'mastercard': 104, 'debmaster': 104,
           'amex': 65, 'cabal': 63, 'naranja': 63, 'maestro': 104}


def _pago_desde_mp(payment_id):
    """GET a la API de Mercado Pago para traer los datos de la tarjeta de una
    venta de MP. Solo lectura. No imprime el token ni el numero completo."""
    token = os.environ.get('MP_ACCESS_TOKEN', '').strip()
    if not token:
        raise SystemExit('Falta MP_ACCESS_TOKEN en el entorno.')
    r = req_lib.get(f'https://api.mercadopago.com/v1/payments/{payment_id}',
                    headers={'Authorization': f'Bearer {token}'}, timeout=30)
    if r.status_code != 200:
        raise SystemExit(f'MP respondio {r.status_code}: {r.text[:300]}')
    p = r.json() or {}
    card = p.get('card') or {}
    tit = card.get('cardholder') or {}
    ident = tit.get('identification') or {}
    marca = str(p.get('payment_method_id') or '').lower()
    exp_m, exp_a = card.get('expiration_month'), card.get('expiration_year')
    print(f'  MP {payment_id}: {p.get("status")}/{p.get("status_detail")} '
          f'marca={marca} cuotas={p.get("installments")} '
          f'bin={card.get("first_six_digits")} last4={card.get("last_four_digits")}')
    return {
        'bin': card.get('first_six_digits'),
        'last4': card.get('last_four_digits'),
        'payment_method_id': MP_A_PW.get(marca),
        'installments': p.get('installments'),
        'holder_name': tit.get('name'),
        'holder_doc': re.sub(r'\D', '', str(ident.get('number') or '')),
        'holder_doc_type': (ident.get('type') or 'dni').lower(),
        'expiration': f'{int(exp_m):02d}/{exp_a}' if exp_m and exp_a else '',
        'payment_id': p.get('id'),
        'auth_code': p.get('authorization_code'),
        'cupon': (p.get('transaction_details') or {}).get('payment_method_reference_id'),
        'tid': None, 'valdom': None,
        'bank_code': None, 'bank_desc': p.get('status_detail'),
    }


def _partir(texto, prov_venta):
    """Misma heurística que usa el checkout para separar la dirección."""
    txt = (texto or '').strip()
    cp = ''
    m = re.search(r'\bCP\s*([0-9A-Za-z]+)\s*$', txt)
    if m:
        cp = m.group(1)
        txt = txt[:m.start()].rstrip(' ,')
    partes = [p.strip() for p in txt.split(',') if p.strip()]
    calle_full = partes[0] if partes else ''
    ciudad = partes[1] if len(partes) > 1 else ''
    prov = partes[2] if len(partes) > 2 else (prov_venta or '')
    m2 = re.match(r'^(.*?)\s+(\d+[A-Za-z]?)$', calle_full)
    calle, altura = (m2.group(1), m2.group(2)) if m2 else (calle_full, '')
    return calle, altura, ciudad, prov, cp


# ── biseccion ────────────────────────────────────────────────────────────────
def bisecar(orden, token):
    """Dos direcciones a la vez:
       QUITA-*  = la orden real sin un bloque (si aparece, ese bloque la mataba)
       SUMA-*   = la base conocida-buena con un bloque de la real encima
    """
    import copy
    suf = uuid.uuid4().hex[:6]
    casos = []

    def _quita(nombre, fn):
        o = copy.deepcopy(orden)
        o['ID'] = f'DIAG-Q-{nombre}-{suf}'
        fn(o)
        casos.append((o['ID'], f'QUITA {nombre}', o))

    def _suma(nombre, fn):
        o = orden_base(f'DIAG-S-{nombre}-{suf}', ITEMS_EJEMPLO)
        fn(o)
        casos.append((o['ID'], f'SUMA  {nombre}', o))

    _quita('FULL',     lambda o: None)
    _quita('CUSTOM',   lambda o: o.pop('CustomFields', None))
    _quita('OBS',      lambda o: o.pop('Obs', None))
    _quita('NACIM',    lambda o: (o['BillingData'].pop('BirthDate', None),
                                  o['ShippingData'].pop('BirthDate', None)))
    _quita('BILLING',  lambda o: o.update({'BillingData': o['ShippingData']}))
    _quita('ITEMS',    lambda o: o.update({'Items': ITEMS_EJEMPLO}))
    _quita('PAGO',     lambda o: o.update({'Payments': [
        dict(p, CardBin=p.get('CardBin') or '516585',
             CardEndNumber=p.get('CardEndNumber') or '7711')
        for p in o['Payments']]}))

    _suma('PERSONAS',  lambda o: o.update({'BillingData': orden['BillingData'],
                                           'ShippingData': orden['ShippingData']}))
    _suma('PAGO',      lambda o: o.update({'Payments': orden['Payments']}))
    _suma('ITEMS',     lambda o: o.update({'Items': orden['Items']}))
    _suma('CUSTOM',    lambda o: o.update({'CustomFields': orden.get('CustomFields', [])}))
    _suma('OBS',       lambda o: o.update({'Obs': orden.get('Obs', '')}))
    _suma('TOTALES',   lambda o: o.update({
        'TotalItems': orden['TotalItems'], 'TotalOrder': orden['TotalOrder'],
        'TotalShipping': orden['TotalShipping']}))
    _suma('CABECERA',  lambda o: o.update({
        'Email': orden['Email'], 'Date': orden['Date'],
        'IP': orden['IP'], 'Origin': orden['Origin']}))

    api_key = clearsale._creds()[0]
    base = clearsale._base()
    print(f'\nENVIANDO {len(casos)} variantes, de a una ({base}):')
    for oid, nombre, o in casos:
        try:
            r = req_lib.post(f'{base}/api/order/send',
                             json={'ApiKey': api_key, 'LoginToken': token,
                                   'AnalysisLocation': 'ARG', 'Orders': [o]},
                             headers={'Content-Type': 'application/json',
                                      'analysisLocation': 'ARG'}, timeout=40)
            # El cuerpo del error es lo unico que explica un descarte: en
            # produccion siempre vimos 200 y nunca llegamos a leerlo.
            cuerpo = '' if r.status_code == 200 else ' ' + r.text[:400]
            print(f'    {oid:<30} {nombre:<16} HTTP {r.status_code}{cuerpo}')
        except Exception as e:
            print(f'    {oid:<30} {nombre:<16} EXC {type(e).__name__}: {e}')
    print('\n  Consultalas con:')
    print('  venv/bin/python3 scripts/clearsale_probe.py get '
          + ' '.join(i for i, _, _ in casos))


def bisecar_customfields(orden, token):
    """El bloque CustomFields es lo que descarta la orden. Aisla CUAL de los
    cuatro, y si el problema es el nombre o el "Type": cada campo va solo,
    primero con el Type del catalogo (lo que manda clearsale.py) y despues
    con Type 1, que es lo que mandaba el script viejo que SI entregaba."""
    suf = uuid.uuid4().hex[:6]
    casos = []
    reales = orden.get('CustomFields') or []

    o = orden_base(f'CF2-CTRL-{suf}', ITEMS_EJEMPLO)
    o.pop('CustomFields', None)
    casos.append((o['ID'], 'control sin CF', o))

    # El ID lleva un indice: truncar el nombre hacia colisionar SHIPPING_TYPE
    # con SHIPPING_METHOD, y una variante pisaba a la otra.
    n = 0
    for cf in reales:
        for tipo in dict.fromkeys([cf['Type'], 1]):   # sin repetir si ya es 1
            n += 1
            oo = orden_base(f'CF2-{n:02d}-T{tipo}-{suf}', ITEMS_EJEMPLO)
            oo['CustomFields'] = [{'Name': cf['Name'], 'Type': tipo,
                                   'Value': cf['Value']}]
            casos.append((oo['ID'], f'{cf["Name"]} Type={tipo}', oo))

    # Los cuatro juntos con Type 1, que es la combinacion que usaba el script.
    oo = orden_base(f'CF2-TODOS-T1-{suf}', ITEMS_EJEMPLO)
    oo['CustomFields'] = [{'Name': c['Name'], 'Type': 1, 'Value': c['Value']}
                          for c in reales]
    casos.append((oo['ID'], 'los 4 con Type=1', oo))

    api_key = clearsale._creds()[0]
    base = clearsale._base()
    print(f'\nENVIANDO {len(casos)} variantes de CustomFields, de a una:')
    for oid, nombre, oo in casos:
        try:
            r = req_lib.post(f'{base}/api/order/send',
                             json={'ApiKey': api_key, 'LoginToken': token,
                                   'AnalysisLocation': 'ARG', 'Orders': [oo]},
                             headers={'Content-Type': 'application/json',
                                      'analysisLocation': 'ARG'}, timeout=40)
            cuerpo = '' if r.status_code == 200 else ' ' + r.text[:300]
            print(f'    {oid:<34} {nombre:<28} HTTP {r.status_code}{cuerpo}')
        except Exception as e:
            print(f'    {oid:<34} {nombre:<28} EXC {type(e).__name__}: {e}')
    print('\n  Consultalas con:')
    print('  venv/bin/python3 scripts/clearsale_probe.py get '
          + ' '.join(i for i, _, _ in casos))


def bisecar_nombres(orden, token):
    """BillingData tiene que ser el TITULAR de la tarjeta, no el comprador.
    Del titular sabemos nombre y domicilio, pero no el DNI: hay que ver si
    ClearSale acepta la persona sin LegalDocument antes de mandarle el DNI
    del comprador, que seria un dato falso."""
    import copy
    suf = uuid.uuid4().hex[:6]
    casos = []
    TITULAR = 'MATIAS DZIENCIELSKY'

    def _v(nombre, fn):
        o = copy.deepcopy(orden)
        o['ID'] = f'NOM-{nombre}-{suf}'
        o['BillingData'] = copy.deepcopy(o['BillingData'])
        fn(o)
        casos.append((o['ID'], nombre, o))

    _v('CTRL',    lambda o: None)
    _v('NOMDIST', lambda o: o['BillingData'].update({'Name': TITULAR}))
    _v('SINDOC',  lambda o: o['BillingData'].pop('LegalDocument', None))
    _v('DOCVACIO', lambda o: o['BillingData'].update({'LegalDocument': ''}))
    _v('AMBOS',   lambda o: (o['BillingData'].update({'Name': TITULAR}),
                             o['BillingData'].pop('LegalDocument', None)))
    _v('SINMAIL', lambda o: (o['BillingData'].update({'Name': TITULAR}),
                             o['BillingData'].pop('LegalDocument', None),
                             o['BillingData'].pop('Email', None),
                             o['BillingData'].pop('Phones', None)))

    api_key = clearsale._creds()[0]
    base = clearsale._base()
    print(f'\nENVIANDO {len(casos)} variantes de nombres, de a una:')
    for oid, nombre, o in casos:
        try:
            r = req_lib.post(f'{base}/api/order/send',
                             json={'ApiKey': api_key, 'LoginToken': token,
                                   'AnalysisLocation': 'ARG', 'Orders': [o]},
                             headers={'Content-Type': 'application/json',
                                      'analysisLocation': 'ARG'}, timeout=40)
            cuerpo = '' if r.status_code == 200 else ' ' + r.text[:300]
            print(f'    {oid:<28} {nombre:<10} HTTP {r.status_code}{cuerpo}')
        except Exception as e:
            print(f'    {oid:<28} {nombre:<10} EXC {type(e).__name__}: {e}')
    print('\n  Consultalas con:')
    print('  venv/bin/python3 scripts/clearsale_probe.py get '
          + ' '.join(i for i, _, _ in casos))


def main():
    if len(sys.argv) < 2 or not sys.argv[1].isdigit():
        print(__doc__)
        return 1
    venta_id = int(sys.argv[1])
    v, cli, cart, totales, pago = reconstruir(venta_id)
    orden = clearsale.armar_orden(
        numero_venta=v.get('numero_venta'), cli=cli, cart_items=cart,
        totales=totales, pago=pago, fecha=v.get('fecha_venta'))

    print(f"=== venta {venta_id} ({v.get('numero_venta')}) — "
          f"payload de clearsale.armar_orden ===")
    print(json.dumps(orden, indent=2, ensure_ascii=False, default=str))

    if '--enviar' not in sys.argv:
        print('\n(sin --enviar no se mandó nada)')
        return 0
    # Token y ApiKey tienen que salir de la MISMA fuente que usa la tienda:
    # mezclar el token del probe (.env) con el ApiKey del modulo da 400.
    token = clearsale._login()
    if not token:
        print('No se pudo obtener el token con las credenciales del modulo.')
        return 3
    if '--cf' in sys.argv:
        bisecar_customfields(orden, token)
    elif '--nombres' in sys.argv:
        bisecar_nombres(orden, token)
    elif '--real' in sys.argv:
        # Manda la orden con su ID de verdad, para que quede en el panel de
        # ClearSale con el numero de venta. NO toca la base: el campo
        # clearsale_estado se actualiza aparte.
        api_key = clearsale._creds()[0]
        r = req_lib.post(f'{clearsale._base()}/api/order/send',
                         json={'ApiKey': api_key, 'LoginToken': token,
                               'AnalysisLocation': 'ARG', 'Orders': [orden]},
                         headers={'Content-Type': 'application/json',
                                  'analysisLocation': 'ARG'}, timeout=40)
        print(f"\nenviada {orden['ID']} -> HTTP {r.status_code} "
              f"{'' if r.status_code == 200 else r.text[:300]}")
        print(f"  verificar: venv/bin/python3 scripts/clearsale_probe.py get {orden['ID']}")
    else:
        bisecar(orden, token)
    return 0


if __name__ == '__main__':
    sys.exit(main())
