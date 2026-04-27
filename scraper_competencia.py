"""
scraper_competencia.py — Scraping de competencia ML.
Corre en Windows con Chrome conectado vía CDP en puerto 9222.

Pipeline:
1. Pide al VPS la lista de sondas activas (publicaciones propias con cuotas conocidas).
2. Scrapea las 6 URLs de listado de competidores (TMS, Ivana, Lanus × colchones, sommiers).
3. Scrapea individualmente cada URL de sonda para detectar el pasaje activo.
4. Genera competencia_completo.csv (productos) + sondas_resultado.csv (cuotas mostradas).

Configuración:
    VPS_BASE: URL del sistema (sin barra final)
"""
from playwright.sync_api import sync_playwright
import csv, re, requests, sys
from datetime import datetime

# ============================================================================
# Configuración
# ============================================================================
VPS_BASE = 'https://sistema.mercadomuebles.com.ar'

# ============================================================================
# Listado de tiendas a scrapear (igual que antes)
# ============================================================================
TIENDAS = [
    {'nombre':'TMS',  'categoria':'sommiers',
     'url_p1':'https://listado.mercadolibre.com.ar/tienda/tu-mejor-sommier/listado/hogar-muebles-jardin/camas-colchones-accesorios/juegos-sommier-colchon/cannon/',
     'url_p2':'https://listado.mercadolibre.com.ar/tienda/tu-mejor-sommier/listado/hogar-muebles-jardin/camas-colchones-accesorios/juegos-sommier-colchon/cannon/_Desde_{offset}_NoIndex_True',
     'archivo':'tms_sommiers.csv'},
    {'nombre':'TMS',  'categoria':'colchones',
     'url_p1':'https://listado.mercadolibre.com.ar/tienda/tu-mejor-sommier/listado/hogar-muebles-jardin/camas-colchones-accesorios/colchones/cannon/',
     'url_p2':'https://listado.mercadolibre.com.ar/tienda/tu-mejor-sommier/listado/hogar-muebles-jardin/camas-colchones-accesorios/colchones/cannon/_Desde_{offset}_NoIndex_True',
     'archivo':'tms_colchones.csv'},
    {'nombre':'Ivana','categoria':'sommiers',
     'url_p1':'https://listado.mercadolibre.com.ar/tienda/colchoneria-ivana/listado/hogar-muebles-jardin/camas-colchones-accesorios/juegos-sommier-colchon/cannon/',
     'url_p2':'https://listado.mercadolibre.com.ar/tienda/colchoneria-ivana/listado/hogar-muebles-jardin/camas-colchones-accesorios/juegos-sommier-colchon/cannon/_Desde_{offset}_NoIndex_True',
     'archivo':'ivana_sommiers.csv'},
    {'nombre':'Ivana','categoria':'colchones',
     'url_p1':'https://listado.mercadolibre.com.ar/tienda/colchoneria-ivana/listado/hogar-muebles-jardin/camas-colchones-accesorios/colchones/cannon/',
     'url_p2':'https://listado.mercadolibre.com.ar/tienda/colchoneria-ivana/listado/hogar-muebles-jardin/camas-colchones-accesorios/colchones/cannon/_Desde_{offset}_NoIndex_True',
     'archivo':'ivana_colchones.csv'},
    {'nombre':'Lanus','categoria':'sommiers',
     'url_p1':'https://listado.mercadolibre.com.ar/pagina/muebleslanus/listado/hogar-muebles-jardin/camas-colchones-accesorios/juegos-sommier-colchon/cannon/',
     'url_p2':'https://listado.mercadolibre.com.ar/pagina/muebleslanus/listado/hogar-muebles-jardin/camas-colchones-accesorios/juegos-sommier-colchon/cannon/_Desde_{offset}_NoIndex_True',
     'archivo':'lanus_sommiers.csv'},
    {'nombre':'Lanus','categoria':'colchones',
     'url_p1':'https://listado.mercadolibre.com.ar/pagina/muebleslanus/listado/hogar-muebles-jardin/camas-colchones-accesorios/colchones/cannon/',
     'url_p2':'https://listado.mercadolibre.com.ar/pagina/muebleslanus/listado/hogar-muebles-jardin/camas-colchones-accesorios/colchones/cannon/_Desde_{offset}_NoIndex_True',
     'archivo':'lanus_colchones.csv'},
]

