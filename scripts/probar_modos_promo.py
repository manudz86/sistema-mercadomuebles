#!/usr/bin/env python3
"""Verifica los tres estados del 2x1 y del envío sin cargo en CABA.

  '0'    -> apagada siempre
  '1'    -> encendida siempre
  'auto' -> encendida solo mientras el evento este activo

Falsea la tabla configuracion en memoria: no toca la base ni el panel.
"""
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')

fallos = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


class CursorFalso:
    def __init__(self, cfg): self.cfg = cfg; self._r = None
    def execute(self, sql, params=None):
        s = sql.strip().upper()
        if s.startswith('INSERT'):
            self._r = None; return
        if 'LIKE' in s:                      # la query de get_hot_event
            self._r = [{'clave': k, 'valor': v} for k, v in self.cfg.items()]
        else:                                # SELECT valor WHERE clave=%s
            clave = params[0] if params else ''
            self._r = {'valor': self.cfg.get(clave, '0')}
    def fetchall(self): return self._r if isinstance(self._r, list) else []
    def fetchone(self): return self._r if isinstance(self._r, dict) else None
    def close(self): pass


class DbFalsa:
    def __init__(self, cfg): self.cfg = cfg
    def cursor(self): return CursorFalso(self.cfg)
    def commit(self): pass
    def close(self): pass


def main():
    import tienda_bp as tb
    from flask import Flask
    from zoneinfo import ZoneInfo

    ahora = datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).replace(tzinfo=None)

    def f(dt): return dt.strftime('%Y-%m-%d %H:%M:%S')

    def cfg(modo_2x1, modo_caba, evento_activo):
        base = {
            'hot_event_activo': 'auto',
            'hot_event_fecha_inicio': f(ahora - timedelta(days=1)),
            'hot_event_fecha_fin': f(ahora + timedelta(days=(3 if evento_activo else 0)
                                                       - (0 if evento_activo else 2))),
            'evento_fecha_corte': f(ahora + timedelta(days=1)),
            'evento_titulo': 'CYBERSALE', 'evento_cupon': 'CYBERSALE',
            'evento_cupon_pct': '5', 'evento_descuento_max': '10',
            'promo_2x1_almohadas': modo_2x1,
            'evento_envio_gratis_caba': modo_caba,
        }
        if not evento_activo:                 # evento ya terminado
            base['hot_event_fecha_inicio'] = f(ahora - timedelta(days=9))
            base['hot_event_fecha_fin'] = f(ahora - timedelta(days=2))
        return base

    app = Flask(__name__, root_path='/home/cannon/app',
                static_folder='/home/cannon/app/static',
                template_folder='/home/cannon/app/templates')
    app.secret_key = 'modos'
    app.register_blueprint(tb.tienda_bp, url_prefix='/tienda')

    CP_CABA = '1414'

    def estado(modo_2x1, modo_caba, evento_activo):
        """Devuelve (2x1_activo, caba_gratis) con esa configuracion."""
        c = cfg(modo_2x1, modo_caba, evento_activo)
        original = tb.get_db
        tb.get_db = lambda: DbFalsa(c)
        try:
            # Request context nuevo cada vez: el cache de modos vive en flask.g
            with app.test_request_context('/tienda/'):
                return tb.promo_2x1_activa(), tb.envio_gratis_caba(CP_CABA)
        finally:
            tb.get_db = original

    print('EVENTO ACTIVO')
    for modo, esperado in (('0', False), ('1', True), ('auto', True)):
        dosx1, caba = estado(modo, modo, True)
        chequear(dosx1 is esperado, f'2x1 en modo {modo!r} -> {esperado}', str(dosx1))
        chequear(caba is esperado, f'envio CABA en modo {modo!r} -> {esperado}', str(caba))

    print('EVENTO TERMINADO')
    # Con el evento apagado, 'auto' tiene que apagarse solo. '1' queda prendido
    # en el 2x1 (es su proposito: poder correrlo fuera de un evento) pero el
    # envio CABA no, porque exige evento activo por diseño.
    for modo, esp_2x1, esp_caba in (('0', False, False),
                                    ('1', True, False),
                                    ('auto', False, False)):
        dosx1, caba = estado(modo, modo, False)
        chequear(dosx1 is esp_2x1, f'2x1 en modo {modo!r} -> {esp_2x1}', str(dosx1))
        chequear(caba is esp_caba, f'envio CABA en modo {modo!r} -> {esp_caba}', str(caba))

    print('CP QUE NO ES DE CABA')
    c = cfg('auto', 'auto', True)
    original = tb.get_db
    tb.get_db = lambda: DbFalsa(c)
    try:
        with app.test_request_context('/tienda/'):
            chequear(tb.envio_gratis_caba('7600') is False,
                     'Mar del Plata no recibe envio bonificado')
    finally:
        tb.get_db = original

    print()
    print('RESULTADO:', 'los tres estados funcionan' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
