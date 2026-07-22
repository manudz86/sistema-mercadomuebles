import os, json, time, re, threading
from datetime import datetime, date, timedelta
import requests
import mysql.connector
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv('config/.env')

whatsapp_bp = Blueprint('whatsapp', __name__)

# ── Config ────────────────────────────────────────────────────────
WA_TOKEN      = os.getenv('WA_ACCESS_TOKEN')
WA_PHONE_ID   = os.getenv('WA_PHONE_NUMBER_ID')
WA_VERIFY_TOKEN = os.getenv('WA_VERIFY_TOKEN', 'mercadomuebles2025')
# Lista de números a los que se deriva (todos reciben la notificación)
NUMEROS_DERIVAR = ['+5491126275185', '+5491136696113']
# Nombre del template aprobado en WhatsApp Manager (Utility, Spanish ARG)
WA_TEMPLATE_DERIVACION = 'derivacion_cliente'
# Códigos de idioma a probar en orden (Meta usa distintos según la plantilla)
WA_TEMPLATE_LANGS = ['es_AR', 'es', 'es_LA', 'es_MX', 'es_ES']
ANTHROPIC_KEY  = os.getenv('ANTHROPIC_API_KEY')

anthropic = Anthropic(api_key=ANTHROPIC_KEY)

# Conversaciones en memoria: {phone: [{"role": ..., "content": ...}]}
conversaciones = {}
# Lock por número para evitar respuestas duplicadas
processing = {}

# ── Lógica de demora (replica tienda_bp.py) ───────────────────────
# Líneas/modelos que NUNCA muestran demora — siempre "sin stock"
_LINEAS_SIN_DEMORA  = {'compac', 'almohadas', 'box'}
_MODELOS_SIN_DEMORA = {'compac'}

def _aplica_demora(linea, tipo, modelo=None):
    """Replica aplica_demora() de tienda_bp.py."""
    if not linea and tipo == 'almohada':
        return False
    if (modelo or '').lower() in _MODELOS_SIN_DEMORA:
        return False
    return (linea or '').lower() not in _LINEAS_SIN_DEMORA

# ── DB ────────────────────────────────────────────────────────────
def _db():
    db = mysql.connector.connect(
        host='localhost', user='cannon',
        password=os.getenv('DB_PASSWORD', 'Sistema@32267845'),
        database='inventario_cannon'
    )
    cur = db.cursor()
    cur.execute("SET time_zone = '-03:00'")
    cur.close()
    return db

def _q(sql, params=None):
    db = _db(); cur = db.cursor(dictionary=True)
    try:
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        cur.close(); db.close()

def _exec(sql, params=None):
    db = _db(); cur = db.cursor()
    try:
        cur.execute(sql, params or ())
        db.commit()
    finally:
        cur.close(); db.close()

def _get_stock_disponible_bulk(skus):
    """
    Calcula stock disponible real para una lista de SKUs.
    Replica get_stock_disponible_sku() de tienda_bp.py pero en bulk (2 queries totales).
    Fórmula: (stock_actual + stock_full) - comprometido_en_ventas_pendientes
    El comprometido incluye ventas directas del SKU Y ventas de productos_compuestos que lo usan.
    """
    if not skus:
        return {}
    ph = ','.join(['%s'] * len(skus))
    skus_t = tuple(skus)

    # Stock físico (stock_actual + stock_full)
    fisico_rows = _q(f"""
        SELECT sku,
               COALESCE(stock_actual, 0) + COALESCE(stock_full, 0) AS stock_fisico
        FROM productos_base WHERE sku IN ({ph})
    """, skus_t)
    stock_fisico = {r['sku']: int(r['stock_fisico']) for r in fisico_rows}

    # Comprometido en ventas pendientes (replica lógica de tienda_bp.py)
    comp_rows = _q(f"""
        SELECT COALESCE(pb_comp.sku, iv.sku) AS sku,
               SUM(iv.cantidad * COALESCE(c.cantidad_necesaria, 1)) AS vendido
        FROM items_venta iv
        JOIN ventas v ON iv.venta_id = v.id
        LEFT JOIN productos_compuestos pc ON iv.sku = pc.sku
        LEFT JOIN componentes c ON pc.id = c.producto_compuesto_id
        LEFT JOIN productos_base pb_comp ON c.producto_base_id = pb_comp.id
        WHERE v.estado_entrega = 'pendiente'
          AND COALESCE(pb_comp.sku, iv.sku) IN ({ph})
        GROUP BY COALESCE(pb_comp.sku, iv.sku)
    """, skus_t)
    comprometido = {r['sku']: int(r['vendido'] or 0) for r in comp_rows}

    return {sku: max(0, stock_fisico.get(sku, 0) - comprometido.get(sku, 0)) for sku in skus}

