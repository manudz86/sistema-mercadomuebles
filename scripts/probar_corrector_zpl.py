#!/usr/bin/env python3
"""Pruebas del Corrector de etiquetas ZPL (/herramientas/corrector-zpl).

Corre el JavaScript REAL (static/js/zpl_corrector.js) en Chromium headless (Playwright)
y compara byte a byte contra una referencia independiente en Python. Además renderiza la
página real de Flask y prueba carga (input y drag & drop), procesamiento y descarga.
No escribe en la base ni sube nada a ningún lado (bloquea toda request externa).

Uso: venv/bin/python scripts/probar_corrector_zpl.py
"""
import os
import re
import sys

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from playwright.sync_api import sync_playwright  # noqa: E402

JS = open('static/js/zpl_corrector.js', 'rb').read()
fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    fallas += 0 if cond else 1


def referencia(b):
    """Implementación independiente: reemplazo de comando completo (no seguido de dígito)."""
    return re.sub(rb'\^LH0,(90|410)(?!\d)', lambda m: b'^LH0,0' if m.group(1) == b'90' else b'^LH0,320', b)


GFA = b'^FO40,40^GFA,512,512,8,' + (b'00FF0A0B90410C' * 36)[:1024] + b'^FS'


def etiqueta(n, nl=b'\n', lh90=True, lh410=True, nombre='Geraldine Ñandú Peña'.encode('utf-8')):
    partes = [b'^XA', b'^MCY', b'^CI28']
    if lh90:
        partes.append(b'^LH0,90')
    partes += [GFA,
               b'^FO520,60^BQN,2,5^FDLA,{"id":"4844525%04d","t":"lm"}^FS' % n,
               b'^FO80,300^BY3^BCN,120,N,N^FD4844525%04d^FS' % n,
               b'^FO30,450^A0N,32,32^FDEtiqueta n%d^FS' % n]
    if lh410:
        partes.append(b'^LH0,410')
    partes += [b'^FO30,20^A0N,30,30^FD' + nombre + b'^FS',
               b'^FO30,60^A0N,26,26^FDCalle Coronel Intendente Avalos 2181 - Munro (1605)^FS',
               b'^PQ1,0,1,Y', b'^XZ']
    return nl.join(partes) + nl