# ============================================================================
# Scraping de listado (igual que antes)
# ============================================================================
def scrapear_pagina(page, url):
    page.goto(url, timeout=30000)
    page.wait_for_timeout(3000)

    if 'login' in page.url or 'identification' in page.url:
        print("  -> Pide login. Logueate en el browser y presiona Enter...")
        input()
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)

    for _ in range(10):
        page.evaluate("window.scrollBy(0, 500)")
        page.wait_for_timeout(300)
    page.wait_for_timeout(1000)

    items = page.query_selector_all('.poly-card')
    productos = []
    for item in items:
        titulo = item.query_selector('.poly-component__title')
        precio = (item.query_selector('.poly-price__current .andes-money-amount__fraction') or
                  item.query_selector('.poly-component__price .andes-money-amount__fraction'))
        cuotas = item.query_selector('.poly-price__installments')
        envio  = item.query_selector('.poly-component__shipping')
        link   = item.query_selector('a.poly-component__title')
        if titulo:
            productos.append({
                'tienda':'', 'categoria':'',
                'titulo': titulo.inner_text().strip(),
                'precio': precio.inner_text().strip() if precio else '?',
                'cuotas': cuotas.inner_text().strip() if cuotas else '-',
                'envio':  envio.inner_text().strip() if envio else '-',
                'url':    link.get_attribute('href') if link else '-',
                'fecha':  datetime.now().strftime('%Y-%m-%d %H:%M'),
            })
    return productos


def scrapear_tienda(page, tienda):
    print(f"\n{'='*50}")
    print(f"Scrapeando {tienda['nombre']} - {tienda['categoria']}")
    print(f"{'='*50}")
    todos = []
    print("  Pagina 1...")
    prods = scrapear_pagina(page, tienda['url_p1'])
    for p in prods:
        p['tienda'] = tienda['nombre']
        p['categoria'] = tienda['categoria']
    print(f"  -> {len(prods)} productos")
    todos.extend(prods)
    offset = 49
    while True:
        url = tienda['url_p2'].format(offset=offset)
        print(f"  Offset {offset}...")
        prods = scrapear_pagina(page, url)
        for p in prods:
            p['tienda'] = tienda['nombre']
            p['categoria'] = tienda['categoria']
        print(f"  -> {len(prods)} productos")
        if len(prods) == 0:
            break
        todos.extend(prods)
        if len(prods) < 48:
            break
        offset += 48
        if offset > 1000:
            break
    print(f"  TOTAL {tienda['nombre']} {tienda['categoria']}: {len(todos)}")
    return todos


# ============================================================================
# Scraping de SONDA (página individual de un item)
# ============================================================================
def scrapear_sonda(page, sonda):
    """
    Entra a la URL de la sonda y extrae las cuotas s/i mostradas hoy en la UI.
    Devuelve cuotas_si_mostradas (int) o 0 si no se ve cuotas s/i.
    """
    print(f"  Sonda {sonda['item_id_ml']} ({sonda['tipo']}, {sonda['cuotas_reales']}c reales)...", end=' ')
    try:
        page.goto(sonda['url'], timeout=30000)
        page.wait_for_timeout(2500)
    except Exception as e:
        print(f"ERROR: {e}")
        return None

    # La zona de cuotas en una página de detalle puede estar en varios selectores.
    # Probamos varios y caemos al texto del body como último recurso.
    texto_zona = ''
    selectores = [
        '.ui-pdp-payment-cuotas-info',
        '.ui-pdp-installments',
        '.ui-pdp-payment-actions',
        '.ui-pdp-payment',
        '#price',
    ]
    for sel in selectores:
        elem = page.query_selector(sel)
        if elem:
            texto_zona = elem.inner_text()
            if 'cuota' in texto_zona.lower():
                break
    if not texto_zona or 'cuota' not in texto_zona.lower():
        # Fallback: zona de precio del header
        try:
            texto_zona = page.inner_text('body')[:8000]
        except Exception:
            texto_zona = ''

    # Detectar cuotas s/i: "Mismo precio en X cuotas"
    cuotas = 0
    m = re.search(r'mismo precio[^\d]*(\d+)\s*cuotas?', texto_zona, re.IGNORECASE)
    if m:
        cuotas = int(m.group(1))
    print(f"mostradas: {cuotas}c")
    return cuotas