def _crear_tablas():
    db = _db(); cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wa_mensajes (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            fecha       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            phone       VARCHAR(30),
            rol         ENUM('user','assistant'),
            contenido   TEXT,
            derivado    TINYINT(1) DEFAULT 0,
            INDEX idx_phone_fecha (phone, fecha)
        )
    """)
    db.commit(); cur.close(); db.close()

try:
    _crear_tablas()
except Exception as e:
    print(f"[WA] Error creando tablas: {e}")

# ── Zipnova ───────────────────────────────────────────────────────
ZIPNOVA_BASE_URL   = 'https://api.zipnova.com.ar/v2'
ZIPNOVA_PATAS_PESO = 2000

def _zn_creds():
    """Lee credenciales Zipnova en runtime para garantizar que dotenv ya cargó."""
    # Re-cargar por si acaso el path relativo no resolvió al importar
    from dotenv import load_dotenv as _lde
    import os as _os
    for p in ['config/.env', '/home/cannon/app/config/.env']:
        _lde(p, override=False)
    return (
        _os.getenv('ZIPNOVA_ACCOUNT_ID', '5786'),
        _os.getenv('ZIPNOVA_ORIGIN_ID', '374397'),
        _os.getenv('ZIPNOVA_API_KEY', ''),
        _os.getenv('ZIPNOVA_API_SECRET', ''),
    )

def _armar_bultos_bot(sku):
    """Arma bultos para un único SKU (colchon o sommier)."""
    bultos = []
    peso_patas = 0
    hay_patas  = False
    SKUS_ALM   = {'CLASICA','SUBLIME','CERVICAL','RENOVATION','PLATINO','DORAL','DUAL','EXCLUSIVE'}

    # ¿Es sommier?
    comp = _q("SELECT id FROM productos_compuestos WHERE sku=%s LIMIT 1", (sku,))
    if comp:
        comp_id = comp[0]['id']
        rows = _q("""
            SELECT pb.sku, pb.nombre, pb.alto_cm, pb.ancho_cm, pb.largo_cm,
                   pb.peso_gramos, c.cantidad_necesaria
            FROM componentes c
            JOIN productos_base pb ON c.producto_base_id = pb.id
            WHERE c.producto_compuesto_id = %s
        """, (comp_id,))
        for r in rows:
            csku = r['sku']; cant = r['cantidad_necesaria']
            if csku in SKUS_ALM:
                peso_patas += (r['peso_gramos'] or 0) * cant
            else:
                for _ in range(cant):
                    bultos.append({
                        'sku': csku, 'description': r['nombre'],
                        'weight': max(10, r['peso_gramos'] or 20000),
                        'height': r['alto_cm'] or 27,
                        'width':  r['ancho_cm'] or 100,
                        'length': r['largo_cm'] or 190,
                    })
        peso_patas += ZIPNOVA_PATAS_PESO
        hay_patas = True
    else:
        row = _q("SELECT nombre, alto_cm, ancho_cm, largo_cm, peso_gramos FROM productos_base WHERE sku=%s", (sku,))
        if row:
            r = row[0]
            bultos.append({
                'sku': sku, 'description': r['nombre'],
                'weight': max(10, r['peso_gramos'] or 20000),
                'height': r['alto_cm'] or 27,
                'width':  r['ancho_cm'] or 100,
                'length': r['largo_cm'] or 190,
            })

    if hay_patas:
        bultos.append({'sku':'PATAS','description':'Patas y accesorios',
                       'weight': max(10, int(peso_patas)), 'height':30,'width':20,'length':10})
    return bultos

CP_CIUDADES = {
    '1000': ('Buenos Aires', 'Buenos Aires'), '1425': ('Buenos Aires', 'Buenos Aires'),
    '1640': ('Martínez', 'Buenos Aires'), '1602': ('Florida', 'Buenos Aires'),
    '1706': ('Ituzaingó', 'Buenos Aires'), '1832': ('Lomas de Zamora', 'Buenos Aires'),
    '1900': ('La Plata', 'Buenos Aires'), '2000': ('Rosario', 'Santa Fe'),
    '2400': ('San Francisco', 'Córdoba'), '3000': ('Santa Fe', 'Santa Fe'),
    '3500': ('Resistencia', 'Chaco'), '4000': ('San Miguel de Tucumán', 'Tucumán'),
    '5000': ('Córdoba', 'Córdoba'), '5500': ('Mendoza', 'Mendoza'),
    '6000': ('Junín', 'Buenos Aires'), '7000': ('Tandil', 'Buenos Aires'),
    '8000': ('Bahía Blanca', 'Buenos Aires'), '9000': ('Comodoro Rivadavia', 'Chubut'),
}

def _cp_a_ciudad(cp):
    """Intenta resolver ciudad y provincia desde CP conocidos."""
    return CP_CIUDADES.get(cp, (cp, 'Buenos Aires'))

def cotizar_envio_bot(sku, cp, ciudad, provincia, precio_producto):
    """Cotiza envío con Zipnova. Retorna string listo para enviar al cliente."""
    try:
        bultos = _armar_bultos_bot(sku)
        if not bultos:
            return None
        zn_account, zn_origin, zn_key, zn_secret = _zn_creds()
        payload = {
            'account_id':     zn_account,
            'origin_id':      zn_origin,
            'declared_value': int(precio_producto),
            'destination':    {'zipcode': cp, 'city': ciudad, 'state': provincia},
            'items':          bultos,
        }
        resp = requests.post(
            f"{ZIPNOVA_BASE_URL}/shipments/quote",
            json=payload,
            auth=(zn_key, zn_secret),
            timeout=15
        )
        if resp.status_code != 200:
            return None
        resultados = resp.json().get('all_results') or resp.json().get('results') or []
        if not resultados:
            return None
        # Filtrar solo entrega a domicilio (excluir retiro en sucursal) — igual que la tienda web
        CODIGOS_DOMICILIO = {'standard_delivery', 'express_delivery', 'same_day', 'next_day'}
        resultados_domicilio = [
            r for r in resultados
            if (r.get('service_type') or {}).get('code', 'standard_delivery') in CODIGOS_DOMICILIO
            or isinstance(r.get('service_type'), str) and 'pickup' not in r.get('service_type', '').lower()
        ]
        if resultados_domicilio:
            resultados = resultados_domicilio
        # Tomar la opción más barata
        def _get_price(r):
            amounts = r.get('amounts', {})
            return amounts.get('price_incl_tax') or amounts.get('price') or 0
        def _get_dias(r):
            dt = r.get('delivery_time', {})
            mn = dt.get('min', '?')
            mx = dt.get('max', '?')
            if mn != '?' and mx != '?':
                return f"{mn}-{mx}"
            return str(mn)
        mejor = min(resultados, key=lambda x: _get_price(x) or 9999999)
        costo = _get_price(mejor)
        dias  = _get_dias(mejor)
        carrier = mejor.get('carrier', {})
        carrier_name = carrier.get('name', '') if isinstance(carrier, dict) else str(carrier)
        print(f"[WA] Zipnova OK: costo={costo} dias={dias} carrier={carrier_name}")
        carrier_name = carrier_name or 'transportista'
        if not costo or costo == 0:
            print(f"[WA] Zipnova devolvió $0 para {sku} CP {cp}")
            return None
        costo_final = int(costo) + 10000  # recargo fijo, igual que la tienda web
        return f"envío a domicilio en {ciudad} (CP {cp}) te sale ${costo_final:,} por {carrier_name} y llega en aproximadamente {dias} días hábiles"
    except Exception as e:
        print(f"[WA] Error Zipnova: {e}")
        return None

# ── Fotos ──────────────────────────────────────────────────────────
FOTO_BASE_URL = "https://sistema.mercadomuebles.com.ar/static/img/productos"

def wa_send_foto(to, sku, caption=""):
    """Envía foto del producto por WhatsApp."""
    foto_url = f"{FOTO_BASE_URL}/{sku}/1.jpg"
    try:
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages",
            headers={'Authorization': f'Bearer {WA_TOKEN}', 'Content-Type': 'application/json'},
            json={
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'image',
                'image': {'link': foto_url, 'caption': caption}
            },
            timeout=10
        )
        return r.status_code == 200
    except Exception as e:
        print(f"[WA] Error enviando foto: {e}")
        return False

# ── Productos ─────────────────────────────────────────────────────
def get_productos_context():
    """Devuelve contexto de productos para el system prompt (cacheado 10 min)."""
    cache = getattr(get_productos_context, '_cache', None)
    if cache and time.time() - cache['ts'] < 600:
        return cache['data']

    # Colchones
    colchones = _q("""
        SELECT p.sku, p.nombre, p.modelo, p.medida, p.linea, p.tipo, p.tipo_base,
               p.precio_base, p.descuento_catalogo, p.stock_actual,
               p.alto_cm, p.ancho_cm, p.largo_cm,
               COALESCE(o.descuento_pct, 0) as oferta_pct
        FROM productos_base p
        LEFT JOIN ofertas_home o ON o.sku = p.sku AND o.activo = 1
        WHERE p.activo = 1 AND p.tipo = 'colchon'
        ORDER BY p.modelo, p.medida
    """)

    # Almohadas
    almohadas = _q("""
        SELECT p.sku, p.nombre, p.linea, p.tipo, p.modelo,
               p.precio_base, p.descuento_catalogo, p.stock_actual,
               COALESCE(o.descuento_pct, 0) as oferta_pct
        FROM productos_base p
        LEFT JOIN ofertas_home o ON o.sku = p.sku AND o.activo = 1
        WHERE p.activo = 1 AND p.tipo = 'almohada'
        ORDER BY p.nombre
    """)

    # Sommiers — precio calculado sumando componentes (igual que la tienda web)
    sommiers_base = _q("""
        SELECT pc.sku, pc.nombre, pc.descuento_catalogo,
               COALESCE(o.descuento_pct, 0) as oferta_pct,
               pc.activo
        FROM productos_compuestos pc
        LEFT JOIN ofertas_home o ON o.sku = pc.sku AND o.activo = 1
        WHERE pc.activo = 1
        ORDER BY pc.nombre
    """)

    # Sumar precios de componentes para cada sommier
    sommiers = []
    for pc in sommiers_base:
        componentes = _q("""
            SELECT pb.sku, pb.precio_base, pb.descuento_catalogo as comp_desc, c.cantidad_necesaria,
                   pb.stock_actual, pb.linea, pb.tipo, pb.modelo
            FROM componentes c
            JOIN productos_base pb ON pb.id = c.producto_base_id
            WHERE c.producto_compuesto_id = (
                SELECT id FROM productos_compuestos WHERE sku = %s LIMIT 1
            )
        """, (pc['sku'],))

        if not componentes:
            continue

        # Precio base = suma de (precio_componente × cantidad)
        precio_sum = sum(
            float(c['precio_base'] or 0) * int(c['cantidad_necesaria'] or 1)
            for c in componentes
        )

        if precio_sum <= 0:
            continue

        sommiers.append({
            'sku':               pc['sku'],
            'nombre':            pc['nombre'],
            'precio_base':       precio_sum,
            'descuento_catalogo': pc['descuento_catalogo'],
            'oferta_pct':        pc['oferta_pct'],
            # Stock provisional con stock_actual crudo — se reemplaza abajo con bulk real
            'stock_actual':      min(int(c['stock_actual'] or 0) for c in componentes),
            # SKUs de componentes para calcular stock disponible real
            '_comp_skus':        [c['sku'] for c in componentes if c.get('sku')],
            # Para aplica_demora usamos el componente colchón (tipo != 'base')
            '_comp_linea':       next((c['linea']  for c in componentes if (c.get('tipo') or '') != 'base'), None),
            '_comp_tipo':        next((c['tipo']   for c in componentes if (c.get('tipo') or '') != 'base'), 'conjunto'),
            '_comp_modelo':      next((c['modelo'] for c in componentes if (c.get('tipo') or '') != 'base'), None),
        })

    # ── Stock disponible real (bulk, 2 queries) ───────────────────
    # Colchones: SKUs directos
    skus_colchones = [p['sku'] for p in colchones]
    # Almohadas: SKUs directos
    skus_almohadas_list = [a['sku'] for a in almohadas]
    # Sommiers: todos los SKUs de componentes (bases + colchones)
    skus_comp_sommiers = list({sku for s in sommiers for sku in s.get('_comp_skus', [])})

    todos_los_skus = list(set(skus_colchones + skus_almohadas_list + skus_comp_sommiers))
    stock_real = _get_stock_disponible_bulk(todos_los_skus) if todos_los_skus else {}

    # Reemplazar stock_actual por stock disponible real en colchones y almohadas
    for p in colchones:
        p['stock_actual'] = stock_real.get(p['sku'], 0)
    for a in almohadas:
        a['stock_actual'] = stock_real.get(a['sku'], 0)
    # Para sommiers: MIN del stock disponible real de sus componentes
    for s in sommiers:
        comp_stocks = [stock_real.get(sku, 0) for sku in s.get('_comp_skus', [])]
        s['stock_actual'] = min(comp_stocks) if comp_stocks else 0

    # Recargos cuotas — reflejan los medios REALMENTE activos (igual que la tienda)
    coefs = _q("SELECT clave, valor FROM configuracion WHERE clave LIKE 'cuotas_%_coef'")
    _cf = {r['clave']: float(r['valor']) for r in coefs}
    coef_6  = _cf.get('cuotas_6_coef', 1.25)      # GetNet (6 cuotas)
    coef_12 = _cf.get('cuotas_12_coef', 1.6)      # MercadoPago (12 cuotas, solo online)
    flags = _q("SELECT clave, valor FROM configuracion WHERE clave IN ('payway_enabled','getnet_enabled','mp_3_enabled','mp_12_enabled')")
    _fl = {r['clave']: str(r['valor']) for r in flags}
    payway_on = _fl.get('payway_enabled', '1') == '1'    # Payway 3 cuotas
    mp3_on    = _fl.get('mp_3_enabled', '0') == '1'       # MercadoPago 3 cuotas
    getnet_on = _fl.get('getnet_enabled', '1') == '1'     # GetNet 6 cuotas
    mp_12_on  = _fl.get('mp_12_enabled', '0') == '1'      # MercadoPago 12 cuotas
    # 3 cuotas: MENOR coeficiente entre los medios de 3 cuotas ACTIVOS (Payway 3 / MP 3)
    _c3 = []
    if payway_on: _c3.append(_cf.get('cuotas_3_coef', 1.25))
    if mp3_on:    _c3.append(_cf.get('cuotas_mp3_coef', 1.18))
    coef_3_ef = min(_c3) if _c3 else None   # None → no hay 3 cuotas activas

    def _cuotas_web_line(pf):
        """Línea de cuotas para el contexto, SOLO con los medios activos."""
        partes = []
        if coef_3_ef is not None:
            t3 = round(pf * coef_3_ef); partes.append(f"3 fijas de ${round(t3/3):,} (total ${t3:,})")
        if getnet_on:
            t6 = round(pf * coef_6);    partes.append(f"6 fijas de ${round(t6/6):,} (total ${t6:,})")
        if mp_12_on:
            t12 = round(pf * coef_12);  partes.append(f"12 fijas de ${round(t12/12):,} (total ${t12:,})")
        return ("  Cuotas Web: " + " | ".join(partes)) if partes else None

    # Demora sin stock
    dem_row = _q("SELECT valor FROM configuracion WHERE clave = 'demora_sin_stock'")
    demora_dias = int(dem_row[0]['valor']) if dem_row and dem_row[0]['valor'] else 0
    fecha_demora = (date.today() + timedelta(days=demora_dias)).strftime('%d/%m/%Y') if demora_dias else None

    def estado_stock(stock, linea, tipo, modelo):
        """Devuelve la etiqueta de disponibilidad para el contexto del bot."""
        if stock and int(stock) > 0:
            return '✅ Con stock'
        if demora_dias and _aplica_demora(linea, tipo, modelo):
            return f'⏳ Sin stock — demora {demora_dias} días hábiles (disponible aprox. {fecha_demora})'
        return '❌ Sin stock'

    def precio_final(precio_base, desc_cat, oferta):
        desc = max(float(desc_cat or 0), float(oferta or 0))
        return round(float(precio_base) * (1 - desc / 100))

    lines = ["=== PRODUCTOS Y PRECIOS (actualizados) ===",
             "Cada producto tiene precio Web (con descuento online) y precio Local (de lista, para compra presencial).",
             "Si NO hay descuento, ambos precios son iguales y se muestra solo uno.\n"]

    lines.append("--- COLCHONES ---")
    for p in colchones:
        if not p['precio_base']:
            continue
        precio_lista = round(float(p['precio_base']))
        pf = precio_final(p['precio_base'], p['descuento_catalogo'], p['oferta_pct'])
        desc = max(float(p['descuento_catalogo'] or 0), float(p['oferta_pct'] or 0))
        stock_txt = estado_stock(p['stock_actual'], p.get('linea'), p.get('tipo'), p.get('modelo'))
        link = f"https://www.mercadomuebles.com.ar/tienda/producto/{p['sku']}?utm_source=whatsapp&utm_medium=bot"
        if desc > 0:
            precio_str = f"Web: ${pf:,} (-{int(desc)}%) | Lista: ${precio_lista:,}"
        else:
            precio_str = f"Precio: ${pf:,}"
        lines.append(
            f"• {p['nombre']} (SKU:{p['sku']}) | {precio_str} | {stock_txt} | {link}"
        )
        # Cuotas sobre precio web (solo medios activos)
        _cl = _cuotas_web_line(pf)
        if _cl:
            lines.append(_cl)

    lines.append("\n--- SOMMIERS / CONJUNTOS (colchón + base) ---")
    for p in sommiers:
        if not p['precio_base']:
            continue
        precio_lista = round(float(p['precio_base']))
        pf = precio_final(p['precio_base'], p['descuento_catalogo'], p['oferta_pct'])
        desc = max(float(p['descuento_catalogo'] or 0), float(p['oferta_pct'] or 0))
        stock_txt = estado_stock(p['stock_actual'], p.get('_comp_linea'), p.get('_comp_tipo'), p.get('_comp_modelo'))
        link = f"https://www.mercadomuebles.com.ar/tienda/producto/{p['sku']}?utm_source=whatsapp&utm_medium=bot"
        if desc > 0:
            precio_str = f"Web: ${pf:,} (-{int(desc)}%) | Lista: ${precio_lista:,}"
        else:
            precio_str = f"Precio: ${pf:,}"
        lines.append(
            f"• {p['nombre']} (SKU:{p['sku']}) | {precio_str} | {stock_txt} | {link}"
        )
        # Cuotas sobre precio web (solo medios activos)
        _cl = _cuotas_web_line(pf)
        if _cl:
            lines.append(_cl)

    # Almohadas — sección separada, sin cuotas (productos accesorios)
    if almohadas:
        lines.append("\n--- ALMOHADAS ---")
        for a in almohadas:
            if not a['precio_base']:
                continue
            pf = precio_final(a['precio_base'], a['descuento_catalogo'], a['oferta_pct'])
            desc = max(float(a['descuento_catalogo'] or 0), float(a['oferta_pct'] or 0))
            stock_txt = estado_stock(a['stock_actual'], a.get('linea'), a.get('tipo'), a.get('modelo'))
            precio_str = f"Web: ${pf:,} (-{int(desc)}%)" if desc > 0 else f"${pf:,}"
            lines.append(f"• {a['nombre']} (SKU:{a['sku']}) | {precio_str} | {stock_txt}")

    # Bases sueltas
    bases = _q("""
        SELECT sku, nombre, precio_base FROM productos_base
        WHERE activo=1 AND (tipo = 'base' OR sku LIKE 'BASE%')
        ORDER BY nombre
    """)
    if bases:
        lines.append("\n--- BASES SUELTAS (precio por unidad, color fijo por modelo) ---")
        for b in bases:
            if b['precio_base']:
                lines.append(f"• {b['nombre']} (SKU:{b['sku']}) | ${int(b['precio_base']):,}")

    data = '\n'.join(lines)
    get_productos_context._cache = {'ts': time.time(), 'data': data}
    return data

# ── System prompt ─────────────────────────────────────────────────
CATALOGO_INFO = """
LÍNEA CANNON ACTUAL — CARACTERÍSTICAS DE PRODUCTOS:

