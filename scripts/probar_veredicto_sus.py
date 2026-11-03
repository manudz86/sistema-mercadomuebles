#!/usr/bin/env python3
"""Verifica que un veredicto SUS dispare el circuito completo de rechazo.

El caso real: PW-1043068513 ($822.755) recibio SUS y no paso nada, porque el
codigo tenia SUS como "todavia analizando". Esta prueba corre
aplicar_veredicto_clearsale sobre una venta FICTICIA y comprueba que:

  - la venta pase a cancelada
  - se avise al comprador
  - se avise al equipo para devolver la plata
  - lo mismo valga para CAN, y que el aviso interno NO diga "ClearSale
    rechazo" cuando fue el comprador el que pidio cancelar
  - APG (primera etapa) NO dispare nada ni habilite la entrega

Los envios de mail y WhatsApp se interceptan: no sale nada hacia afuera.
La venta de prueba se crea y se borra.
"""
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')

fallos = []
enviados = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


def main():
    import tienda_bp as tb
    import clearsale as cs
    from flask import Flask

    app = Flask(__name__, root_path='/home/cannon/app',
                static_folder='/home/cannon/app/static',
                template_folder='/home/cannon/app/templates')
    app.secret_key = 'veredicto'
    app.register_blueprint(tb.tienda_bp, url_prefix='/tienda')

    # Interceptar solo las HOJAS que mandan algo hacia afuera, dejando correr
    # _cs_avisar_veredicto de verdad: es la que decide si el aviso interno es
    # de rechazo o de aprobacion, y reemplazarla entera tapaba esa rama.
    tb.avisar_estado_pago = lambda tipo, *a, **k: enviados.append(('comprador', tipo))
    tb._mail_interno = lambda v, **k: enviados.append(('interno', k.get('titulo', '')))

    db = tb.get_db(); cur = db.cursor()
    cur.execute("""INSERT INTO ventas (numero_venta, nombre_cliente, telefono_cliente,
                      email_cliente, importe_total, importe_abonado, metodo_pago,
                      canal, estado, estado_entrega, tipo_entrega, metodo_envio,
                      clearsale_estado)
                   VALUES ('ZZ-TEST-VEREDICTO','Prueba Veredicto','1100000000',
                      'prueba@invalido.local', 1000, 1000, 'Payway', 'tienda_web',
                      'ACTIVA','pendiente','envio','Flete Propio','AMA')""")
    db.commit()
    vid = cur.lastrowid
    print(f'venta de prueba creada: id {vid}')

    def estado_venta():
        # commit para renovar el snapshot: aplicar_veredicto_clearsale escribe
        # desde OTRA conexion y en REPEATABLE READ no veriamos su commit.
        db.commit()
        cur.execute("SELECT clearsale_estado, estado_entrega FROM ventas WHERE id=%s", (vid,))
        return cur.fetchone()

    def correr(desde, hasta):
        enviados.clear()
        cur.execute("UPDATE ventas SET clearsale_estado=%s, estado_entrega='pendiente' "
                    "WHERE id=%s", (desde, vid))
        db.commit()
        cur.execute("SELECT * FROM ventas WHERE id=%s", (vid,))
        v = cur.fetchone()
        with app.test_request_context('/'):
            tb.aplicar_veredicto_clearsale(v, hasta, score=0.87, origen='prueba')
        import time as _t, threading as _th
        for _h in _th.enumerate():          # esperar los avisos en hilo
            if _h is not _th.current_thread() and _h.daemon:
                _h.join(timeout=3)
        _t.sleep(0.3)
        return estado_venta()

    try:
        chequear(cs.modo() == '1', 'ClearSale esta en modo 1 (si no, no actua)', cs.modo())

        print('AMA -> SUS (el caso real)')
        r = correr('AMA', 'SUS')
        chequear(r['estado_entrega'] == 'cancelada', 'la venta queda cancelada',
                 r['estado_entrega'])
        chequear(('comprador', 'rechazado') in enviados, 'se avisa al comprador', str(enviados))
        chequear(any(t == 'interno' and 'rechaz' in x.lower() for t, x in enviados),
                 'se avisa al equipo, como rechazo', str(enviados))

        print('AMA -> CAN (el comprador pidio cancelar)')
        r = correr('AMA', 'CAN')
        chequear(r['estado_entrega'] == 'cancelada', 'la venta queda cancelada',
                 r['estado_entrega'])
        chequear(any(t == 'interno' and 'comprador' in x.lower() for t, x in enviados),
                 'se avisa al equipo, hablando del comprador', str(enviados))

        print('NVO -> APG (primera etapa, no es veredicto)')
        r = correr('NVO', 'APG')
        chequear(r['estado_entrega'] == 'pendiente', 'la venta NO se cancela',
                 r['estado_entrega'])
        chequear(not enviados, 'no se avisa a nadie', str(enviados))
        chequear(cs.bloquea_entrega('APG', '1')[0], 'y sigue bloqueando la entrega')

        print('AMA -> APA (aprobada de verdad)')
        r = correr('AMA', 'APA')
        chequear(r['estado_entrega'] == 'pendiente', 'la venta sigue activa')
        chequear(not cs.bloquea_entrega('APA', '1')[0], 'se habilita la entrega')

        # El texto del aviso interno segun el estado
        print('el aviso interno distingue CAN de un rechazo')
        import importlib
        tb2 = importlib.reload(__import__('tienda_bp'))
        textos = {}
        tb2._mail_interno = lambda v, **k: textos.update(k)
        cur.execute("SELECT * FROM ventas WHERE id=%s", (vid,))
        v = cur.fetchone()
        with app.test_request_context('/'):
            tb2._aviso_interno_rechazo(v, 'CAN')
            can_tit = textos.get('titulo', '')
            tb2._aviso_interno_rechazo(v, 'SUS')
            sus_tit = textos.get('titulo', '')
        chequear('comprador' in can_tit.lower(), 'CAN: habla del comprador', can_tit)
        chequear('rechaz' in sus_tit.lower(), 'SUS: habla de rechazo', sus_tit)
    finally:
        cur.execute("DELETE FROM ventas WHERE id=%s AND numero_venta='ZZ-TEST-VEREDICTO'", (vid,))
        db.commit()
        cur.execute("SELECT COUNT(*) n FROM ventas WHERE id=%s", (vid,))
        print(f'venta de prueba borrada: quedan {cur.fetchone()["n"]}')
        cur.close(); db.close()

    print()
    print('RESULTADO:', 'el circuito de veredicto funciona' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