# ============================================================================
# Pipeline principal
# ============================================================================
def obtener_sondas_del_vps():
    """Trae la lista de sondas activas desde el VPS."""
    try:
        r = requests.get(
            f"{VPS_BASE}/admin/competencia-scraper/sondas/lista",
            timeout=10
        )
        r.raise_for_status()
        return r.json().get('sondas', [])
    except Exception as e:
        print(f"  ⚠️  No pude obtener sondas del VPS: {e}")
        print(f"  Continuo sin scraping de sondas (no se actualizarán los pasajes).")
        return []


def main():
    # 1. Obtener sondas del VPS
    print("Obteniendo sondas del VPS...")
    sondas = obtener_sondas_del_vps()
    print(f"  -> {len(sondas)} sondas activas")

    # 2. Conectar a Chrome
    with sync_playwright() as p:
        print("\nConectando al Chrome abierto en puerto 9222...")
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.new_page()
        print("Conectado!\n")

        # 3. Scraping principal de tiendas
        todos_combinado = []
        for tienda in TIENDAS:
            prods = scrapear_tienda(page, tienda)
            todos_combinado.extend(prods)
            with open(tienda['archivo'], 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=['tienda','categoria','titulo','precio','cuotas','envio','url','fecha'])
                w.writeheader()
                w.writerows(prods)
            print(f"  Guardado: {tienda['archivo']}")

        with open('competencia_completo.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['tienda','categoria','titulo','precio','cuotas','envio','url','fecha'])
            w.writeheader()
            w.writerows(todos_combinado)
        print(f"\nGuardado competencia_completo.csv: {len(todos_combinado)} productos")

        # 4. Scraping de sondas
        if sondas:
            print(f"\n{'='*50}")
            print(f"Scrapeando {len(sondas)} sondas para detectar pasajes")
            print(f"{'='*50}")
            resultados = []
            for sonda in sondas:
                cuotas_mostradas = scrapear_sonda(page, sonda)
                if cuotas_mostradas is not None:
                    resultados.append({
                        'item_id_ml':       sonda['item_id_ml'],
                        'tipo':             sonda['tipo'],
                        'cuotas_reales':    sonda['cuotas_reales'],
                        'cuotas_mostradas': cuotas_mostradas,
                        'fecha':            datetime.now().strftime('%Y-%m-%d %H:%M'),
                    })
            with open('sondas_resultado.csv', 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=['item_id_ml','tipo','cuotas_reales','cuotas_mostradas','fecha'])
                w.writeheader()
                w.writerows(resultados)
            print(f"\nGuardado sondas_resultado.csv: {len(resultados)} sondas")

        browser.close()

    # 5. Resumen
    print(f"\n{'='*50}")
    print(f"SCRAPING COMPLETADO")
    print(f"  Productos:  {len(todos_combinado)} (competencia_completo.csv)")
    if sondas:
        print(f"  Sondas:     {len(resultados)}/{len(sondas)} (sondas_resultado.csv)")
    print(f"\nPaso siguiente: subir ambos CSVs al VPS con:")
    print(f"  curl -X POST -F 'competencia=@competencia_completo.csv' "
          f"-F 'sondas=@sondas_resultado.csv' "
          f"{VPS_BASE}/admin/competencia-scraper/upload")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