VOCABULARIO IMPORTANTE:
- "Sommier", "conjunto" o "sommier conjunto" = colchón + base/box. Son sinónimos.
- "Colchón solo" = solo el colchón, sin base.
- "Base" o "box" = la base del sommier (se vende sola o en conjunto).
- "2 plazas" puede ser 140x190 cm O 150x190 cm — siempre confirmar medida exacta.

COLCHONES DE ESPUMA:
- Tropical Matelaseado: espuma 22kg/m³, 18cm alto, sistema flip, sensación suave, soporte 70kg. Color: diseño tropical multicolor. Ideal para uso diario.
- Princess 20: espuma 24kg/m³, 20cm, flip, firme, soporte 80kg. Color: diseño floral lila/gris. Tela sábana matelaseada.
- Princess 23: espuma 24kg/m³, 23cm, flip, firme, soporte 80kg. Color: blanco con banda gris oscura. Tela Jacquard.
- Exclusive: espuma alta densidad 30kg/m³, 25cm, flip, firme, soporte 100kg. Color: blanco con banda marrón oscuro. Máxima durabilidad.
- Exclusive Pillow Top: igual que Exclusive con capa pillow top, 29cm. Más suavidad al tacto.
- Renovation: espuma altísima densidad 35kg/m³, 26cm, flip, extra firme, soporte 120kg. Color: blanco/gris neutro.
- Renovation Euro Pillow: igual que Renovation con euro pillow, 33cm, extra firme.
- Compac: espuma multicapa 30kg/m³, 25cm, sistema NO flip, firme, soporte 100kg.

