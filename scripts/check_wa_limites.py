#!/usr/bin/env python3
"""Verifica los limites anti-bucle del bot de WhatsApp.

Muestra los topes vigentes, el consumo actual de cada numero y simula si un
telefono quedaria bloqueado. NO manda mensajes ni llama a la API de Claude.

Uso:  venv/bin/python3 scripts/check_wa_limites.py [telefono]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from whatsapp_bp import _wa_limites, _wa_excedido, _q  # noqa: E402


def main():
    lim = _wa_limites()
    print('TOPES VIGENTES (configuracion)')
    print('-' * 56)
    for k, v in lim.items():
        print(f'  {k:<22} {v}')

    tot = _q("SELECT COUNT(*) n FROM wa_mensajes WHERE rol='user' "
             "AND fecha >= NOW() - INTERVAL 1 DAY")
    usado = tot[0]['n'] if tot else 0
    print(f'\nGLOBAL ultimas 24h: {usado} / {lim["wa_max_global_dia"]} '
          f'({usado / lim["wa_max_global_dia"] * 100:.0f}% del tope)')

    print('\nPOR TELEFONO (ultimas 24h)')
    print('-' * 70)
    print(f'  {"telefono":<16} {"1h":>5} {"24h":>5}  estado')
    filas = _q("""
        SELECT phone,
               SUM(fecha >= NOW() - INTERVAL 1 HOUR) AS hora,
               COUNT(*) AS dia
        FROM wa_mensajes
        WHERE rol='user' AND fecha >= NOW() - INTERVAL 1 DAY
        GROUP BY phone ORDER BY dia DESC
    """) or []
    if not filas:
        print('  (sin mensajes en las ultimas 24h)')
    for f in filas:
        bloq, motivo = _wa_excedido(f['phone'])
        estado = f'BLOQUEADO — {motivo}' if bloq else 'ok'
        print(f'  {f["phone"]:<16} {f["hora"]:>5} {f["dia"]:>5}  {estado}')

    if len(sys.argv) > 1:
        tel = sys.argv[1]
        bloq, motivo = _wa_excedido(tel)
        print(f'\nCHEQUEO PUNTUAL {tel}: '
              f'{"BLOQUEADO — " + motivo if bloq else "pasa, se le responderia"}')

    print('\nBloqueos registrados (ultimos 5):')
    ev = _q("""SELECT timestamp, detalle FROM sistema_logs
               WHERE modulo='whatsapp' AND accion='limite_alcanzado'
               ORDER BY id DESC LIMIT 5""") or []
    if not ev:
        print('  ninguno')
    for e in ev:
        print(f'  {e["timestamp"]}  {e["detalle"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
