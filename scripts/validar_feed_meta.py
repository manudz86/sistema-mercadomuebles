#!/usr/bin/env python3
"""Valida el feed de catálogo de Meta.

Dos modos:

  --local   Levanta una app Flask mínima con tienda_bp registrado y pide el feed
            por test_client. Sirve para validar ANTES de reiniciar el servicio.
  (default) Baja el feed de la URL pública y lo valida de punta a punta.

Chequea lo que hace rechazar productos en Meta:
  - XML bien formado y campos obligatorios presentes
  - id (SKU) único: sin duplicados
  - precio > 0 y moneda ARS; sale_price siempre menor que price
  - availability y condition con valores válidos
  - el link resuelve 200 y dos productos no caen en la misma URL final
  - la imagen resuelve 200, es una imagen y mide >= 500x500 (mínimo de Meta)
  - el precio del feed coincide con el de la ficha del producto (JSON-LD),
    que es la comparación que hace Meta y la que provoca rechazos

Uso:
    venv/bin/python3 scripts/validar_feed_meta.py --local
    venv/bin/python3 scripts/validar_feed_meta.py
    venv/bin/python3 scripts/validar_feed_meta.py --rapido   # sin chequear links
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import requests
from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')

URL_FEED = 'https://www.mercadomuebles.com.ar/tienda/feed/meta.xml'
G = '{http://base.google.com/ns/1.0}'
MIN_LADO = 500
OBLIGATORIOS = ('id', 'title', 'description', 'link', 'image_link',
                'availability', 'condition', 'price')


def feed_local():
    """Pide el feed a una app Flask mínima, sin reiniciar el servicio."""
    from flask import Flask
    import tienda_bp as tb

    # root_path explicito: si no, Flask lo deduce de este script y queda
    # apuntando a /home/cannon/app/scripts, donde no estan las imagenes.
    app = Flask(__name__,
                root_path='/home/cannon/app',
                static_folder='/home/cannon/app/static',
                template_folder='/home/cannon/app/templates')
    app.secret_key = 'validador'
    app.register_blueprint(tb.tienda_bp, url_prefix='/tienda')
    # Se invoca la vista dentro de un request context en vez de usar
    # test_client: esta version de werkzeug no expone __version__ y el cliente
    # de pruebas de Flask se cae al construirse.
    with app.test_request_context('/tienda/feed/meta.xml?nocache=1'):
        resp = app.ensure_sync(tb.feed_meta)()
        return resp.get_data(as_text=True)


def feed_remoto():
    r = requests.get(URL_FEED, timeout=60)
    r.raise_for_status()
    return r.text


def precio_de_la_ficha(url, sesion):
    """Precio publicado en la ficha, leído del JSON-LD Product/Offer."""
    try:
        r = sesion.get(url, timeout=25, allow_redirects=True)
        if r.status_code != 200:
            return None, r.status_code, r.url
        for m in re.finditer(
                r'<script type="application/ld\+json">(.*?)</script>', r.text, re.S):
            try:
                d = json.loads(m.group(1))
            except Exception:
                continue
            if d.get('@type') == 'Product':
                off = d.get('offers') or {}
                p = off.get('price')
                return (float(p) if p is not None else None), 200, r.url
        return None, 200, r.url
    except Exception:
        return None, -1, url


def main():
    local  = '--local' in sys.argv
    rapido = '--rapido' in sys.argv

    xml = feed_local() if local else feed_remoto()
    print(f'fuente: {"app local (test_client)" if local else URL_FEED}')
    print(f'tamaño: {len(xml)/1024:.1f} KB')

    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError as e:
        print(f'FATAL: XML mal formado: {e}'); return 1

    items = raiz.findall('./channel/item')
    print(f'items  : {len(items)}')
    print()

    errores, avisos = [], []
    ids, urls_finales = {}, {}
    por_tipo = {}
    sesion = requests.Session()
    sesion.headers['User-Agent'] = 'facebookexternalhit/1.1'

    for it in items:
        def g(n):
            e = it.find(G + n)
            return e.text if e is not None and e.text else None

        sku = g('id') or '(sin id)'

        for campo in OBLIGATORIOS:
            if not g(campo):
                errores.append(f'{sku}: falta <g:{campo}>')

        if sku in ids:
            errores.append(f'{sku}: ID DUPLICADO')
        ids[sku] = True

        tipo = g('product_type') or '?'
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1

        # precio y moneda
        precio = None
        if g('price'):
            m = re.match(r'^([0-9]+(?:\.[0-9]+)?) ([A-Z]{3})$', g('price'))
            if not m:
                errores.append(f'{sku}: price mal formado -> {g("price")!r}')
            else:
                precio = float(m.group(1))
                if m.group(2) != 'ARS':
                    errores.append(f'{sku}: moneda {m.group(2)}, deberia ser ARS')
                if precio <= 0:
                    errores.append(f'{sku}: precio {precio}')
        sale = None
        if g('sale_price'):
            m = re.match(r'^([0-9]+(?:\.[0-9]+)?) ([A-Z]{3})$', g('sale_price'))
            if not m:
                errores.append(f'{sku}: sale_price mal formado')
            else:
                sale = float(m.group(1))
                if precio and sale >= precio:
                    errores.append(f'{sku}: sale_price {sale} >= price {precio}')

        if g('availability') not in ('in stock', 'out of stock'):
            errores.append(f'{sku}: availability {g("availability")!r}')
        if g('condition') != 'new':
            errores.append(f'{sku}: condition {g("condition")!r}')

        if rapido:
            continue

        # imagen: tiene que bajar y medir >= 500
        img = g('image_link')
        if img:
            try:
                ri = sesion.get(img, timeout=25)
                if ri.status_code != 200:
                    errores.append(f'{sku}: imagen HTTP {ri.status_code}')
                elif not ri.headers.get('content-type', '').startswith('image/'):
                    errores.append(f'{sku}: imagen no es imagen '
                                   f'({ri.headers.get("content-type")})')
                else:
                    from PIL import Image
                    from io import BytesIO
                    w, h = Image.open(BytesIO(ri.content)).size
                    if min(w, h) < MIN_LADO:
                        errores.append(f'{sku}: imagen {w}x{h}, minimo {MIN_LADO}')
            except Exception as e:
                errores.append(f'{sku}: imagen ERROR {type(e).__name__}')

        # link: tiene que resolver 200 y no colisionar con otro producto
        link = g('link')
        if link:
            p_ficha, code, final = precio_de_la_ficha(link, sesion)
            if code != 200:
                errores.append(f'{sku}: link HTTP {code} -> {link}')
            else:
                if final in urls_finales and urls_finales[final] != sku:
                    errores.append(f'{sku}: misma URL final que '
                                   f'{urls_finales[final]} -> {final}')
                urls_finales[final] = sku

                esperado = sale if sale is not None else precio
                if p_ficha is None:
                    avisos.append(f'{sku}: la ficha no expone precio en JSON-LD')
                elif esperado and abs(p_ficha - esperado) > max(1.0, esperado * 0.01):
                    errores.append(f'{sku}: precio feed {esperado:.0f} != '
                                   f'ficha {p_ficha:.0f}')

    print('items por tipo:')
    for t, n in sorted(por_tipo.items()):
        print(f'  {t:<10} {n}')
    print()
    print(f'errores: {len(errores)}')
    for e in errores[:40]:
        print(f'  ✗ {e}')
    if len(errores) > 40:
        print(f'  ... y {len(errores)-40} mas')
    if avisos:
        print()
        print(f'avisos: {len(avisos)}')
        for a in avisos[:15]:
            print(f'  ! {a}')
        if len(avisos) > 15:
            print(f'  ... y {len(avisos)-15} mas')
    print()
    print('RESULTADO:', 'OK, el feed es publicable' if not errores
          else 'HAY ERRORES que Meta va a rechazar')
    return 0 if not errores else 1


if __name__ == '__main__':
    sys.exit(main())
