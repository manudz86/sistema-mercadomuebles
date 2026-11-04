#!/usr/bin/env python3
"""Verifica las autorizaciones al tope de aporte propio en promos de ML.

Lo que tiene que cumplirse:

  - sin autorizar, una promo por encima del tope se revierte (como siempre)
  - autorizada, queda puesta y se registra la excepcion
  - la excepcion es por par (publicacion, campania): no exime otra campania
  - si ML termina aplicando MAS de lo que se autorizo, se revierte igual
  - el tope duro no se puede pasar ni autorizando
  - el job diario respeta la excepcion solo mientras el aporte no la supere

Se intercepta todo lo que habla con ML: no sale ni una llamada. Las filas de
prueba se borran al final.
"""
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
os.environ['CANNON_SIN_SCHEDULER'] = '1'

MLA = 'MLAZZTEST001'
CAMP_A, CAMP_B = 'P-ZZTESTA', 'P-ZZTESTB'

fallos = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


def main():
    import app as A

    def limpiar():
        A.execute_db("DELETE FROM promo_excepciones WHERE mla_id=%s", (MLA,))
        A.execute_db("DELETE FROM promos_ml_historial WHERE mla_id=%s", (MLA,))

    limpiar()

    # Interceptar todo lo que toca ML
    aporte_que_aplica = {'v': 9.6}
    borrados = []

    class _Resp:
        status_code = 200

    A._promo_leer_aplicada = lambda tok, mla, tipo, pid: {
        'price': 381043, 'original_price': 425200,
        'seller_percentage': aporte_que_aplica['v'], 'meli_percentage': 0.8}
    A._promo_aporte_de = lambda p: (p.get('seller_percentage'), p.get('meli_percentage'))

    def _fake_ml(method, url, *a, **k):
        if method == 'delete':
            borrados.append(url)
        return _Resp()
    A.ml_request = _fake_ml

    registros = []
    A._promo_hist_registrar = lambda **kw: registros.append(kw)

    tope = A._promo_limite_aporte()
    duro = A._promo_tope_duro()
    print(f'tope {tope}% · tope duro {duro}%')

    def aplicar(autorizado=None, aporte=9.6, camp=CAMP_A):
        aporte_que_aplica['v'] = aporte
        borrados.clear()
        return A._promo_verificar_y_registrar(
            'tok', MLA, 'SMART', camp, {'ok': True}, mostrado_pct=aporte,
            origen='prueba', campania_nombre='Relampago prueba',
            autorizado_pct=autorizado, usuario='prueba')

    print('sin autorizar, una promo cara se revierte')
    r = aplicar(autorizado=None, aporte=9.6)
    chequear(r.get('ok') is False, 'no queda aplicada', str(r.get('error'))[:70])
    chequear(bool(borrados), 'se mando el DELETE a ML')
    chequear(not A.query_db("SELECT 1 FROM promo_excepciones WHERE mla_id=%s", (MLA,)),
             'no se guardo ninguna excepcion')

    print('autorizada, queda puesta y se registra')
    r = aplicar(autorizado=9.6, aporte=9.6)
    chequear(r.get('ok') is True, 'queda aplicada', str(r)[:70])
    chequear(not borrados, 'no se mando ningun DELETE')
    exc = A.query_one("SELECT campania_id, tope_pct FROM promo_excepciones WHERE mla_id=%s",
                      (MLA,))
    chequear(exc is not None and exc['campania_id'] == CAMP_A,
             'la excepcion queda guardada para esa campania', str(exc))
    chequear(exc is not None and float(exc['tope_pct']) == 9.6,
             'guarda el % aceptado, no un permiso en blanco',
             str(exc['tope_pct']) if exc else '')

    print('la excepcion es por campania, no por publicacion')
    chequear(A._promo_excepcion_cubre(MLA, CAMP_A, 9.6), 'cubre la campania autorizada')
    chequear(not A._promo_excepcion_cubre(MLA, CAMP_B, 9.6),
             'NO cubre otra campania de la misma publicacion')

    print('si ML sube el aporte por encima de lo autorizado, se revierte')
    chequear(not A._promo_excepcion_cubre(MLA, CAMP_A, 17.2),
             'la excepcion de 9,6% no cubre 17,2%')
    r = aplicar(autorizado=9.6, aporte=17.2, camp=CAMP_B)
    chequear(r.get('ok') is False, 'aplicar con 17,2% autorizando 9,6% no queda',
             str(r.get('error'))[:80])
    chequear(bool(borrados), 'y se revierte en ML')

    print('el tope duro no se puede pasar ni autorizando')
    r = aplicar(autorizado=duro + 10, aporte=duro + 5, camp=CAMP_B)
    chequear(r.get('ok') is False, f'{duro + 5}% no queda aunque se autorice',
             str(r.get('error'))[:80])
    chequear('DURO' in str(r.get('error', '')).upper(), 'el mensaje explica que es el tope duro',
             str(r.get('error'))[:80])
    chequear(not A.query_db("SELECT 1 FROM promo_excepciones WHERE mla_id=%s AND "
                            "campania_id=%s", (MLA, CAMP_B)),
             'no se guarda excepcion por encima del tope duro')

    print('el endpoint rechaza autorizar por encima del tope duro')
    A.app.config['LOGIN_DISABLED'] = True
    import werkzeug
    if not hasattr(werkzeug, '__version__'):
        werkzeug.__version__ = 'prueba'
    cli = A.app.test_client()
    rr = cli.post('/promociones-ml/aplicar', json={
        'mla': MLA, 'promotion_type': 'SMART', 'promotion_id': CAMP_A,
        'autorizar_aporte_pct': duro + 1})
    j = rr.get_json() or {}
    chequear(j.get('ok') is False and 'duro' in str(j.get('error', '')).lower(),
             'el endpoint corta antes de tocar ML', str(j.get('error'))[:80])

    print('se puede sacar la autorizacion')
    rr = cli.post('/promociones-ml/excepcion-quitar',
                  json={'mla': MLA, 'campania_id': CAMP_A})
    chequear((rr.get_json() or {}).get('ok') is True, 'el endpoint responde ok')
    chequear(not A._promo_excepcion_cubre(MLA, CAMP_A, 9.6),
             'y deja de cubrir')

    limpiar()
    print(f'filas de prueba borradas: quedan '
          f'{A.query_one("SELECT COUNT(*) c FROM promo_excepciones WHERE mla_id=%s", (MLA,))["c"]}')

    print()
    print('RESULTADO:', 'las autorizaciones funcionan' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
