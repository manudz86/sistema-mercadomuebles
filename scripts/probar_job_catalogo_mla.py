#!/usr/bin/env python3
"""Verifica que el refresco diario del indice corra UNA sola vez por dia.

El scheduler de APScheduler arranca en los 5 workers de Gunicorn, asi que sin
candado el job saldria 5 veces y serian 5 recorridas de ~76 llamadas a ML. Esta
prueba lanza 5 hilos a la vez contra job_catalogo_mla con el refresco real
reemplazado por un contador: tiene que ejecutarse una sola vez, y ninguna mas en
el resto del dia.

No le pega a ML. Deja configuracion['catalogo_mla_ultimo_refresco'] como estaba.
"""
import os
import sys
import threading

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
os.environ['CANNON_SIN_SCHEDULER'] = '1'

CLAVE = 'catalogo_mla_ultimo_refresco'
fallos = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


def main():
    import app as A

    previo = A.query_one("SELECT valor FROM configuracion WHERE clave = %s", (CLAVE,))
    previo = previo['valor'] if previo else None
    print(f'valor previo de la clave: {previo!r}')

    corridas = []
    lock = threading.Lock()

    def falso_refresco(log=print):
        with lock:
            corridas.append(1)
        return 0, 0, 0, 0

    real = A.refrescar_catalogo_mla
    A.refrescar_catalogo_mla = falso_refresco
    try:
        # Simular que el ultimo refresco fue ayer
        A.execute_db("INSERT INTO configuracion (clave, valor) VALUES (%s, '1999-01-01') "
                     "ON DUPLICATE KEY UPDATE valor = '1999-01-01'", (CLAVE,))

        print('5 workers arrancan el job a la vez')
        hilos = [threading.Thread(target=A.job_catalogo_mla) for _ in range(5)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=30)
        chequear(len(corridas) == 1, 'el refresco corrio exactamente una vez',
                 f'{len(corridas)} veces')

        print('mas tarde, el mismo dia')
        corridas.clear()
        A.job_catalogo_mla()
        chequear(not corridas, 'no vuelve a correr', f'{len(corridas)} veces')

        from datetime import datetime
        guardado = A.query_one("SELECT valor FROM configuracion WHERE clave = %s", (CLAVE,))
        chequear(guardado and guardado['valor'] == datetime.now().strftime('%Y-%m-%d'),
                 'la clave queda con la fecha de hoy',
                 guardado['valor'] if guardado else 'sin fila')

        print('al dia siguiente vuelve a correr')
        A.execute_db("UPDATE configuracion SET valor = '1999-01-02' WHERE clave = %s", (CLAVE,))
        corridas.clear()
        A.job_catalogo_mla()
        chequear(len(corridas) == 1, 'corre de nuevo', f'{len(corridas)} veces')
    finally:
        A.refrescar_catalogo_mla = real
        if previo is None:
            A.execute_db("DELETE FROM configuracion WHERE clave = %s", (CLAVE,))
            print('clave borrada (no existia antes)')
        else:
            A.execute_db("UPDATE configuracion SET valor = %s WHERE clave = %s", (previo, CLAVE))
            print(f'clave restaurada a {previo!r}')

    print()
    print('RESULTADO:', 'el candado funciona' if not fallos else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
