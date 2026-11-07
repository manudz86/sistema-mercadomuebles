#!/usr/bin/env python3
"""Prueba el papel azul (/ventas/<id>/papel-azul) y el botón 🖨️ en las páginas de ventas.
Solo lectura: genera los PDF en memoria (opcionalmente los guarda en un directorio)
y renderiza las plantillas. No escribe en la base.

Uso: venv/bin/python scripts/probar_papel_azul.py [dir_salida_pdfs]
"""
import io
import os
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
from jinja2 import Environment, FileSystemLoader  # noqa: E402
from pypdf import PdfReader  # noqa: E402
import app as A  # noqa: E402

salida = sys.argv[1] if len(sys.argv) > 1 else None
fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    fallas += 0 if cond else 1


env = Environment(loader=FileSystemLoader('templates'))
for t in ('ventas_activas.html', 'proceso_envio.html', 'ventas_historicas.html'):
    env.parse(open('templates/' + t, encoding='utf-8').read())
    check(True, f'{t} parsea')

vista = A.papel_azul_pdf
while hasattr(vista, '__wrapped__'):
    vista = vista.__wrapped__


def texto_pdf(venta_id):
    with A.app.test_request_context(f'/ventas/{venta_id}/papel-azul'):
        resp = vista(venta_id)
    data = resp.get_data()
    if salida:
        open(os.path.join(salida, f'papel_azul_{venta_id}.pdf'), 'wb').write(data)
    return PdfReader(io.BytesIO(data)).pages[0].extract_text()


casos = [
    ("canal='tienda_web' AND metodo_envio='Delega'", 'SIN_TOTAL', True),
    ("metodo_envio='Flex'", 'FLEX', False),
    ("metodo_envio='Flete Propio'", None, True),
]
for cond, abajo, con_tel in casos:
    v = A.query_one(f"SELECT id, numero_venta, nombre_cliente, telefono_cliente, direccion_entrega FROM ventas WHERE {cond} AND direccion_entrega <> '' ORDER BY id DESC LIMIT 1")
    if not v:
        print(f'      (sin ventas para {cond})')
        continue
    txt = texto_pdf(v['id'])
    lineas = [x.strip() for x in txt.splitlines() if x.strip()]
    ok = (v['nombre_cliente'] or '-') in txt
    if abajo == 'SIN_TOTAL':
        # Delega: fecha, nombre, teléfono, productos y dirección; sin total ni leyenda
        ok = ok and 'Total' not in txt and lineas[-1] not in ('FLEX', 'DELEGA', 'TURBO') and lineas[0].count('-') == 2
    elif abajo:
        ok = ok and lineas[-1] == abajo
    else:
        ok = ok and lineas[-1] not in ('FLEX', 'DELEGA', 'TURBO')
    if abajo in ('DELEGA', 'FLEX'):
        ok = ok and 'Total: $0.-' in txt
    tel = (v['telefono_cliente'] or '').strip()
    if tel:
        ok = ok and ((tel in txt) == con_tel)
    check(ok, f'{cond}: venta {v["numero_venta"]} → pie {lineas[-1]!r}, teléfono {"sí" if tel and tel in txt else "no"}')
    print('      ' + ' | '.join(lineas))

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