COLCHONES DE RESORTES:
- Soñar: resortes bicónicos reforzados, 23cm, flip, suave, soporte 80kg. Entrada de gama resortes.
- Doral: resortes continuos Ultracoil, 27cm, flip, firme, soporte 100kg. Color: diseño gris jaspeado con banda gris. Muy buena estabilidad.
- Doral Pillow Top: igual que Doral con pillow top, 33cm, firme.
- Sublime: resortes individuales Pocket, 32cm, flip, firme, soporte 120kg. Color: blanco perla con detalles dorados. No transmite movimiento entre personas.
- Sublime Euro Pillow: igual que Sublime con euro pillow, 35cm.

BASES / BOX — COLORES FIJOS POR MODELO (no son intercambiables):
Los colores de las bases hacen juego con la banda lateral del colchón correspondiente. NO se puede elegir color — cada modelo tiene su base específica.
- Base Sábana: color gris claro suave. Va con modelos Princess, Soñar, Tropical.
- Base Chocolate: color marrón oscuro. Va con modelos Exclusive, Doral.
- Base Gris: color gris oscuro. Va con Renovation, algunos Doral.
- Base Sublime: color beige/crema. Va exclusivamente con el Sublime.
Cada base tiene precio propio según modelo y medida (NO son todas al mismo precio).

ALTURA TOTAL DE SOMMIERS (siempre igual independientemente de la medida ancho/largo):
La fórmula es: patas (12cm) + base (21cm) + altura del colchón = altura total del conjunto
- Sommier Princess 20cm: 12 + 21 + 20 = 53cm total
- Sommier Princess 23cm: 12 + 21 + 23 = 56cm total
- Sommier Soñar: 12 + 21 + 23 = 56cm total
- Sommier Doral: 12 + 21 + 27 = 60cm total
- Sommier Doral Pillow Top: 12 + 21 + 33 = 66cm total
- Sommier Exclusive: 12 + 21 + 25 = 58cm total
- Sommier Exclusive Pillow Top: 12 + 21 + 29 = 62cm total
- Sommier Renovation: 12 + 21 + 26 = 59cm total
- Sommier Renovation Euro Pillow: 12 + 21 + 33 = 66cm total
- Sommier Sublime: 12 + 21 + 32 = 65cm total
- Sommier Sublime Euro Pillow: 12 + 21 + 35 = 68cm total

DOBLE FAZ / DAR VUELTA:
- Todos los colchones Cannon con pillow top o euro pillow tienen la capa de acolchado de AMBOS lados: se pueden (y conviene) dar vuelta y rotar periódicamente para un desgaste parejo y mayor durabilidad. NUNCA digas que el pillow está de un solo lado ni que no se puede dar vuelta.

MEDIDAS DISPONIBLES (según modelo): 80x190, 90x190, 100x190, 140x190, 150x190, 160x200, 180x200, 200x200

ENVÍOS Y RETIRO:
- Colchones y sommiers: Zipnova. Costo exacto se puede calcular con el código postal del cliente.
- Almohadas: calculado por MercadoPago en el checkout.
- CABA y GBA suelen ser más económicos que el interior del país.
- COORDINACIÓN DE ENTREGA: en AMBA (CABA y Gran Buenos Aires) la entrega la hacemos con flete propio y SE COORDINA con el cliente, así que SÍ se puede acordar el día de entrega. En el interior del país el envío va por transporte y los tiempos los define la empresa (no se puede fijar un día puntual, aunque se puede estimar). Nunca prometas una fecha u hora exacta: en AMBA se coordina el día una vez hecha la compra.
- IMPORTANTE: el envío es hasta la puerta de la calle (planta baja). NO incluye subida a departamento, piso ni acarreo interior. Si el cliente pregunta por subida o acarreo, aclarás esto directamente y sin derivar.
- RETIRO EN LOCAL: todos los productos se pueden retirar sin costo en nuestro local.
  Dirección: Bahía Blanca 1777, Floresta, Ciudad de Buenos Aires.
  Horario: lunes a viernes de 8 a 12hs y de 14 a 16.30hs.
  Sin costo de envío al retirar personalmente.

MEDIOS DE PAGO:
- MercadoPago: todas las formas (débito, crédito, transferencia, depósito, PagoFácil/RapiPago, dinero en cuenta MP).
- Tarjeta de crédito Visa o Mastercard bancarizadas: 3, 6 o 12 cuotas fijas (las 12 cuotas son solo online).

GARANTÍA: 5 años de garantía de fábrica.
"""

def get_system_prompt():
    productos = get_productos_context()
    # Horario de atención
    now = datetime.now()
    # Argentina es UTC-3
    hora_arg = (now.hour - 3) % 24
    dia_semana = now.weekday()  # 0=lunes, 6=domingo
    en_horario = (dia_semana < 5 and 8 <= hora_arg < 17)
    horario_txt = (
        "Estamos dentro del horario de atención (L-V 8-17hs)."
        if en_horario else
        "Estamos FUERA del horario de atención. El horario es lunes a viernes de 8 a 17hs. "
        "Cuando derives o el cliente pida hablar con alguien, avisale que un asesor lo va a contactar en ese horario."
    )

    return f"""Sos el asistente virtual de Mercado Muebles, distribuidora oficial de colchones Cannon en Buenos Aires.
Atendés consultas de clientes por WhatsApp.

PERSONALIDAD Y FORMATO:
- Amable y cercano, sin ser exagerado ni adulador
- Usás el voseo rioplatense (vos, tenés, podés)
- Respuestas concisas, máximo 4 párrafos
- NUNCA uses asteriscos (*), guiones (-) al inicio, ni ningún formato markdown
- Es WhatsApp: texto plano solamente. Usá saltos de línea para separar ideas.
- Podés usar emojis con moderación si viene al caso
- NUNCA te presentes como bot, agente virtual, IA o asistente automático a menos que el cliente lo pregunte explícitamente
- Si el cliente pregunta si sos un bot o una persona, podés responder honestamente que sos un asistente virtual

