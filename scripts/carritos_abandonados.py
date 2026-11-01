#!/usr/bin/env python3
"""Listado de carritos abandonados, para una campaña de recupero.

Fuente: pedidos_pendientes, que se escribe cuando alguien llega al checkout
con sus datos ya cargados. O sea que son personas que dejaron el mail y el
telefono y se cayeron en el ultimo paso, no visitantes anonimos.

Se considera abandonado el mail que NUNCA aparece en ventas. Si compro
despues, aunque haya abandonado antes, queda afuera.

Sale ordenado por temperatura:
  CALIENTE  intento pagar y la tarjeta rechazo (llego hasta el final)
  TIBIO     llego al checkout en los ultimos 30 dias
  FRIO      mas viejo que eso

Solo lectura. Escribe un CSV.

Uso:
    venv/bin/python3 scripts/carritos_abandonados.py
    venv/bin/python3 scripts/carritos_abandonados.py --dias 60 --salida /tmp/x.csv
"""
import argparse
import csv
import json
import re
import os
import sys
from collections import defaultdict
from datetime import datetime

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')


def conectar():
    return pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER'), password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME'), cursorclass=pymysql.cursors.DictCursor)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dias', type=int, default=0,
                    help='Solo carritos de los ultimos N dias (0 = todos)')
    ap.add_argument('--salida', default='/home/cannon/app/carritos_abandonados.csv')
    a = ap.parse_args()

    cn = conectar(); cur = cn.cursor()

    # Mails que SI compraron alguna vez
    cur.execute("SELECT DISTINCT LOWER(TRIM(email_cliente)) m FROM ventas "
                "WHERE email_cliente IS NOT NULL AND email_cliente <> ''")
    compraron = {r['m'] for r in cur.fetchall() if r['m']}

    # Refs que llegaron a un intento de pago rechazado: los mas calientes
    cur.execute("""SELECT DISTINCT SUBSTRING(pi.site_transaction_id, 4) ref
                   FROM payway_intentos pi
                   WHERE pi.site_transaction_id LIKE 'PW-%' AND pi.status_es = 'Rechazada'""")
    con_rechazo = {r['ref'] for r in cur.fetchall()}

    # Señal de riesgo: una MISMA tarjeta usada por mails distintos, o un mail
    # probando varias tarjetas. Es la firma del card testing, y a esa gente no
    # hay que mandarle un cupon.
    #
    # OJO: solo sirve desde el 24/10/2026, que es cuando se empezo a guardar
    # last4. Antes solo hay BIN, y agrupar por BIN marca como "tarjeta
    # compartida" a cualquiera que tenga cuenta en el mismo banco.
    cur.execute("""SELECT pp.cliente_json, pi.bin, pi.last4
                   FROM pedidos_pendientes pp
                   JOIN payway_intentos pi ON pi.site_transaction_id = CONCAT('PW-', pp.ref)
                   WHERE pi.last4 IS NOT NULL AND pi.last4 <> ''""")
    _mail_tarj, _tarj_mail = defaultdict(set), defaultdict(set)
    for r in cur.fetchall():
        try:
            m = (json.loads(r['cliente_json']).get('email') or '').strip().lower()
        except Exception:
            continue
        if not m:
            continue
        t = f"{r['bin']}-{r['last4']}"
        _mail_tarj[m].add(t)
        _tarj_mail[t].add(m)
    riesgosos = {m for m, ts in _mail_tarj.items() if len(ts) >= 2}
    for t, ms in _tarj_mail.items():
        if len(ms) >= 2:
            riesgosos |= ms

    # DNIs bloqueados por fraude
    try:
        cur.execute("SELECT valor FROM fraude_blocklist "
                    "WHERE activo=1 AND lista='block' AND tipo='dni'")
        dnis_bloqueados = {str(r['valor']).strip() for r in cur.fetchall()}
    except Exception:
        dnis_bloqueados = set()

    filtro = ''
    if a.dias:
        filtro = f'WHERE pp.fecha_creacion >= NOW() - INTERVAL {int(a.dias)} DAY'
    cur.execute(f"""SELECT pp.ref, pp.carrito_json, pp.cliente_json, pp.fecha_creacion
                    FROM pedidos_pendientes pp {filtro}
                    ORDER BY pp.fecha_creacion""")
    filas = cur.fetchall()
    cur.close(); cn.close()

    # Agrupar por mail: nos interesa la persona, no cada intento suelto
    por_mail = defaultdict(lambda: {'carritos': 0, 'rechazo': False, 'ult': None,
                                    'cli': None, 'carrito': None, 'valor': 0.0})
    for f in filas:
        try:
            cli = json.loads(f['cliente_json'])
            carrito = json.loads(f['carrito_json'])
        except Exception:
            continue
        mail = (cli.get('email') or '').strip().lower()
        if not mail or '@' not in mail:
            continue
        d = por_mail[mail]
        d['carritos'] += 1
        if f['ref'] in con_rechazo:
            d['rechazo'] = True
        # Nos quedamos con el ultimo carrito: es el que refleja lo que querian
        if d['ult'] is None or f['fecha_creacion'] >= d['ult']:
            d['ult'] = f['fecha_creacion']
            d['cli'] = cli
            d['carrito'] = carrito
            d['valor'] = sum(float(i.get('precio') or 0) * int(i.get('cantidad') or 0)
                             for i in carrito)

    hoy = datetime.now()
    registros = []
    for mail, d in por_mail.items():
        if mail in compraron:
            continue                     # compro alguna vez: no es abandono
        dias = (hoy - d['ult']).days if d['ult'] else 999
        if d['rechazo']:
            temp = 'CALIENTE'
        elif dias <= 30:
            temp = 'TIBIO'
        else:
            temp = 'FRIO'
        cli = d['cli'] or {}
        dni = re.sub(r'\D', '', str(cli.get('dni') or ''))
        riesgo = 'SI' if (mail in riesgosos or (dni and dni in dnis_bloqueados)) else ''
        registros.append({
            'riesgo': riesgo,
            'temperatura': temp,
            'email': mail,
            'nombre': (cli.get('nombre') or '').strip(),
            'telefono': (cli.get('telefono') or '').strip(),
            'provincia': (cli.get('provincia') or '').strip(),
            'ultimo_carrito': d['ult'].strftime('%Y-%m-%d %H:%M') if d['ult'] else '',
            'dias_desde': dias,
            'veces_que_abandono': d['carritos'],
            'pago_rechazado': 'si' if d['rechazo'] else 'no',
            'valor_carrito': round(d['valor']),
            'productos': ' + '.join(
                f"{i.get('cantidad')}x {i.get('nombre') or i.get('sku')}"
                for i in (d['carrito'] or [])),
        })

    orden = {'CALIENTE': 0, 'TIBIO': 1, 'FRIO': 2}
    registros.sort(key=lambda r: (orden[r['temperatura']], r['dias_desde']))

    with open(a.salida, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=list(registros[0].keys()) if registros
                           else ['email'])
        w.writeheader()
        w.writerows(registros)

    # Resumen
    tot = len(registros)
    print(f'carritos analizados ....... {len(filas)}')
    print(f'personas unicas con mail .. {len(por_mail)}')
    print(f'  ya compraron (excluidas)  {len(por_mail) - tot}')
    print(f'  ABANDONADAS ............. {tot}')
    print()
    riesgo_n = len([r for r in registros if r['riesgo']])
    if riesgo_n:
        print(f'  marcadas RIESGO (no mandarles cupon) ... {riesgo_n}')
        print()
    for t in ('CALIENTE', 'TIBIO', 'FRIO'):
        g = [r for r in registros if r['temperatura'] == t and not r['riesgo']]
        if not g:
            continue
        valor = sum(r['valor_carrito'] for r in g)
        print(f'  {t:<9} {len(g):>4} personas   ${valor:,.0f} en carritos'
              .replace(',', '.'))
    print()
    print(f'valor total en juego ...... ${sum(r["valor_carrito"] for r in registros):,.0f}'
          .replace(',', '.'))
    print(f'CSV ....................... {a.salida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
