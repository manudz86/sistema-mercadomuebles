#!/usr/bin/env python3
"""Envia un mail de confirmacion de compra FICTICIO usando la funcion real del
sistema (tienda_bp.enviar_email_confirmacion), para validar la plantilla HTML y
el SMTP configurado. NO registra ninguna venta ni toca la base.

Uso:  venv/bin/python3 scripts/test_mail_confirmacion.py destino@mail.com
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from tienda_bp import enviar_email_confirmacion, enviar_email_vendedor  # noqa: E402

ITEMS = [
    {'sku': 'CDOP140', 'nombre': 'Colchón Cannon Doral Pillow 140x190',
     'precio': 610080.0, 'cantidad': 1},
    {'sku': 'ALM70', 'nombre': 'Almohada Cannon', 'precio': 25000.0, 'cantidad': 2},
]


def main():
    destino = sys.argv[1] if len(sys.argv) > 1 else None
    if not destino:
        print(__doc__)
        return 1

    ref = 'PRUEBA-' + datetime.now().strftime('%H%M%S')
    total = sum(i['precio'] * i['cantidad'] for i in ITEMS) + 19999

    print(f'SMTP en uso : {os.getenv("MAIL_SMTP_HOST")}:{os.getenv("MAIL_SMTP_PORT")}')
    print(f'Remitente   : {os.getenv("MAIL_FROM")}')
    print(f'Destino     : {destino}')
    print(f'Referencia  : {ref}  (ficticia, no se registra venta)\n')

    with app.app_context():
        print('1) Mail de confirmacion al CLIENTE ...')
        try:
            enviar_email_confirmacion(
                payment_id=ref,
                nombre_cliente='Manuel (prueba)',
                email_cliente=destino,
                items=ITEMS,
                tipo_entrega='envio',
                direccion='Calle de Prueba 123, CABA CP 1406',
                fecha_entrega=None,
                importe_total=total,
                costo_flete=19999,
                canal='getnet',
            )
            print('   OK\n')
        except Exception as e:
            print(f'   ERROR: {type(e).__name__}: {e}\n')
            return 1

        print('2) Mail de aviso al VENDEDOR ...')
        try:
            enviar_email_vendedor(
                ref, 'Manuel (prueba)', destino, '1122334455',
                ITEMS, 'envio', 'Calle de Prueba 123, CABA CP 1406', total,
                metodo_envio='Flete Propio', canal='getnet',
            )
            print('   OK\n')
        except Exception as e:
            print(f'   ERROR: {type(e).__name__}: {e}\n')
            return 1

    print('Listo: revisa la casilla (y Spam).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