COTIZACIONES:
- "2 plazas" puede ser 140x190 O 150x190. SIEMPRE preguntá la medida exacta si no está confirmada.
- "Con base" o "con box" = sommier (colchón + base). Cotizá el sommier correspondiente.
- Cuando el cliente da 2 o más requisitos (medida + tipo + preferencia), mostrá TODOS los modelos que encajan, no solo los 2 más económicos. Si hay más de 3 que encajan, cotizá los 3 principales y mencioná los demás por nombre ofreciendo cotizarlos si el cliente quiere.
  Ejemplo: "También hay Sublime Euro Pillow y Exclusive Pillow Top que podrían interesarte, ¿querés que te los cotice?"
- Cuando cotices cuotas, usá este formato exacto: "3 cuotas fijas de $XX.XXX (total $XXX.XXX)", "6 cuotas fijas de $XX.XXX (total $XXX.XXX)" o "12 cuotas fijas de $XX.XXX (total $XXX.XXX)". Cotizá SOLO las cuotas que figuran en el contexto de cada producto (las 12 cuotas son solo online). NO menciones la marca del procesador de pagos (no digas Payway, GetNet, ni ningún nombre similar).
- Si el cliente pregunta por cuotas sin interés: explicá que las cuotas son fijas (el importe no varía cuota a cuota). No menciones ni confirmes ni niegues si tienen interés embebido.

PRECIOS (REGLA CRÍTICA):
- Cada producto tiene un "precio de lista" (sale de costos) y un "precio con descuento". El descuento sale de la base de datos, es por producto, y aplica ÚNICAMENTE en la tienda web.
- SIEMPRE cotizá el precio CON descuento: es el que ve y paga el cliente en la web, y es nuestro MENOR precio. Ese número YA tiene el descuento aplicado — NUNCA le restes otro descuento ni inventes un precio más bajo.
- Podés mencionar el precio de lista solo para mostrar el ahorro, con los números EXACTOS del contexto (ej: "de $436.000 baja a $405.480 con el descuento web"). Nunca inventes montos.
- El precio con descuento aplica a TODOS los pagos online: contado, 1 pago con tarjeta o en cuotas. "1 pago con tarjeta" NO es "precio de lista".
- NUNCA menciones ni cotices un precio del local físico (puede variar y no lo tenés). Si preguntan cuánto sale en el local, decíles que el precio del local se consulta presencialmente, pasales la dirección y el horario del local, y aclarales que nuestro MENOR precio es el online en la tienda web.
- Las cuotas (3/6/12) son formas de financiación, NO descuentos. No confundas "12 cuotas" con un "12%".

LINK DE LA TIENDA:
- Los links de cada producto ya vienen etiquetados en el contexto: pasalos TAL CUAL, no les recortes la parte de "?utm_source=...".
- Si compartís el link general de la tienda, usá siempre este: https://www.mercadomuebles.com.ar/tienda/?utm_source=whatsapp&utm_medium=bot

ENVÍOS:
- Podés calcular el costo de envío exacto si el cliente te da su código postal
- Cuando el cliente pida el costo de envío, pedile el código postal si no lo tenés
- Una vez que tengas SKU + CP, usá SOLO el comando sin texto adicional antes: [COTIZAR_ENVIO:SKU:CP:CIUDAD:PROVINCIA]
  El sistema genera el mensaje completo automáticamente. NO escribas nada antes del comando.
- Si el cliente pregunta el envío de DOS modelos, hacé DOS comandos separados
- Si no sabés la ciudad, usá "N/A" como ciudad

STOCK Y DEMORA (REGLA CRÍTICA):
En el contexto de productos cada artículo tiene uno de estos tres estados:
  ✅ Con stock — disponible para entrega inmediata. El tiempo de entrega es solo el del envío.
  ⏳ Sin stock — demora X días hábiles (disponible aprox. DD/MM) — el producto no está en depósito, hay una demora antes de poder despacharse. La entrega total es demora + tiempo de tránsito del envío.
  ❌ Sin stock — sin fecha de reposición, no disponible.

Reglas cuando cotices o respondas sobre disponibilidad:
- NUNCA digas "está con stock" si el contexto dice ⏳ o ❌.
- Para productos ⏳: aclarále al cliente que el artículo tiene una demora de X días hábiles antes de despacharse, y que a eso se suma el tiempo de envío. Ejemplo: "El Exclusive Pillow 140x190 está disponible con una demora de 10 días hábiles (disponible aprox. 15/05). A eso se suma el tiempo de envío una vez despachado."
- Para productos ❌: informá que no hay stock disponible y ofrecé alternativas si hay.
- Si el cliente pregunta la fecha de entrega de un producto ⏳: sumá la demora del producto + los días de tránsito del envío. Por ejemplo: "Demora 10 días hábiles + 3-4 días de tránsito = aproximadamente 13-14 días hábiles desde hoy."
- El retiro en local de un producto ⏳ también tiene la misma demora — no se puede retirar antes de la fecha disponible.

FOTOS:
- Cuando recomendés o cotices un producto específico, podés enviar la foto usando [FOTO:SKU]
  Ejemplo: "Acá te muestro cómo es. [FOTO:CDOP160]"
- Usá solo la primera foto — no mandes varias fotos seguidas
- Solo enviá foto cuando el cliente pregunta por un modelo específico

MEDIOS DE PAGO:
- MercadoPago (online en la tienda web): todas las formas (débito, crédito, transferencia, PagoFácil/RapiPago).
- Tarjeta de crédito Visa o Mastercard bancarizadas: 3 o 6 cuotas fijas (online y en el local) y 12 cuotas fijas (solo online), sin mencionar la marca del procesador de pagos.
- En el local también se acepta efectivo y transferencia.

HORARIO: {horario_txt}

DERIVAR A HUMANO cuando:
- El cliente pide hablar con una persona
- El cliente consulta por una compra ya realizada (pedido, entrega, reclamo)
- Detectás frustración (frases como "no entendés", "no me ayudás", más de 2 intentos fallidos)
- Pregunta algo fuera de tu alcance
Cuando derivés, usá EXACTAMENTE: [DERIVAR] seguido de tu mensaje.
Ejemplo en horario: "[DERIVAR] Te conecto con un asesor ahora."
Ejemplo fuera de horario: "[DERIVAR] Te paso con un asesor. Nuestro horario de atención personalizada es lunes a viernes de 8 a 17hs, así que te van a contactar en el próximo horario hábil."
SIEMPRE indicá el horario de atención cuando derivés fuera del horario comercial (L-V 8-17hs).

PLACAS Y TABLEROS (melamina, aglomerado, fenólico, MDF, paneles ranurados):
- Mercado Muebles se dedica a colchones, sommiers y almohadas Cannon. Las placas y tableros (melamina, aglomerado, fenólico, MDF, paneles ranurados) las maneja el sector de placas de Cimater, la empresa dueña de Mercado Muebles.
- Cuando el cliente pregunte o consulte por cualquiera de esos artículos, NO le digas que está equivocado ni que "solo vendemos colchones". Derivalo de forma amable al sector de placas de Cimater pasándole este teléfono tal cual: +54 9 11 5029-1777
- NO uses [DERIVAR] en estos casos: ese sector lo atiende Cimater (no Mercado Muebles), así que no hay que avisar a un asesor nuestro. Solo pasale el teléfono como texto.
- Ejemplo: "Las placas de melamina, MDF, fenólico y los paneles los maneja directamente el sector de placas de Cimater. Escribiles a este número y te asesoran: +54 9 11 5029-1777"

