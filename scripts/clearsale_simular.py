#!/usr/bin/env python3
"""Simula compras de la tienda por Payway y las manda a ClearSale, para
probar el circuito completo sin esperar a que entre una venta real.

El sandbox de ClearSale decide el resultado por el IMPORTE de la orden:
    <= 50        -> APA  aprobada automatica
    50 < x <= 100 -> RPA  rechazada automatica
    > 100        -> AMA  analisis manual (se resuelve desde el panel)

Por eso los importes son chicos y no el precio real de una almohada: son el
disparador del resultado que se quiere probar.

Uso:
    venv/bin/python3 scripts/clearsale_simular.py            # ver que haria
    venv/bin/python3 scripts/clearsale_simular.py --crear    # crear y enviar
    venv/bin/python3 scripts/clearsale_simular.py --listar   # estado actual
    venv/bin/python3 scripts/clearsale_simular.py --borrar   # limpiar

Las ventas se crean con el prefijo SIMUL- en numero_venta para poder
encontrarlas y borrarlas despues sin tocar nada real.

OJO: inserta filas reales en la tabla ventas. No descuenta stock (eso pasa
recien al pasar a proceso) y no dispara mails, porque no pasa por
pago_payway: inserta directo y llama a clearsale.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _common import cargar_env, conectar_db  # noqa: E402

for _k, _v in (cargar_env() or {}).items():
    os.environ.setdefault(_k, _v)

import clearsale  # noqa: E402

PREFIJO = 'SIMUL-'
EMAIL = 'manudz86@gmail.com'      # el usuario quiere recibir todo acá
SKU = 'PLATINO'

# Cuatro compradores distintos entre sí: nombre, documento, teléfono,
# domicilio de entrega, titular de la tarjeta y su documento, y tarjeta.
# Todo inventado.
CASOS = [
    {
        'clave': 'APA', 'monto': 30.0,
        'esperado': 'APA — aprobada automática',
        'nombre': 'Ramiro Beltran', 'dni': '28144902', 'telefono': '1148223017',
        'calle': 'Av. Cabildo', 'altura': '2340', 'piso': '7 B',
        'ciudad': 'Belgrano', 'provincia': 'Capital Federal', 'cp': '1428',
        'titular': 'RAMIRO BELTRAN', 'doc_titular': '28144902',
        'bin': '450799', 'last4': '3081', 'marca': 1, 'cuotas': 3,
        'nacimiento': '1980-03-17',
        'billing': None,                      # mismo domicilio que la entrega
    },
    {
        'clave': 'RPA', 'monto': 75.0,
        'esperado': 'RPA — rechazada automática',
        'nombre': 'Valeria Pignataro', 'dni': '35709164', 'telefono': '2214470255',
        'calle': 'Calle 50', 'altura': '1288', 'piso': '',
        'ciudad': 'La Plata', 'provincia': 'Buenos Aires', 'cp': '1900',
        'titular': 'GONZALO PIGNATARO', 'doc_titular': '30221877',
        'bin': '516585', 'last4': '7042', 'marca': 104, 'cuotas': 6,
        'nacimiento': '1991-11-02',
        # Paga un tercero y desde otro domicilio: el caso que más le interesa
        # ver a ClearSale.
        'billing': {'calle': 'Pasaje Ortiz 455', 'ciudad': 'Quilmes',
                    'provincia': 'Buenos Aires', 'cp': '1878'},
    },
    {
        'clave': 'AMA1', 'monto': 150.0,
        'esperado': 'AMA — análisis manual (aprobar desde el panel)',
        'nombre': 'Nicolas Ferreyra', 'dni': '31985640', 'telefono': '3514028866',
        'calle': 'Bv. San Juan', 'altura': '910', 'piso': '3 C',
        'ciudad': 'Cordoba', 'provincia': 'Cordoba', 'cp': '5000',
        'titular': 'NICOLAS FERREYRA', 'doc_titular': '31985640',
        'bin': '450995', 'last4': '1264', 'marca': 1, 'cuotas': 3,
        'nacimiento': '1986-07-29',
        'billing': None,
    },
    {
        'clave': 'AMA2', 'monto': 180.0,
        'esperado': 'AMA — análisis manual (rechazar desde el panel)',
        'nombre': 'Carla Monzon', 'dni': '40233715', 'telefono': '3415590744',
        'calle': 'Mendoza', 'altura': '3677', 'piso': '',
        'ciudad': 'Rosario', 'provincia': 'Santa Fe', 'cp': '2000',
        'titular': 'CARLA S MONZON', 'doc_titular': '40233715',
        'bin': '516117', 'last4': '9930', 'marca': 104, 'cuotas': 6,
        'nacimiento': '1997-01-23',
        'billing': {'calle': 'San Lorenzo 1420', 'ciudad': 'Rosario',
                    'provincia': 'Santa Fe', 'cp': '2000'},
    },
]


def _conn():
    """Conexión de escritura: estas ventas se crean y se borran de verdad."""
    return conectar_db(solo_lectura=False)


def listar():
    db = _conn(); cur = db.cursor()
    cur.execute("""SELECT id, numero_venta, nombre_cliente, importe_abonado,
                          clearsale_estado, clearsale_score, clearsale_order_id,
                          clearsale_actualizado, estado_entrega
                   FROM ventas WHERE numero_venta LIKE %s ORDER BY id""",
                (PREFIJO + '%',))
    filas = cur.fetchall()
    cur.close(); db.close()
    if not filas:
        print('No hay ventas simuladas.')
        return filas
    print(f'{"id":<7}{"numero_venta":<26}{"cliente":<20}{"$":>8}  '
          f'{"CS":<5}{"score":<7}{"entrega":<12}actualizado')
    print('-' * 108)
    for f in filas:
        print(f'{f["id"]:<7}{f["numero_venta"]:<26}{(f["nombre_cliente"] or "")[:19]:<20}'
              f'{float(f["importe_abonado"]):>8.0f}  '
              f'{str(f["clearsale_estado"] or "-"):<5}'
              f'{str(f["clearsale_score"] or "-"):<7}'
              f'{str(f["estado_entrega"] or "-"):<12}'
              f'{f["clearsale_actualizado"] or "-"}')
    return filas


def crear():
    ahora = datetime.now()
    sello = ahora.strftime('%m%d%H%M')
    db = _conn(); cur = db.cursor()
    creadas = []

    for c in CASOS:
        numero = f"{PREFIJO}{c['clave']}-{sello}"
        direccion = (f"{c['calle']} {c['altura']}"
                     + (f" {c['piso']}" if c['piso'] else '')
                     + f", {c['ciudad']}, {c['provincia']} CP {c['cp']}")
        notas = '\n'.join([
            'VENTA SIMULADA — prueba de ClearSale, no es una compra real',
            f"Titular: {c['titular']}",
            f"Doc titular: DNI {c['doc_titular']}",
            f"Nacimiento: {c['nacimiento']}",
            f"Tarjeta: {c['bin']}****{c['last4']} Cuotas: {c['cuotas']}",
        ])
        cur.execute("""
            INSERT INTO ventas (
                numero_venta, canal, nombre_cliente, telefono_cliente,
                email_cliente, dni_cliente, provincia_cliente,
                importe_total, importe_abonado, metodo_pago, tipo_entrega,
                metodo_envio, direccion_entrega, estado_pago, estado_entrega,
                estado, costo_flete, pago_mercadopago, stock_descontado,
                notas, fecha_venta, fecha_registro
            ) VALUES (
                %s, 'tienda_web', %s, %s,
                %s, %s, %s,
                %s, %s, 'Payway', 'envio',
                'Flete Propio', %s, 'pagado', 'pendiente',
                'ACTIVA', 0, 0, 0,
                %s, %s, %s
            )""", (numero, c['nombre'], c['telefono'], EMAIL, c['dni'],
                   c['provincia'], c['monto'], c['monto'], direccion,
                   notas, ahora, ahora))
        venta_id = cur.lastrowid
        cur.execute("""INSERT INTO items_venta (venta_id, sku, cantidad, precio_unitario)
                       VALUES (%s, %s, 1, %s)""", (venta_id, SKU, c['monto']))
        db.commit()
        creadas.append((venta_id, numero, c))
        print(f'  venta {venta_id} {numero}  ${c["monto"]:.0f}  {c["nombre"]}')

    cur.close(); db.close()
    return creadas


def enviar(creadas):
    """Usa el mismo camino que la tienda: armar_orden + _procesar, que envía,
    verifica que la orden exista y guarda el estado en la venta."""
    for venta_id, numero, c in creadas:
        cli = {
            'nombre': c['nombre'], 'email': EMAIL, 'dni': c['dni'],
            'telefono': c['telefono'], 'calle': c['calle'],
            'altura': c['altura'], 'piso_depto': c['piso'],
            'ciudad': c['ciudad'], 'provincia': c['provincia'], 'cp': c['cp'],
            'tipo_entrega': 'envio',
            '_birth_date': c['nacimiento'],
            '_capi_ip': c.get('ip', '181.47.' + str(venta_id % 250) + '.10'),
            '_capi_ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/151.0',
            '_cs_session': clearsale.nuevo_session_id(numero),
        }
        if c['billing']:
            cli['_billing'] = c['billing']
        orden = clearsale.armar_orden(
            numero_venta=numero, cli=cli,
            cart_items=[{'sku': SKU, 'nombre': 'Almohada Platino',
                         'precio': c['monto'], 'cantidad': 1}],
            totales={'productos': c['monto'], 'total': c['monto'],
                     'flete': 0, 'metodo_envio': 'Flete Propio'},
            pago={'bin': c['bin'], 'last4': c['last4'],
                  'payment_method_id': c['marca'], 'installments': c['cuotas'],
                  'holder_name': c['titular'], 'holder_doc': c['doc_titular'],
                  'expiration': '08/2031',
                  'payment_id': f'SIM{venta_id}', 'auth_code': '0' + str(venta_id)[-5:],
                  'tid': None, 'valdom': 'VTE0011',
                  'bank_code': None, 'bank_desc': None},
            fecha=datetime.now())
        print(f'\n  --> {numero} (espera {c["esperado"]})')
        clearsale._procesar(venta_id, orden)


def borrar():
    db = _conn(); cur = db.cursor()
    cur.execute("SELECT id, numero_venta FROM ventas WHERE numero_venta LIKE %s",
                (PREFIJO + '%',))
    filas = cur.fetchall()
    if not filas:
        print('No hay nada que borrar.')
        cur.close(); db.close(); return
    ids = [f['id'] for f in filas]
    print('Se van a borrar estas ventas y sus items:')
    for f in filas:
        print(f'  {f["id"]}  {f["numero_venta"]}')
    marcas = ','.join(['%s'] * len(ids))
    cur.execute(f"DELETE FROM items_venta WHERE venta_id IN ({marcas})", ids)
    n_items = cur.rowcount
    cur.execute(f"DELETE FROM ventas WHERE id IN ({marcas})", ids)
    n_ventas = cur.rowcount
    db.commit(); cur.close(); db.close()
    print(f'\nBorradas {n_ventas} venta(s) y {n_items} item(s).')


def main():
    print(f'ClearSale: {clearsale._base()}  ·  modo={clearsale.modo()}\n')
    if '--listar' in sys.argv:
        listar(); return 0
    if '--borrar' in sys.argv:
        borrar(); return 0
    if '--crear' not in sys.argv:
        print('Simularía estas 4 compras (1 Almohada Platino cada una):\n')
        for c in CASOS:
            tercero = ' · paga un tercero' if c['billing'] else ''
            print(f"  ${c['monto']:>6.0f}  {c['esperado']:<46} "
                  f"{c['nombre']}{tercero}")
        print('\nCorré con --crear para hacerlo de verdad.')
        return 0
    print('CREANDO VENTAS')
    creadas = crear()
    print('\nENVIANDO A CLEARSALE')
    enviar(creadas)
    print('\nRESULTADO')
    listar()
    return 0


if __name__ == '__main__':
    sys.exit(main())
