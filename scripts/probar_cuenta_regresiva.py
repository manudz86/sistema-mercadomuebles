#!/usr/bin/env python3
"""Verifica las dos etapas del evento: a qué apunta la cuenta regresiva y qué
banner se sirve en cada una.

No se puede congelar el reloj (get_hot_event importa datetime adentro), así que
se hace lo inverso: se falsea la tabla configuracion con fechas relativas al
ahora real y se comprueba qué elige la función. No toca la base.

Lo que tiene que cumplirse:
  - Etapa 1 (antes del corte): cuenta hasta el CORTE y banner sin sufijo.
  - Etapa 2 (pasado el corte): cuenta hasta el FIN y banner _ext.
  - El contador llega a cero en el mismo instante en que cambia el banner.
  - Antes del inicio y después del fin, el evento está inactivo.
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
    def __init__(self, filas): self._filas = filas
    def execute(self, *a, **k): pass
    def fetchall(self): return self._filas
    def close(self): pass


class DbFalsa:
    def __init__(self, filas): self._filas = filas
    def cursor(self): return CursorFalso(self._filas)
    def close(self): pass


def con_config(tb, cfg):
    """Hace que get_hot_event lea esta configuración y devuelve su resultado."""
    filas = [{'clave': k, 'valor': v} for k, v in cfg.items()]
    original = tb.get_db
    tb.get_db = lambda: DbFalsa(filas)
    try:
        return tb.get_hot_event()
    finally:
        tb.get_db = original


def f(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def main():
    import tienda_bp as tb

    # Hora de pared ARGENTINA, no la del servidor: get_hot_event interpreta las
    # fechas de configuracion en America/Argentina/Buenos_Aires, y este server
    # corre en UTC. Usando datetime.now() pelado, las fechas simuladas quedaban
    # corridas 3 horas y los casos de 1 segundo daban al reves.
    try:
        from zoneinfo import ZoneInfo
        ahora = datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).replace(tzinfo=None)
    except Exception:
        ahora = datetime.now()

    BASE = {
        'hot_event_activo': 'auto',
        'evento_titulo': 'CYBERSALE',
        'evento_cupon': 'CYBERSALE',
        'evento_cupon_pct': '5',
        'evento_descuento_max': '10',
    }

    # ── Etapa 1: el corte está en el futuro ───────────────────────────────
    print('ETAPA 1 (dentro de los primeros dias, corte aun por venir)')
    corte1 = ahora + timedelta(days=2)
    fin1   = ahora + timedelta(days=6)
    he = con_config(tb, dict(BASE,
                             hot_event_fecha_inicio=f(ahora - timedelta(days=1)),
                             hot_event_fecha_fin=f(fin1),
                             evento_fecha_corte=f(corte1)))
    chequear(he['activo'], 'el evento esta activo')
    chequear(he['extendido'] is False, 'NO extendido')
    chequear(he['banner_desktop'].endswith('cybersale_desktop.jpg'),
             'banner desktop sin sufijo', he['banner_desktop'])
    chequear(he['banner_mobile'].endswith('cybersale_mobile.jpg'),
             'banner mobile sin sufijo')
    chequear(he['fecha_fin_iso'][:19] == corte1.strftime('%Y-%m-%dT%H:%M:%S'),
             'la cuenta regresiva apunta al CORTE, no al fin',
             he['fecha_fin_iso'][:19])

    # ── Etapa 2: el corte ya pasó ─────────────────────────────────────────
    print('ETAPA 2 (pasado el corte)')
    corte2 = ahora - timedelta(days=2)
    fin2   = ahora + timedelta(days=2)
    he = con_config(tb, dict(BASE,
                             hot_event_fecha_inicio=f(ahora - timedelta(days=5)),
                             hot_event_fecha_fin=f(fin2),
                             evento_fecha_corte=f(corte2)))
    chequear(he['activo'], 'el evento esta activo')
    chequear(he['extendido'] is True, 'extendido')
    chequear(he['banner_desktop'].endswith('cybersale_desktop_ext.jpg'),
             'banner desktop _ext', he['banner_desktop'])
    chequear(he['banner_mobile'].endswith('cybersale_mobile_ext.jpg'),
             'banner mobile _ext')
    chequear(he['fecha_fin_iso'][:19] == fin2.strftime('%Y-%m-%dT%H:%M:%S'),
             'la cuenta regresiva apunta al FIN', he['fecha_fin_iso'][:19])

    # ── El instante del cambio es el mismo para contador y banner ─────────
    print('EL CAMBIO ES SIMULTANEO (corte a 1 segundo de distancia)')
    casi = ahora + timedelta(seconds=1)
    he_a = con_config(tb, dict(BASE,
                               hot_event_fecha_inicio=f(ahora - timedelta(days=1)),
                               hot_event_fecha_fin=f(ahora + timedelta(days=4)),
                               evento_fecha_corte=f(casi)))
    recien = ahora - timedelta(seconds=1)
    he_b = con_config(tb, dict(BASE,
                               hot_event_fecha_inicio=f(ahora - timedelta(days=1)),
                               hot_event_fecha_fin=f(ahora + timedelta(days=4)),
                               evento_fecha_corte=f(recien)))
    chequear(he_a['extendido'] is False and he_b['extendido'] is True,
             'un segundo antes y despues del corte cambia de etapa')
    chequear(he_a['fecha_fin_iso'][:19] == casi.strftime('%Y-%m-%dT%H:%M:%S'),
             'justo antes del corte el contador apunta al corte (llega a 0 ahi)')
    chequear(he_a['banner_desktop'] != he_b['banner_desktop'],
             'el banner cambia en ese mismo instante')

    # ── Fuera de rango ────────────────────────────────────────────────────
    print('FUERA DE RANGO')
    he = con_config(tb, dict(BASE,
                             hot_event_fecha_inicio=f(ahora + timedelta(days=2)),
                             hot_event_fecha_fin=f(ahora + timedelta(days=9)),
                             evento_fecha_corte=f(ahora + timedelta(days=5))))
    chequear(not he['activo'], 'antes del inicio: inactivo')
    chequear(he['fecha_fin_iso'] == '', 'sin cuenta regresiva')
    he = con_config(tb, dict(BASE,
                             hot_event_fecha_inicio=f(ahora - timedelta(days=9)),
                             hot_event_fecha_fin=f(ahora - timedelta(days=1)),
                             evento_fecha_corte=f(ahora - timedelta(days=5))))
    chequear(not he['activo'], 'despues del fin: inactivo')

    # ── Sin fecha de corte: se comporta como antes ────────────────────────
    print('SIN FECHA DE CORTE (compatibilidad)')
    fin3 = ahora + timedelta(days=3)
    he = con_config(tb, dict(BASE,
                             hot_event_fecha_inicio=f(ahora - timedelta(days=1)),
                             hot_event_fecha_fin=f(fin3)))
    chequear(he['activo'] and he['extendido'] is False, 'activo y no extendido')
    chequear(he['fecha_fin_iso'][:19] == fin3.strftime('%Y-%m-%dT%H:%M:%S'),
             'cuenta hasta el fin, como antes')

    print()
    print('RESULTADO:', 'las dos etapas funcionan' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