PUBLICACIONES DE MERCADO LIBRE:
- Este WhatsApp es solo para consultas de nuestra TIENDA WEB (mercadomuebles.com.ar) y del local. Las publicaciones de Mercado Libre son otro canal (precio, cuotas, stock o envíos pueden ser distintos) y NO se gestionan por acá.
- Si el cliente manda un link de Mercado Libre o pregunta por una publicación de ML: NO cotices ni compares contra el precio de esa publicación. Aclarale amablemente que ese es otro canal de consulta y pasale este número tal cual: para consultas de publicaciones de Mercado Libre, escribí al +54 9 11 2627-5185 (lunes a viernes de 8 a 16.30hs).
- Después de aclararlo, SÍ podés ofrecerle ayudarlo con ese mismo producto (o el equivalente) en nuestra tienda web, cotizándolo con nuestro precio si el cliente quiere.
- NO uses [DERIVAR] en estos casos: solo pasás el número como texto.

REGLAS CRÍTICAS — INCUMPLIRLAS ES UN ERROR GRAVE:
1. NUNCA preguntes algo que el cliente ya respondió en esta conversación
2. NUNCA hagas más de UNA pregunta por mensaje
3. Si el cliente dijo "colchón solo" → NUNCA vuelvas a preguntar si quiere con base
4. Si el cliente dio una medida → NUNCA vuelvas a preguntar la medida
5. Si el cliente dio un CP → calculá el envío directamente, no preguntes de qué producto
6. Si el cliente mencionó un modelo → no preguntes el modelo de nuevo
7. Leé el bloque "DATOS YA CONFIRMADOS" al inicio y úsalos como hechos firmes
8. Cuando tengas producto + medida + CP → ejecutá [COTIZAR_ENVIO:SKU:CP:CIUDAD:PROVINCIA] sin preguntar nada

NUNCA:
- Inventes precios o características que no estén en la info provista
- Des información sobre pedidos ya realizados
- Prometás fechas de entrega exactas
- Digas "no recibí mensajes anteriores" — el historial completo está disponible

{CATALOGO_INFO}

{productos}"""

# ── WhatsApp API ──────────────────────────────────────────────────
def wa_send(to, text):
    """Envía mensaje de texto por WhatsApp."""
    if not WA_TOKEN or not WA_PHONE_ID:
        print(f"[WA] Sin credenciales. Mensaje para {to}: {text[:50]}")
        return False
    try:
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages",
            headers={
                'Authorization': f'Bearer {WA_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'text',
                'text': {'body': text}
            },
            timeout=10
        )
        if r.status_code != 200:
            print(f"[WA] Error enviando a {to}: {r.status_code} {r.text[:100]}")
        return r.status_code == 200
    except Exception as e:
        print(f"[WA] Excepción enviando a {to}: {e}")
        return False

def _sanitizar_param_template(texto, max_chars=900):
    """
    Sanitiza un string para usarlo como parámetro de template WhatsApp.
    Meta rechaza: 4+ saltos de línea, 4+ tabs, 4+ espacios consecutivos.
    """
    if not texto:
        return '-'
    # Reemplazar saltos de línea por separador visual
    t = str(texto).replace('\r\n', '\n').replace('\r', '\n')
    # Compactar saltos múltiples (max 1) y reemplazar por " · "
    import re as _re
    t = _re.sub(r'\n+', ' · ', t)
    # Compactar espacios múltiples
    t = _re.sub(r'[ \t]+', ' ', t).strip()
    # Truncar a max_chars
    if len(t) > max_chars:
        t = t[:max_chars - 3] + '...'
    return t or '-'

def wa_send_template_derivacion(to, tel_cliente, resumen, ultimo_msg):
    """
    Envía el template 'derivacion_cliente' (Utility, aprobado en Meta).
    Funciona FUERA de la ventana de 24hs y a cualquier número.
    Reemplaza al envío freeform que solo funcionaba con testers.
    Prueba múltiples códigos de idioma hasta encontrar el que matchea.
    """
    if not WA_TOKEN or not WA_PHONE_ID:
        print(f"[WA] Sin credenciales para template a {to}")
        return False

    # Si ya descubrimos qué idioma funciona, usarlo primero
    cached_lang = getattr(wa_send_template_derivacion, '_cached_lang', None)
    langs_orden = ([cached_lang] + [l for l in WA_TEMPLATE_LANGS if l != cached_lang]) if cached_lang else WA_TEMPLATE_LANGS

    parametros = [
        {'type': 'text', 'text': _sanitizar_param_template(tel_cliente, 60)},
        {'type': 'text', 'text': _sanitizar_param_template(resumen, 700)},
        {'type': 'text', 'text': _sanitizar_param_template(ultimo_msg, 200)},
    ]

    ultimo_error = None
    for lang in langs_orden:
        payload = {
            'messaging_product': 'whatsapp',
            'to': to,
            'type': 'template',
            'template': {
                'name': WA_TEMPLATE_DERIVACION,
                'language': {'code': lang},
                'components': [{'type': 'body', 'parameters': parametros}]
            }
        }
        try:
            r = requests.post(
                f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages",
                headers={
                    'Authorization': f'Bearer {WA_TOKEN}',
                    'Content-Type': 'application/json'
                },
                json=payload,
                timeout=10
            )
            if r.status_code == 200:
                # Cachear el idioma que funcionó para los próximos envíos
                wa_send_template_derivacion._cached_lang = lang
                if lang != cached_lang:
                    print(f"[WA] Template OK con idioma '{lang}' (cacheado para próximos envíos)")
                return True
            # Si el error NO es 132001, no tiene sentido reintentar con otro idioma
            try:
                err_code = r.json().get('error', {}).get('code')
            except Exception:
                err_code = None
            ultimo_error = f"{r.status_code} {r.text[:200]}"
            if err_code != 132001:
                print(f"[WA] Error template derivacion a {to} (lang={lang}): {ultimo_error}")
                return False
        except Exception as e:
            ultimo_error = str(e)
            print(f"[WA] Excepción template derivacion a {to} (lang={lang}): {e}")

    print(f"[WA] Template derivacion FALLÓ con todos los idiomas para {to}: {ultimo_error}")
    return False

def wa_mark_read(phone, msg_id):
    """Marca mensaje como leído."""
    try:
        requests.post(
            f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages",
            headers={'Authorization': f'Bearer {WA_TOKEN}', 'Content-Type': 'application/json'},
            json={'messaging_product': 'whatsapp', 'status': 'read', 'message_id': msg_id},
            timeout=5
        )
    except Exception:
        pass

# ── Derivación ────────────────────────────────────────────────────
def derivar_a_humano(phone_cliente, historial):
    """Manda resumen al número de derivación."""
    try:
        msgs_texto = '\n'.join(
            f"{'Cliente' if m['role']=='user' else 'Bot'}: {m['content']}"
            for m in historial[-14:]
        )
        resumen_resp = anthropic.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=300,
            messages=[{
                'role': 'user',
                'content': f"""Resumí esta conversación de ventas en 3-4 líneas:
1. Qué producto buscaba (modelo, medida, con/sin base)
2. Qué info se le dio (precios, envío, medios de pago)
3. Por qué se derivó

{msgs_texto}

