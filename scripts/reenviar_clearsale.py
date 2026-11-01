#!/usr/bin/env python3
"""Reenvía a ClearSale una venta que quedó en ERR, reconstruyendo la orden
desde la base.

Existe por el caso PW-1041164792: una fecha de nacimiento mal formada
('20001-08-0', producto de un `[:10]` sobre un año de 5 dígitos) hizo que
ClearSale rechazara la orden entera con HTTP 400. La venta se cobró bien pero
quedó sin análisis de fraude y con la entrega bloqueada, y el job de respaldo
no reintenta los ERR a propósito (nunca entraron).

Por defecto SOLO MUESTRA el payload. Para enviarlo de verdad hay que pasar
--enviar. El ID de la orden es el número de venta, así que un reenvío de una
orden que nunca entró no genera duplicado.

Uso:
    venv/bin/python3 scripts/reenviar_clearsale.py PW-1041164792
    venv/bin/python3 scripts/reenviar_clearsale.py PW-1041164792 --nacimiento 2001-08-05
    venv/bin/python3 scripts/reenviar_clearsale.py PW-1041164792 --enviar
"""
import argparse
import json
import os
import re
import sys

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')


def conectar():
    return pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER'), password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME'), cursorclass=pymysql.cursors.DictCursor)


# Etiquetas que usa pago_payway al armar las notas. Se listan explícitamente
# porque los valores pueden tener espacios ("Sara Lionela Maciel") y las claves
# también ("Doc titular") o guión bajo ("OP_PAYWAY"): sin la lista, el corte
# entre un campo y el siguiente es adivinanza.
ETIQUETAS = ('PWID', 'OP_PAYWAY', 'Cuotas', 'Coef', 'Titular', 'Doc titular',
             'Vencimiento', 'Nacimiento', 'MPID', 'CUOTAS', 'VEID', 'SHID')


def dato_de_notas(notas, etiqueta):
    """Saca 'etiqueta: valor' de las notas, cortando en la etiqueta siguiente."""
    otras = '|'.join(re.escape(e) for e in ETIQUETAS if e != etiqueta)
    m = re.search(rf'\b{re.escape(etiqueta)}:\s*(.+?)(?=\s+(?:{otras}):|$)',
                  notas or '', re.S)
    return m.group(1).strip() if m else ''


