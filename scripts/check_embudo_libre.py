#!/usr/bin/env python3
"""Espera a que nadie esté en el embudo de compra de la tienda (SOLO LECTURA).

Mira el access log de nginx y sale cuando pasan N minutos sin hits a
carrito / datos-envio / checkout / pago. Sirve para elegir el momento de
reiniciar el servicio sin cortarle una compra a nadie.

Uso: venv/bin/python3 scripts/check_embudo_libre.py [--quieto 10] [--max 60]
  --quieto  minutos sin actividad en el embudo para considerarlo libre (def 10)
  --max     minutos máximos de espera antes de rendirse (def 60)
Sale con 0 si quedó libre, 1 si se agotó la espera.
"""
import re
import sys
import time
from datetime import datetime, timezone, timedelta

LOG = '/var/log/nginx/access.log'
EMBUDO = re.compile(r'"(?:GET|POST) /tienda/(?:carrito|datos-envio|checkout|pago|verificar-pago|procesar)')
FECHA = re.compile(r'\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}) ([+-]\d{4})\]')


def ultimo_hit():
    """Fecha (UTC) del último hit al embudo en las últimas ~5000 líneas."""
    try:
        with open(LOG, 'rb') as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 1_500_000))
            lineas = f.read().decode('utf-8', 'replace').splitlines()
    except OSError as e:
        print(f'no pude leer {LOG}: {e}', flush=True)
        return None
    for ln in reversed(lineas):
        if EMBUDO.search(ln):
            m = FECHA.search(ln)
            if m:
                return datetime.strptime(f'{m.group(1)} {m.group(2)}', '%d/%b/%Y:%H:%M:%S %z')
    return None


def arg(nombre, defecto):
    return int(sys.argv[sys.argv.index(nombre) + 1]) if nombre in sys.argv else defecto


def main():
    quieto = timedelta(minutes=arg('--quieto', 10))
    limite = time.time() + arg('--max', 60) * 60
    while True:
        ahora = datetime.now(timezone.utc)
        u = ultimo_hit()
        if u is None or ahora - u >= quieto:
            hace = 'sin hits recientes' if u is None else f'último hit hace {int((ahora - u).total_seconds() // 60)} min'
            print(f'LIBRE — {hace}', flush=True)
            return 0
        if time.time() > limite:
            print(f'OCUPADO — se agotó la espera, último hit {u:%H:%M} UTC', flush=True)
            return 1
        time.sleep(30)


if __name__ == '__main__':
    sys.exit(main())
