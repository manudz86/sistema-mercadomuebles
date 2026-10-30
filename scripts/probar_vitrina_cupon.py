#!/usr/bin/env python3
"""Renderiza la tienda con el evento y el 2x1 SIMULADOS encendidos y verifica
que las almohadas no muestren precio de cupón y sí el mensaje del 2x1.

No toca la configuración real: parchea get_hot_event() y promo_2x1_activa()
en memoria, así se puede verificar antes de prender las promos en vivo.
"""
import re
import sys

from dotenv import load_dotenv

sys.path.insert(0, '/home/cannon/app')
load_dotenv('/home/cannon/app/config/.env')

fallos = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


def main():
    import tienda_bp as tb
    from flask import Flask

    # ── Simular evento activo + 2x1 activo ────────────────────────────────
    EVENTO = {
        'activo': True, 'titulo': 'CYBERSALE', 'cupon': 'CYBERSALE',
        'cupon_pct': 5, 'fechas': '1 AL 8 DE NOVIEMBRE', 'descuento_max': 10,
        'banner_desktop': '/static/img/banners/cybersale_desktop.jpg',
        'banner_mobile': '/static/img/banners/cybersale_mobile.jpg',
        'descuento_extra_catalogo': 0, 'descuento_extra_oferta': 0,
        'envio_gratis_caba': True,
    }
    tb.get_hot_event = lambda: dict(EVENTO)
    tb.promo_2x1_activa = lambda: True

    app = Flask(__name__, root_path='/home/cannon/app',
                static_folder='/home/cannon/app/static',
                template_folder='/home/cannon/app/templates')
    app.secret_key = 'vitrina'
    app.register_blueprint(tb.tienda_bp, url_prefix='/tienda')

    with app.test_request_context('/tienda/'):
        # ── Filtros, directo ──────────────────────────────────────────────
        print('filtros')
        chequear(tb._filtro_con_cupon(100000, 'CEX160') is not None,
                 'colchon: con_cupon devuelve precio',
                 str(tb._filtro_con_cupon(100000, 'CEX160')))
        chequear(tb._filtro_con_cupon(90000, 'CLASICA') is None,
                 'almohada: con_cupon devuelve None')
        chequear(tb._filtro_precio_2x1(90000, 'CLASICA') is not None,
                 'almohada: precio_2x1 devuelve 45.000',
                 str(tb._filtro_precio_2x1(90000, 'CLASICA')))
        chequear(tb._filtro_precio_2x1(500000, 'CEX160') is None,
                 'colchon: precio_2x1 devuelve None (no publica la mitad)')
        chequear(tb._filtro_lleva_cupon('CEX160') is True, 'lleva_cupon colchon')
        chequear(tb._filtro_lleva_cupon('CLASICA') is False, 'lleva_cupon almohada')
        a_alm = tb._filtro_ahorro_total({'sku': 'CLASICA', 'precio_base_real': 100000,
                                         'precio': 90000})
        chequear(a_alm == 10000, 'ahorro de almohada = solo catalogo, sin cupon',
                 str(a_alm))
        a_col = tb._filtro_ahorro_total({'sku': 'CEX160', 'precio_base_real': 100000,
                                         'precio': 90000})
        chequear(a_col == 14500, 'ahorro de colchon = catalogo + cupon', str(a_col))

    def render(url, fn, *args):
        with app.test_request_context(url):
            r = app.ensure_sync(fn)(*args)
            return r if isinstance(r, str) else (
                r.get_data(as_text=True) if hasattr(r, 'get_data') else str(r))

    # La home pagina, así que se pide cada tipo por separado: así la grilla
    # trae SOLO almohadas o SOLO colchones y las aserciones son inequívocas.
    print('home filtrada a ALMOHADAS')
    alm = render('/tienda/?tipo=almohada', tb.home)
    chequear('llevando 2 unidades' in alm,
             'muestra el precio por unidad llevando 2',
             re.search(r'(\$[\d.]+) cada una llevando', alm).group(1)
             if re.search(r'(\$[\d.]+) cada una llevando', alm) else '')
    chequear('badge-2x1">2x1' in alm, 'muestra el badge 2x1')
    chequear('CON CYBERSALE' not in alm,
             'NO muestra precio con cupon en ninguna almohada')
    # Se busca el markup RENDERIZADO, no el nombre de la clase: el CSS define
    # .ob-extra y .price-tachado en todas las paginas y daria falso positivo.
    chequear('class="ob-extra"' not in alm,
             'NO muestra el -5% extra del cyber en el badge')
    chequear('price-oferta price-tachado' not in alm,
             'NO tacha el precio de la almohada (no hay precio de cupon abajo)')

    print('home filtrada a COLCHONES')
    col = render('/tienda/?tipo=colchon', tb.home)
    chequear('CON CYBERSALE' in col, 'el colchon SI muestra precio con cupon')
    chequear('price-tachado' in col, 'el colchon tacha el precio de lista')
    chequear('llevando 2 unidades' not in col,
             'el colchon NO muestra mensaje de 2x1')

    # Las fichas se piden por SLUG: con el SKU la ruta responde un 301 al slug
    # canonico y lo que vuelve es el redirect, no la pagina.
    print('ficha de almohada')
    slug_alm = 'almohada-visco-clasica'
    det = render(f'/tienda/producto/{slug_alm}', tb.detalle, slug_alm)
    chequear(len(det) > 5000, 'la ficha renderizo (no es un redirect)', f'{len(det)} bytes')
    chequear('llevando 2 unidades' in det,
             'la ficha muestra el precio por unidad llevando 2')
    chequear('con el cupón' not in det, 'la ficha NO ofrece el cupon')

    print('ficha de colchon')
    slug_col = 'colchon-cannon-exclusive-160x200cm'
    detc = render(f'/tienda/producto/{slug_col}', tb.detalle, slug_col)
    chequear(len(detc) > 5000, 'la ficha renderizo', f'{len(detc)} bytes')
    chequear('con el cupón' in detc, 'la ficha del colchon SI ofrece el cupon')
    chequear('llevando 2 unidades' not in detc,
             'la ficha del colchon NO muestra el 2x1')

    print()
    print('RESULTADO:', 'la vitrina quedo correcta' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