def partir_direccion(texto, provincia):
    """'Calle 123, CIUDAD, Provincia CP 1166' -> (linea, ciudad, cp)."""
    cp = ''
    m = re.search(r'CP\s*(\d{4,8})', texto or '')
    if m:
        cp = m.group(1)
    partes = [p.strip() for p in re.split(r',', texto or '') if p.strip()]
    linea = partes[0] if partes else ''
    ciudad = partes[1] if len(partes) > 1 else (provincia or '')
    return linea, ciudad, cp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('numero_venta')
    ap.add_argument('--nacimiento', default='',
                    help='Fecha de nacimiento del titular YYYY-MM-DD. '
                         'Si no se pasa, la orden va SIN BirthDate (es opcional).')
    ap.add_argument('--enviar', action='store_true',
                    help='Enviar de verdad. Sin esto solo muestra el payload.')
    args = ap.parse_args()

    import clearsale
    import tienda_bp as tb

    cn = conectar(); cur = cn.cursor()
    cur.execute("""SELECT id, numero_venta, nombre_cliente, email_cliente,
                          telefono_cliente, dni_cliente, provincia_cliente,
                          direccion_entrega, tipo_entrega, metodo_envio,
                          importe_total, importe_abonado, costo_envio_vendedor,
                          fecha_venta, notas, clearsale_estado
                   FROM ventas WHERE numero_venta=%s""", (args.numero_venta,))
    v = cur.fetchone()
    if not v:
        print(f'No existe la venta {args.numero_venta}'); return 1

    cur.execute("""SELECT iv.sku, iv.cantidad, iv.precio_unitario,
                          COALESCE(pb.nombre, pc.nombre, iv.sku) nombre
                   FROM items_venta iv
                   LEFT JOIN productos_base pb ON pb.sku = iv.sku
                   LEFT JOIN productos_compuestos pc ON pc.sku = iv.sku
                   WHERE iv.venta_id=%s""", (v['id'],))
    items = cur.fetchall()

    # Datos de la tarjeta: del intento de Payway, que es la fuente real
    pwid = dato_de_notas(v['notas'], 'PWID')
    cur.execute("""SELECT payment_id, installments, card_brand, bin, last4, tid,
                          payment_method_id
                   FROM payway_intentos WHERE payment_id=%s""", (pwid or 0,))
    pw = cur.fetchone() or {}
    cur.close(); cn.close()

    linea, ciudad, cp = partir_direccion(v['direccion_entrega'], v['provincia_cliente'])

    cli = {
        'nombre':   v['nombre_cliente'],
        'email':    v['email_cliente'],
        'telefono': v['telefono_cliente'],
        'dni':      v['dni_cliente'],
        'direccion': linea,
        'calle': linea, 'altura': '',
        'ciudad': ciudad, 'provincia': v['provincia_cliente'], 'cp': cp,
        'tipo_entrega': v['tipo_entrega'],
        # Titular de la tarjeta, tal como quedó registrado
        '_holder_name': dato_de_notas(v['notas'], 'Titular'),
        '_holder_doc':  re.sub(r'\D', '', dato_de_notas(v['notas'], 'Doc titular')),
    }

    # La fecha de nacimiento solo va si se pasa y es válida. Nunca se inventa:
    # es un dato que el antifraude puntúa.
    if args.nacimiento:
        ok = tb._fecha_nacimiento_valida(args.nacimiento)
        if not ok:
            print(f'Fecha de nacimiento inválida: {args.nacimiento!r}. '
                  f'Debe ser YYYY-MM-DD y de una persona de 18 a 110 años.')
            return 1
        cli['_birth_date'] = ok

    cart_items = [{'sku': i['sku'], 'nombre': i['nombre'],
                   'cantidad': int(i['cantidad']),
                   'precio': float(i['precio_unitario'])} for i in items]

    flete = float(v['costo_envio_vendedor'] or 0)
    totales = {
        'productos': float(v['importe_total'] or 0) - flete,
        'total':     float(v['importe_abonado'] or v['importe_total'] or 0),
        'flete':     flete,
        'metodo_envio': v['metodo_envio'],
    }
    pago = {
        'payment_id':        pw.get('payment_id') or pwid,
        'installments':      pw.get('installments'),
        'bin':               pw.get('bin'),
        'last4':             pw.get('last4'),
        'tid':               pw.get('tid'),
        'payment_method_id': pw.get('payment_method_id'),
        'holder_name':       cli['_holder_name'],
        'holder_doc':        cli['_holder_doc'],
        'expiration':        dato_de_notas(v['notas'], 'Vencimiento'),
        'cupon':             dato_de_notas(v['notas'], 'OP_PAYWAY'),
    }

    orden = clearsale.armar_orden(v['numero_venta'], cli, cart_items, totales,
                                  pago, fecha=v['fecha_venta'])

    print(f"venta ............. {v['numero_venta']} (id {v['id']})")
    print(f"estado ClearSale .. {v['clearsale_estado'] or '(vacío)'}")
    print(f"modo ClearSale .... {clearsale.modo()}")
    print(f"BirthDate ......... {orden['BillingData'].get('BirthDate', '(no se manda)')}")
    print()
    print('PAYLOAD QUE SE ENVIARÍA:')
    print(json.dumps(orden, indent=2, ensure_ascii=False, default=str))
    print()

    if not args.enviar:
        print('>> Modo vista. Nada enviado. Agregá --enviar para mandarlo de verdad.')
        return 0

    print('>> Enviando a ClearSale...')
    clearsale.logger = None
    clearsale._procesar(v['id'], orden)

    cn = conectar(); cur = cn.cursor()
    cur.execute("SELECT clearsale_estado, clearsale_score FROM ventas WHERE id=%s",
                (v['id'],))
    fin = cur.fetchone()
    cur.close(); cn.close()
    print()
    print(f"estado despues .... {fin['clearsale_estado']}  score {fin['clearsale_score']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