Solo el resumen, sin introducción."""
            }]
        )
        resumen = resumen_resp.content[0].text.strip()
    except Exception as e:
        print(f"[WA] Error generando resumen: {e}")
        resumen = "No se pudo generar resumen."

    # Último mensaje del CLIENTE, no del bot
    msgs_cliente = [m for m in historial if m['role'] == 'user']
    ultima_cliente = msgs_cliente[-1]['content'][:200] if msgs_cliente else '-'

    tel_cliente_fmt = f"+{phone_cliente}"

    # Enviar template a TODOS los números configurados
    resultados = []
    for numero in NUMEROS_DERIVAR:
        destino = numero.lstrip('+')
        ok = wa_send_template_derivacion(
            to=destino,
            tel_cliente=tel_cliente_fmt,
            resumen=resumen,
            ultimo_msg=ultima_cliente
        )
        resultados.append((numero, ok))
        print(f"[WA] Derivacion {'OK' if ok else 'FALLO'} para {phone_cliente} → {numero}")

    # Si TODOS los templates fallaron, intentar fallback freeform al primer número
    # (puede funcionar si ese número escribió al bot en las últimas 24hs)
    if not any(ok for _, ok in resultados):
        print(f"[WA] Todos los templates fallaron, intentando fallback freeform")
        msg_fallback = (
            f"Derivacion WA\n"
            f"Cliente: {tel_cliente_fmt}\n"
            f"Resumen: {resumen}\n"
            f"Ultimo mensaje del cliente: {ultima_cliente}"
        )
        primer_num = NUMEROS_DERIVAR[0].lstrip('+')
        wa_send(primer_num, msg_fallback)

# ── Claude ────────────────────────────────────────────────────────
def _extraer_contexto(historial):
    """
    Extractor rápido basado en reglas. Busca datos clave en el historial
    y los inyecta como contexto explícito para evitar re-preguntas.
    """
    if not historial or len(historial) < 2:
        return ""

    import re as _re

    # Texto completo del cliente (mensajes user)
    texto_cliente = ' '.join(
        m['content'].lower() for m in historial if m['role'] == 'user'
    )
    # Texto completo de toda la conv
    texto_todo = ' '.join(m['content'].lower() for m in historial)

    datos = {}

    # Medida — acepta "140x190", "de 140", "el 140", "140 está bien", "140 esta bien"
    medida_match = _re.search(r'(80|90|100|130|140|150|160|180|200)\s*[xX×]\s*1[89]0', texto_cliente)
    if medida_match:
        datos['Medida confirmada'] = medida_match.group(0).replace(' ','').upper()
    else:
        solo_num = _re.search(r'(?:(?:de(?:l)?|el|con|un|una)\s+)?(80|90|100|130|140|150|160|180|200)(?=\s|$|x|,|\.)', texto_cliente)
        if solo_num:
            n = int(solo_num.group(1))
            largo = '200' if n >= 160 else '190'
            datos['Medida confirmada'] = f'{n}x{largo}'

    # Tipo de producto
    if _re.search(r'(solo\s*colch[oó]n|colch[oó]n\s*solo|sin\s*base|sin\s*box|solo\s*el\s*colch[oó]n|colch[oó]n\s*(?:de|solo|nada\s*mas))', texto_cliente):
        datos['Tipo'] = 'solo colchón (SIN base/sommier) — NO volver a preguntar'
    elif _re.search(r'(con\s*base|con\s*box|sommier|conjunto|set)', texto_cliente):
        datos['Tipo'] = 'sommier/conjunto (colchón + base)'

    # Modelo mencionado
    modelos = {
        'tropical': 'Tropical', 'princess': 'Princess',
        'exclusive': 'Exclusive', 'renovation': 'Renovation',
        'doral': 'Doral', 'sublime': 'Sublime', 'soñar': 'Soñar',
        'sonar': 'Soñar', 'compac': 'Compac',
    }
    for k, v in modelos.items():
        if k in texto_cliente:
            datos['Modelo mencionado'] = v
            break

    # Pillow top
    if _re.search(r'\b(pillow|euro pillow|con pillow)\b', texto_cliente):
        datos['Variante'] = 'con Pillow Top'

    # Densidad
    dens = _re.search(r'\b(22|24|30|35)\s*kg\b', texto_cliente)
    if dens:
        datos['Densidad requerida'] = f'{dens.group(1)} kg/m³'

    # Código postal
    cp_match = _re.search(r'\bcp\s*(\d{4})\b|\b(\d{4})\b(?=.*rosario|.*córdoba|.*mendoza|.*tucumán)', texto_cliente)
    if not cp_match:
        cp_match = _re.search(r'(?:cp|código postal|codigo postal)[:\s]*(\d{4})', texto_cliente)
    if cp_match:
        cp = cp_match.group(1) or cp_match.group(2)
        datos['CP destino'] = cp

    # Ciudad mencionada
    ciudades = ['rosario', 'córdoba', 'cordoba', 'mendoza', 'tucumán', 'tucuman',
                'la plata', 'mar del plata', 'santa fe', 'bahía blanca', 'bahia blanca',
                'salta', 'neuquén', 'neuquen', 'resistencia', 'posadas']
    for c in ciudades:
        if c in texto_cliente:
            datos['Ciudad destino'] = c.title()
            break

    # Presupuesto
    if _re.search(r'\b(econ[oó]mico|barato|lo m[aá]s barato|precio bajo|entry)\b', texto_cliente):
        datos['Preferencia'] = 'económico'
    elif _re.search(r'\b(gama media|intermedio|relaci[oó]n calidad)\b', texto_cliente):
        datos['Preferencia'] = 'gama media'
    elif _re.search(r'\b(lo mejor|premium|alta gama|el mejor)\b', texto_cliente):
        datos['Preferencia'] = 'premium'

    if not datos:
        return ""

    lineas = ['\n⚠️ DATOS YA CONFIRMADOS (NO volver a preguntar):']
    for k, v in datos.items():
        lineas.append(f'  {k}: {v}')
    lineas.append('  → Usá estos datos directamente sin pedir confirmación.\n')
    return '\n'.join(lineas)

def _guardar_mensaje(phone, rol, contenido, derivado=False):
    """Guarda mensaje en BD para historial persistente."""
    try:
        _exec(
            "INSERT INTO wa_mensajes (phone, rol, contenido, derivado) VALUES (%s,%s,%s,%s)",
            (phone, rol, contenido, 1 if derivado else 0)
        )
    except Exception as e:
        print(f"[WA] Error guardando mensaje: {e}")

def procesar_mensaje(phone, texto):
    """Procesa mensaje del cliente y genera respuesta."""
    # Guardar mensaje en BD primero
    _guardar_mensaje(phone, 'user', texto)

    # Cargar historial desde BD — sin filtro de tiempo, últimos 30 mensajes
    # Funciona en todos los workers de gunicorn (estado compartido via BD)
    rows = _q("""
        SELECT rol, contenido, fecha FROM wa_mensajes
        WHERE phone = %s
        ORDER BY fecha DESC
        LIMIT 40
    """, (phone,))

    if rows:
        # Si el mensaje más reciente tiene más de 8hs de antigüedad → nueva sesión
        from datetime import timezone
        ultimo_ts = rows[0].get('fecha')
        if ultimo_ts:
            if hasattr(ultimo_ts, 'replace'):
                ultimo_ts = ultimo_ts.replace(tzinfo=timezone.utc) if ultimo_ts.tzinfo is None else ultimo_ts
            from datetime import datetime as _dt
            ahora = _dt.now(timezone.utc)
            diff_horas = (ahora - ultimo_ts).total_seconds() / 3600
            if diff_horas > 8:
                # Nueva sesión — solo el mensaje actual
                rows = [rows[0]]  # solo el que acabamos de guardar

    # Invertir para orden cronológico
    historial = [{'role': r['rol'], 'content': r['contenido']} for r in reversed(rows)]

    if not historial:
        historial = [{'role': 'user', 'content': texto}]

    print(f"[WA] {phone} — historial: {len(historial)} msgs, último: {historial[-1]['content'][:40]}")

    # Extraer contexto acumulado e inyectarlo al system prompt
    ctx_acumulado = _extraer_contexto(historial[:-1])  # sin el último mensaje del usuario
    _sys_estatico = get_system_prompt()
    system = [{"type": "text", "text": _sys_estatico, "cache_control": {"type": "ephemeral"}}]
    if ctx_acumulado:
        system.append({"type": "text", "text": ctx_acumulado})

    try:
        resp = anthropic.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=600,
            system=system,
            messages=historial
        )
        respuesta = resp.content[0].text.strip()
    except Exception as e:
        print(f"[WA] Error Claude: {e}")
        respuesta = "Disculpá, tuve un problema técnico. Podés intentar de nuevo en unos minutos."

    # Limpiar markdown que no funciona en WhatsApp
    import re as _re
    respuesta = _re.sub(r'\*\*(.+?)\*\*', r'\1', respuesta)
    respuesta = _re.sub(r'\*(.+?)\*', r'\1', respuesta)
    respuesta = _re.sub(r'^[•\-]\s+', '', respuesta, flags=_re.MULTILINE)
    respuesta = _re.sub(r'^\d+\.\s+', '', respuesta, flags=_re.MULTILINE)

    # Procesar todos los [COTIZAR_ENVIO:SKU:CP:CIUDAD:PROVINCIA] que haya
    for envio_match in list(_re.finditer(r'\[COTIZAR_ENVIO:([^:\]]+):([^:\]]+):([^:\]]+):([^:\]]+)\]', respuesta)):
        sku_env, cp_env, ciudad_env, prov_env = envio_match.groups()
        sku_env = sku_env.strip(); cp_env = cp_env.strip()
        # Auto-resolver ciudad/provincia si no se conocen
        if not ciudad_env.strip() or ciudad_env.strip() in ('N/A', '?', 'desconocida'):
            ciudad_env, prov_env = _cp_a_ciudad(cp_env)
        else:
            ciudad_env = ciudad_env.strip(); prov_env = prov_env.strip()
        # Buscar precio del producto
        prod = _q("SELECT nombre, precio_base, descuento_catalogo FROM productos_base WHERE sku=%s", (sku_env,))
        if not prod:
            prod = _q("SELECT nombre, precio_base, descuento_catalogo FROM productos_compuestos WHERE sku=%s", (sku_env,))
        precio_env = 0
        nombre_prod = sku_env
        if prod:
            pb = float(prod[0]['precio_base'] or 0)
            desc = float(prod[0]['descuento_catalogo'] or 0)
            precio_env = round(pb * (1 - desc/100))
            nombre_prod = prod[0].get('nombre', sku_env)
        costo_txt = cotizar_envio_bot(sku_env, cp_env, ciudad_env, prov_env, precio_env)
        if costo_txt:
            # Replace generic message with product-specific one
            # Mensaje completo con nombre del producto
            msg_envio = f"El envío del {nombre_prod} a {costo_txt}."
            # Si el bot escribió el nombre antes del comando, reemplazar todo para evitar duplicado
            import re as _re3
            patron_dup = r'(?:El envío del |el envío del )[^\[]{0,60}\[COTIZAR_ENVIO:[^\]]+\]'
            if _re3.search(patron_dup, respuesta):
                respuesta = _re3.sub(patron_dup, msg_envio, respuesta)
            else:
                respuesta = respuesta.replace(envio_match.group(0), msg_envio)
        else:
            # Zipnova falló - reemplazar con mensaje útil, no el comando crudo
            sku_display = sku_env
            respuesta = respuesta.replace(envio_match.group(0), 
                f"El costo de envío del {sku_display} a {ciudad_env} (CP {cp_env}) lo podés consultar directamente en el checkout de la tienda al ingresar tu código postal.")

    # Extraer comandos [FOTO:SKU] para enviarlos después
    fotos_a_enviar = _re.findall(r'\[FOTO:([A-Z0-9]+)\]', respuesta)
    respuesta = _re.sub(r'\[FOTO:[A-Z0-9]+\]', '', respuesta).strip()

    # Detectar derivación
    derivar = '[DERIVAR]' in respuesta
    if derivar:
        respuesta = respuesta.replace('[DERIVAR]', '').strip()

    historial.append({'role': 'assistant', 'content': respuesta})
    _guardar_mensaje(phone, 'assistant', respuesta, derivado=derivar)
    # Actualizar memoria también por si el próximo mensaje va al mismo worker
    conversaciones[phone] = historial[-20:]

    if derivar:
        threading.Thread(
            target=derivar_a_humano,
            args=(phone, historial.copy()),
            daemon=True
        ).start()

    return respuesta, fotos_a_enviar

# ── Webhook ───────────────────────────────────────────────────────
@whatsapp_bp.route('/webhook/whatsapp', methods=['GET'])
def webhook_verify():
    """Verificación del webhook por Meta."""
    mode      = request.args.get('hub.mode')
    token     = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == WA_VERIFY_TOKEN:
        print("[WA] Webhook verificado OK")
        return challenge, 200
    return 'Forbidden', 403

@whatsapp_bp.route('/webhook/whatsapp', methods=['POST'])
def webhook_message():
    """Recibe mensajes entrantes."""
    data = request.get_json(silent=True)
    if not data:
        return 'OK', 200

    try:
        entry = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])

        for msg in messages:
            phone  = msg.get('from', '')
            msg_id = msg.get('id', '')
            tipo   = msg.get('type', '')

            # Solo texto por ahora
            if tipo != 'text':
                wa_send(phone, "Por el momento solo puedo responder mensajes de texto. ¿En qué te puedo ayudar?")
                continue

            texto = msg.get('text', {}).get('body', '').strip()
            if not texto:
                continue

            # Evitar procesamiento duplicado
            if processing.get(msg_id):
                continue
            processing[msg_id] = True

            # Marcar como leído
            wa_mark_read(phone, msg_id)

            # Procesar en thread para no bloquear
            def responder(ph=phone, tx=texto, mid=msg_id):
                try:
                    respuesta, fotos = procesar_mensaje(ph, tx)
                    wa_send(ph, respuesta)
                    # Enviar fotos después del texto
                    for sku_foto in fotos:
                        wa_send_foto(ph, sku_foto)
                except Exception as e:
                    print(f"[WA] Error procesando {ph}: {e}")
                finally:
                    processing.pop(mid, None)

            threading.Thread(target=responder, daemon=True).start()

    except Exception as e:
        print(f"[WA] Error en webhook: {e}")

    return 'OK', 200

# ── Panel de conversaciones (admin) ──────────────────────────────
@whatsapp_bp.route('/admin/whatsapp/conversaciones')
def wa_conversaciones():
    """Vista rápida de conversaciones activas."""
    resumen = []
    for phone, msgs in conversaciones.items():
        if msgs:
            ultimo = msgs[-1]
            resumen.append({
                'phone': phone,
                'mensajes': len(msgs),
                'ultimo_rol': ultimo['role'],
                'ultimo_texto': ultimo['content'][:80],
            })
    return jsonify({'conversaciones': resumen, 'total': len(resumen)})

@whatsapp_bp.route('/admin/whatsapp/limpiar', methods=['POST'])
def wa_limpiar():
    data = request.get_json() or {}
    phone = data.get('phone')
    if phone and phone in conversaciones:
        del conversaciones[phone]
    return jsonify({'ok': True})

@whatsapp_bp.route('/admin/whatsapp')
def wa_admin():
    from flask import render_template
    return render_template('whatsapp_admin.html')

@whatsapp_bp.route('/admin/whatsapp/chats')
def wa_chats():
    """Lista de conversaciones con último mensaje."""
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    rows = _q("""
        SELECT phone,
               COUNT(*) as total_msgs,
               SUM(rol='user') as msgs_cliente,
               MAX(fecha) as ultimo_msg,
               MAX(derivado) as fue_derivado,
               (SELECT contenido FROM wa_mensajes m2
                WHERE m2.phone = m.phone ORDER BY fecha DESC LIMIT 1) as ultimo_texto
        FROM wa_mensajes m
        WHERE DATE(fecha) = %s
        GROUP BY phone
        ORDER BY MAX(fecha) DESC
    """, [fecha])
    def fix(r):
        return {k: (str(v) if hasattr(v,'strftime') else v) for k,v in r.items()}
    return jsonify({'chats': [fix(r) for r in rows], 'fecha': fecha})

@whatsapp_bp.route('/admin/whatsapp/chat/<phone>')
def wa_chat_detalle(phone):
    """Mensajes de una conversación."""
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    rows = _q("""
        SELECT id, fecha, rol, contenido, derivado
        FROM wa_mensajes
        WHERE phone = %s AND DATE(fecha) = %s
        ORDER BY fecha ASC
    """, [phone, fecha])
    def fix(r):
        return {k: (str(v) if hasattr(v,'strftime') else v) for k,v in r.items()}
    return jsonify({'mensajes': [fix(r) for r in rows], 'phone': phone})

@whatsapp_bp.route('/admin/whatsapp/fechas')
def wa_fechas():
    """Fechas con actividad."""
    rows = _q("""
        SELECT DATE(fecha) as fecha, COUNT(DISTINCT phone) as chats, COUNT(*) as msgs
        FROM wa_mensajes
        GROUP BY DATE(fecha)
        ORDER BY fecha DESC
        LIMIT 30
    """)
    return jsonify({'fechas': [{'fecha': str(r['fecha']), 'chats': r['chats'], 'msgs': r['msgs']} for r in rows]})
