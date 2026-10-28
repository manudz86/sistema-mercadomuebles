#!/usr/bin/env python3
"""Prueba la maquina de estados del webhook (parte 3 del modo '1') sin tocar
la configuracion de produccion: parchea clearsale.modo() para que devuelva
'1' solo dentro de este proceso.

Verifica, sobre una venta SIMUL-:
  * que una aprobacion dispare el aviso 'confirmado'
  * que un rechazo cancele la venta y dispare 'rechazado' + aviso interno
  * que una reversion del rechazo devuelva la venta a activas
  * que un reintento del mismo estado no vuelva a avisar

Uso:
    venv/bin/python3 scripts/probar_webhook_modo1.py <numero_venta> [--mandar]

Sin --mandar NO envia mails ni WhatsApp: solo muestra que se dispararia y
comprueba el efecto sobre la base.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _common import cargar_env, conectar_db  # noqa: E402

for _k, _v in (cargar_env() or {}).items():
    os.environ.setdefault(_k, _v)

import clearsale  # noqa: E402
import tienda_bp as T  # noqa: E402

clearsale.modo = lambda: '1'          # solo en este proceso
T.clearsale = clearsale

MANDAR = '--mandar' in sys.argv
enviados = []
if not MANDAR:
    T.avisar_estado_pago = lambda tipo, nom, num, **k: enviados.append(('comprador', tipo, num))
    T._aviso_interno_rechazo = lambda venta, estado: enviados.append(('interno', estado, venta.get('numero_venta')))


def estado_actual(numero):
    db = conectar_db(False); cur = db.cursor()
    cur.execute("""SELECT id, clearsale_estado, estado_entrega
                   FROM ventas WHERE numero_venta=%s""", (numero,))
    r = cur.fetchone(); cur.close(); db.close()
    return r


def simular_webhook(numero, nuevo_estado):
    """Llama al handler real con un payload como el de ClearSale."""
    import werkzeug
    if not hasattr(werkzeug, '__version__'):
        werkzeug.__version__ = '3'    # el test_client lo lee y esta version no lo expone
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(T.tienda_bp)
    key = os.getenv('CLEARSALE_API_KEY', '')
    with app.test_client() as c:
        r = c.post('/tienda/webhook/clearsale',
                   json={'ID': numero, 'Status': nuevo_estado, 'Score': ''},
                   headers={'clearsale-apikey': key})
    return r.status_code


def paso(numero, nuevo, etiqueta):
    enviados.clear()
    antes = estado_actual(numero)
    code = simular_webhook(numero, nuevo)
    despues = estado_actual(numero)
    print(f'\n{etiqueta}')
    print(f'  webhook HTTP {code}')
    print(f'  clearsale_estado : {antes["clearsale_estado"]} -> {despues["clearsale_estado"]}')
    print(f'  estado_entrega   : {antes["estado_entrega"]} -> {despues["estado_entrega"]}')
    import time; time.sleep(1.5)      # el aviso va en un hilo
    print(f'  avisos           : {enviados or "ninguno"}')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        return 1
    numero = args[0]
    if not numero.upper().startswith('SIMUL-'):
        print('Por seguridad solo corre sobre ventas SIMUL-.')
        return 2
    if not estado_actual(numero):
        print(f'No existe {numero}')
        return 2
    print(f'Venta {numero} · modo forzado a 1 · '
          f'{"MANDA mails/WhatsApp de verdad" if MANDAR else "sin mandar nada"}')

    paso(numero, 'AMA', '1) vuelve a analisis (no deberia avisar)')
    paso(numero, 'APM', '2) aprobada  -> debe avisar confirmado')
    paso(numero, 'APM', '3) reintento del mismo estado -> no debe avisar')
    paso(numero, 'RPM', '4) rechazada -> cancela + avisa rechazado + interno')
    paso(numero, 'APM', '5) revierten el rechazo -> reactiva + avisa confirmado')
    return 0


if __name__ == '__main__':
    sys.exit(main())
