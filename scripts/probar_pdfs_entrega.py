#!/usr/bin/env python3
"""Genera la orden de retiro y el remito de una venta y verifica su contenido.

Son los dos documentos que se presentan como prueba ante un contracargo, asi
que lo que importa es que tengan lo que ClearSale exige: quien recibe
identificado, fecha de RECEPCION (no de emision) y el domicilio correcto.

No escribe en la base. Guarda los PDF para poder abrirlos.
"""
import os
import re
import sys

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')
os.environ['CANNON_SIN_SCHEDULER'] = '1'   # no arrancar los jobs al importar app

fallos = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


def texto_pdf(path):
    from pypdf import PdfReader
    return '\n'.join((p.extract_text() or '') for p in PdfReader(path).pages)


def main():
    venta_id = int(sys.argv[1]) if len(sys.argv) > 1 else 25590
    salida = '/tmp/claude-0'

    import app as A

    with A.app.test_request_context(f'/ventas/activas/{venta_id}/orden-retiro'):
        # Saltear el login_required llamando a la funcion sin decorar
        fn_orden = A.orden_retiro_pdf.__wrapped__ if hasattr(A.orden_retiro_pdf, '__wrapped__') \
            else A.orden_retiro_pdf
        fn_remito = A.remito_conforme_pdf.__wrapped__ if hasattr(A.remito_conforme_pdf, '__wrapped__') \
            else A.remito_conforme_pdf
        for nombre, fn in (('orden_retiro', fn_orden), ('remito', fn_remito)):
            try:
                r = fn(venta_id)
                data = r.get_data() if hasattr(r, 'get_data') else r
                p = f'{salida}/{nombre}_{venta_id}.pdf'
                open(p, 'wb').write(data)
                t = texto_pdf(p)
                print(f'--- {nombre} ({len(data)//1024} KB) -> {p}')
                globals()[f'txt_{nombre}'] = t
            except Exception as e:
                print(f'--- {nombre}: ERROR {type(e).__name__}: {e}')
                globals()[f'txt_{nombre}'] = ''

    print()
    print('ORDEN DE RETIRO')
    t = globals().get('txt_orden_retiro', '')
    chequear(bool(t), 'se genero')
    if t:
        chequear('Emilio Lamarca 1870' in t, 'direccion de retiro correcta')
        chequear('Pueden retirar' in t, 'lista de autorizados presente')
        chequear('Comprador' in t, 'figura el comprador')

    print()
    print('REMITO')
    t = globals().get('txt_remito', '')
    chequear(bool(t), 'se genero')
    if t:
        chequear('Fecha y hora de recepci' in t, 'campo de FECHA DE RECEPCION (no de emision)')
        chequear('DNI de quien recibe' in t, 'pide DNI de quien recibe')
        chequear('Aclaraci' in t, 'pide aclaracion de la firma')
        chequear('completar al momento de la entrega' in t.lower(),
                 'dice quien completa que')
        chequear('QUIEN RECIBE' in t, 'identifica lo que completa el cliente')
        chequear('MERCADOMUEBLES' in t, 'identifica lo que completa la empresa')
        chequear('Fecha emisi' in t, 'la fecha de emision esta rotulada como tal')

    print()
    print('RESULTADO:', 'los documentos cumplen' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