with sync_playwright() as pw:
    nav = pw.chromium.launch(args=['--no-sandbox'])
    pag = nav.new_page()
    pag.route('**/*', lambda r: r.abort())  # nada sale a la red
    pag.set_content('<html><body></body></html>')
    pag.add_script_tag(content=JS.decode('utf-8'))

    def corregir(b):
        r = pag.evaluate('''(a) => { const r = ZPLCorrector.corregir(new Uint8Array(a));
            return Object.assign({}, r, {salida: Array.from(r.salida)}); }''', list(b))
        r['salida'] = bytes(r['salida'])
        return r

    # 1. Una etiqueta
    e1 = etiqueta(1)
    r = corregir(e1)
    check(r['ok'] and r['etiquetas'] == 1 and r['reemplazos'] == {'lh90': 1, 'lh410': 1} and r['total'] == 2,
          '1) una etiqueta: 1 × ^LH0,90 y 1 × ^LH0,410 reemplazados')
    check(b'^LH0,0\n' in r['salida'] and b'^LH0,320\n' in r['salida'] and b'^LH0,90' not in r['salida']
          and b'^LH0,410' not in r['salida'], '   el resultado tiene ^LH0,0 y ^LH0,320 y ya no los originales')
    check(r['salida'] == referencia(e1), '   idéntico byte a byte a la referencia independiente')

    # 2. Diez etiquetas
    e10 = b''.join(etiqueta(i) for i in range(1, 11))
    r10 = corregir(e10)
    check(r10['etiquetas'] == 10 and r10['reemplazos'] == {'lh90': 10, 'lh410': 10} and r10['total'] == 20
          and not r10['incompletas'], '2) 10 etiquetas: 10 + 10 reemplazos, ninguna incompleta')
    check(r10['salida'] == referencia(e10), '   idéntico a la referencia')
    orden = re.findall(rb'Etiqueta n(\d+)', r10['salida'])
    check(orden == [str(i).encode() for i in range(1, 11)], '   orden de las etiquetas conservado (1..10)')

    # 3. Comandos parecidos que NO se tocan
    parecidos = (b'^XA\n^LH0,900\n^LH0,4100\n^LH0,9\n^LH0,41\n^LH10,90\n^LH0,910\n^LH0,4105\n^FO0,90^FS\n'
                 b'^LH0,90\n^LH0,410\n^XZ\n^XA^LH0,90^LH0,410^XZ^XA^LH0,90')
    rp = corregir(parecidos)
    esperado = parecidos.replace(b'^LH0,90\n^LH0,410\n^XZ', b'^LH0,0\n^LH0,320\n^XZ') \
                        .replace(b'^XA^LH0,90^LH0,410^XZ', b'^XA^LH0,0^LH0,320^XZ')
    esperado = esperado[:-len(b'^LH0,90')] + b'^LH0,0'
    check(rp['salida'] == esperado and rp['reemplazos'] == {'lh90': 3, 'lh410': 2},
          '3) ^LH0,900 ^LH0,4100 ^LH0,9 ^LH0,41 ^LH10,90 ^LH0,910 ^LH0,4105 ^FO0,90 intactos; '
          'comandos pegados y al final del archivo sí se corrigen')

    # 4. Idempotencia
    r2 = corregir(r10['salida'])
    check(r2['salida'] == r10['salida'] and r2['total'] == 0 and r2['yaCorregidas'] == 10 and not r2['incompletas'],
          '4) segunda pasada: 0 cambios, mismo archivo, 10 etiquetas "ya corregidas"')

    # 5. Datos, QR, códigos de barras y ^GFA intactos
    def bloques(b):
        return re.findall(rb'\^GFA[^\^]*|\^BQN[^\^]*\^FD[^\^]*|\^BCN[^\^]*\^FD[^\^]*|\^FD[^\^]*|\^FO\d+,\d+', b)
    check(bloques(r10['salida']) == bloques(e10) and r10['salida'].count(GFA) == 10,
          '5) ^GFA, QR (^BQN), código de barras (^BCN), ^FD (textos/datos) y ^FO idénticos')

    # 7. Sin modificaciones ajenas: deshaciendo los 2 reemplazos vuelve exactamente el original
    deshecho = r10['salida'].replace(b'^LH0,0\n', b'^LH0,90\n').replace(b'^LH0,320\n', b'^LH0,410\n')
    check(deshecho == e10 and len(e10) - len(r10['salida']) == 10 * 1 + 10 * 0,
          '7) resultado = original salvo los bytes de los reemplazos (diferencia de tamaño exacta: 10 bytes)')

    # Validaciones
    for nombre, b, frag in [('vacío', b'', 'vacío'), ('solo espacios', b' \r\n\t\n', 'espacios'),
                            ('sin ZPL', b'hola mundo\n^LH0,90\n', 'ZPL'),
                            ('UTF-16 con BOM', b'\xff\xfe' + '^XA^LH0,90^XZ'.encode('utf-16-le'), 'UTF-16'),
                            ('UTF-16 sin BOM', '^XA^LH0,90^LH0,410^XZ'.encode('utf-16-le'), 'UTF-16')]:
        rv = corregir(b)
        check(not rv['ok'] and frag in (rv['error'] or ''), f'V) {nombre}: error claro, no se ofrece descarga')

    falta = etiqueta(1) + etiqueta(2, lh410=False) + etiqueta(3, lh90=False, lh410=False)
    rf = corregir(falta)
    check(rf['ok'] and rf['incompletas'] == [2, 3] and rf['reemplazos'] == {'lh90': 2, 'lh410': 1}
          and rf['salida'] == referencia(falta) and b'^LH0,320' not in etiqueta(2),
          'V) falta un comando: avisa etiquetas 2 y 3, no inventa nada')

    extra = b'\xef\xbb\xbf; encabezado de ML\r\n^XA^MCY^XZ\r\n' + etiqueta(1, b'\r\n') + etiqueta(2, b'\r\n') + b'\r\n-- fin --\r\n\x1a'
    rx = corregir(extra)
    check(rx['ok'] and rx['salida'] == referencia(extra) and rx['salida'].startswith(b'\xef\xbb\xbf; encabezado')
          and rx['salida'].endswith(b'-- fin --\r\n\x1a') and rx['salida'].count(b'\r\n') == extra.count(b'\r\n')
          and b'\n' not in rx['salida'].replace(b'\r\n', b''),
          'V) contenido extra antes/después + BOM + CRLF Windows: todo conservado, sin normalizar saltos')
    check(rx['incompletas'] == [1] and 'Windows' in rx['finDeLinea'],
          '   el bloque auxiliar ^XA^MCY^XZ figura como etiqueta sin comandos (aviso, sin cambios)')

    lat = etiqueta(1, nombre='Muñoz Ñandú – José'.encode('cp1252')) + etiqueta(2, nombre='😀 Ñ €'.encode('utf-8'))
    rl = corregir(lat)
    check(rl['ok'] and rl['salida'] == referencia(lat), 'V) caracteres especiales (CP1252 y UTF-8 con emoji) intactos byte a byte')

    ya = referencia(e10)
    check(corregir(ya)['salida'] == ya, 'V) archivo ya corregido: se mantiene sin cambios')

    nombres = pag.evaluate('''() => [ZPLCorrector.nombreCorregido('etiquetas_mercadolibre.zpl'),
        ZPLCorrector.nombreCorregido('Etiq.2026.TXT'), ZPLCorrector.extensionValida('a.ZPL'),
        ZPLCorrector.extensionValida('a.pdf'), ZPLCorrector.extensionValida('zpl')]''')
    check(nombres == ['etiquetas_mercadolibre_corregido.zpl', 'Etiq.2026_corregido.TXT', True, False, False],
          'N) nombre de salida con sufijo _corregido y extensión original; solo .zpl/.txt')

    # 6. Página real + descarga
    import werkzeug  # noqa: E402
    if not hasattr(werkzeug, '__version__'):
        werkzeug.__version__ = '3'
    import app as A  # noqa: E402
    vista = A.corrector_zpl
    while hasattr(vista, '__wrapped__'):
        vista = vista.__wrapped__
    with A.app.test_request_context('/herramientas/corrector-zpl'):
        html = vista()
    check('Corrector etiquetas ZPL' in html and 'zpl_corrector.js?v=' in html, 'P) la página renderiza con el ítem de menú y el JS versionado')

    pag2 = nav.new_page(accept_downloads=True)
    pedidos = []

    def ruteo(route):
        url = route.request.url
        pedidos.append((route.request.method, url))
        if url == 'http://sistema.test/herramientas/corrector-zpl':
            route.fulfill(body=html, content_type='text/html; charset=utf-8')
        elif url.startswith('http://sistema.test/static/js/zpl_corrector.js'):
            route.fulfill(body=JS, content_type='application/javascript')
        else:
            route.abort()
    pag2.route('**/*', ruteo)
    pag2.goto('http://sistema.test/herramientas/corrector-zpl')
    # Sin el CSS de Bootstrap (CDN bloqueado en la prueba) la barra lateral tapa los botones
    pag2.add_style_tag(content='nav.sidebar, .offcanvas, .d-none { display:none !important }')
    pag2.set_input_files('#zpl-file', files=[{'name': 'etiquetas_mercadolibre.zpl', 'mimeType': 'text/plain', 'buffer': e10}])
    pag2.wait_for_function("!document.getElementById('zpl-procesar').disabled")
    check(pag2.inner_text('#zpl-nombre') == 'etiquetas_mercadolibre.zpl', 'P) muestra el nombre del archivo cargado')
    pag2.click('#zpl-procesar')
    stats = [pag2.inner_text(s) for s in ('#st-etiquetas', '#st-lh90', '#st-lh410', '#st-total')]
    check(stats == ['10', '10', '10', '20'] and 'Listo' in pag2.inner_text('#zpl-estado'), f'P) resumen en pantalla: {stats}')
    with pag2.expect_download() as d:
        pag2.click('#zpl-descargar')
    dl = d.value
    contenido = open(dl.path(), 'rb').read()
    check(dl.suggested_filename == 'etiquetas_mercadolibre_corregido.zpl', f'6) nombre de descarga: {dl.suggested_filename}')
    check(contenido == referencia(e10) and re.findall(rb'Etiqueta n(\d+)', contenido) == [str(i).encode() for i in range(1, 11)]
          and contenido.count(b'^XA') == 10 and contenido.count(b'^XZ') == 10,
          '6) la descarga trae las 10 etiquetas completas, en orden, idéntica a la referencia')
    pag2.click('#zpl-ver')
    check(pag2.input_value('#zpl-corr') == referencia(e10).decode('utf-8') and pag2.input_value('#zpl-orig') == e10.decode('utf-8'),
          'C) vista previa original/corregido como texto plano')

    # Drag & drop + archivo con advertencia
    pag2.evaluate('''(a) => { const dt = new DataTransfer();
        dt.items.add(new File([new Uint8Array(a)], 'faltan.txt'));
        document.getElementById('zpl-drop').dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true})); }''',
                  list(falta))
    pag2.wait_for_function("document.getElementById('zpl-nombre').textContent === 'faltan.txt' && !document.getElementById('zpl-procesar').disabled")
    pag2.click('#zpl-procesar')
    estado = pag2.inner_text('#zpl-estado')
    check('2 de 3' in estado and 'advertencias' in estado, 'P) drag & drop + advertencia de etiquetas incompletas en pantalla')
    with pag2.expect_download() as d:
        pag2.click('#zpl-descargar')
    check(d.value.suggested_filename == 'faltan_corregido.txt', 'P) extensión .txt conservada en la descarga')

    pag2.set_input_files('#zpl-file', files=[{'name': 'vacio.zpl', 'mimeType': 'text/plain', 'buffer': b''}])
    pag2.wait_for_function("!document.getElementById('zpl-procesar').disabled")
    pag2.click('#zpl-procesar')
    check('vacío' in pag2.inner_text('#zpl-estado') and not pag2.is_visible('#zpl-descargar'), 'P) archivo vacío: error y sin botón de descarga')
    pag2.set_input_files('#zpl-file', files=[{'name': 'foto.pdf', 'mimeType': 'application/pdf', 'buffer': b'%PDF'}])
    check('no es .zpl ni .txt' in pag2.inner_text('#zpl-error-carga'), 'P) rechaza extensiones que no son .zpl/.txt')

    externos = [p for p in pedidos if 'sistema.test' not in p[1]]
    posts = [p for p in pedidos if p[0] != 'GET']
    check(not posts, f'S) ningún POST/subida al servidor durante el uso ({len(pedidos)} requests, todos GET)')
    print(f'      requests externos (CDN de Bootstrap, bloqueados en la prueba): {len(externos)}')
    nav.close()

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
