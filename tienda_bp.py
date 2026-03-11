"""
tienda_bp.py — Blueprint de la tienda online Mercadomuebles
Rutas:
    GET  /tienda/                    → Home con grilla de productos
    GET  /tienda/producto/<sku>      → Detalle de producto
    POST /tienda/carrito/agregar     → Agregar al carrito (session)
    GET  /tienda/carrito             → Ver carrito
    POST /tienda/carrito/eliminar    → Eliminar item del carrito
    POST /tienda/checkout            → Crear preferencia MP y redirigir
    GET  /tienda/pago/exito          → Página de éxito
    GET  /tienda/pago/pendiente      → Pago pendiente
    GET  /tienda/pago/error          → Pago fallido
    POST /tienda/webhook/mp          → Webhook Mercado Pago → descuenta stock
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
import pymysql
import os
import mercadopago
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

tienda_bp = Blueprint('tienda', __name__, url_prefix='/tienda')

@tienda_bp.app_template_filter('format_price')
def format_price_filter(value):
    if value is None:
        return '$0'
    try:
        return '${:,.0f}'.format(float(value)).replace(',', '.')
    except (ValueError, TypeError):
        return '$0'

# ── DB ─────────────────────────────────────────────────────────────────────────

def get_db():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'cannon'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'inventario_cannon'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# ── MERCADO PAGO ───────────────────────────────────────────────────────────────

def get_mp_sdk():
    return mercadopago.SDK(os.getenv('MP_ACCESS_TOKEN'))

# ── HELPERS ────────────────────────────────────────────────────────────────────

MODELO_DISPLAY = {
    'tropical':                 'Tropical',
    'princess':                 'Princess',
    'exclusive':                'Exclusive 25cm',
    'exclusive con pillow':     'Exclusive con Pillow 29cm',
    'renovation':               'Renovation',
    'renovation europillow':    'Renovation Europillow',
    'sonar':                    'Soñar',
    'doral':                    'Doral',
    'doral con pillow':         'Doral con Pillow',
    'sublime europillow':       'Sublime Europillow',
    'compac':                   'Compac',
    'compac plus pocket':       'Compac Plus Pocket',
}

LINEA_DISPLAY = {
    'espuma':   'Línea Espuma',
    'resortes': 'Línea Resortes',
    'box':      'Colchón en Caja',
}

PLAZA_MAP = {
    '80':  '1 Plaza',
    '90':  '1½ Plaza',
    '100': '1½ Plaza',
    '140': '2 Plazas',
    '150': '2 Plazas',
    '160': 'Queen Size',
    '180': 'King Size',
    '200': 'King Size',
}

def get_plaza(medida):
    if not medida:
        return ''
    ancho = medida.split('x')[0]
    return PLAZA_MAP.get(ancho, medida)

def format_price(price):
    """Formatea precio como $424.000"""
    if not price:
        return '$0'
    return '${:,.0f}'.format(float(price)).replace(',', '.')


def sku_colchon_a_conjunto(sku):
    """CEX140 → SEX140, CDO80 → SDO80, etc."""
    if sku and sku[0] == 'C':
        return 'S' + sku[1:]
    return sku

def sku_conjunto_a_colchon(sku):
    """SEX140 → CEX140"""
    if sku and sku[0] == 'S':
        return 'C' + sku[1:]
    return sku

def get_fotos_producto(sku):
    """
    Busca fotos en /static/img/productos/<SKU>/
    Una carpeta por SKU exacto (CEX140, SEX140, etc.)
    Sin fallbacks — si no hay carpeta, retorna placeholder.
    """
    fotos = []
    try:
        from flask import current_app
        carpeta = os.path.join(current_app.root_path, 'static', 'img', 'productos', sku)
        if os.path.isdir(carpeta):
            for i in range(1, 10):
                for ext in ['png', 'jpg', 'jpeg', 'webp']:
                    nombre = f'{i}.{ext}'
                    if os.path.exists(os.path.join(carpeta, nombre)):
                        fotos.append(url_for('static', filename=f'img/productos/{sku}/{nombre}'))
    except Exception:
        pass

    if not fotos:
        fotos.append(url_for('static', filename='img/placeholder-colchon.svg'))
    return fotos

def get_foto_url(sku):
    """Retorna URL de la foto principal (primera disponible)."""
    return get_fotos_producto(sku)[0]

# ── HOME ───────────────────────────────────────────────────────────────────────


def get_stock_disponible_sku(cursor, sku):
    """
    Stock disponible = stock_actual + stock_full (sin pendientes, ya que tablas no existen)
    """
    cursor.execute(
        "SELECT stock_actual, COALESCE(stock_full,0) as stock_full FROM productos_base WHERE sku = %s",
        (sku,)
    )
    prod = cursor.fetchone()
    if not prod:
        return 0
    return int(prod['stock_actual'] or 0) + int(prod['stock_full'] or 0)

def get_productos(cursor, filtros=None, pagina=1, por_pagina=20, orden='precio_asc'):
    filtros = filtros or {}

    where_clauses = []
    params = []

    if 'tipo' in filtros and filtros['tipo']:
        tipos = filtros['tipo'] if isinstance(filtros['tipo'], list) else [filtros['tipo']]
        where_clauses.append("tipo IN (%s)" * len(tipos))
        params.extend(tipos)

    if 'linea' in filtros and filtros['linea']:
        lineas = filtros['linea'] if isinstance(filtros['linea'], list) else [filtros['linea']]
        where_clauses.append("linea IN (%s)" * len(lineas))
        params.extend(lineas)

    if 'plaza' in filtros and filtros['plaza']:
        plazas = filtros['plaza'] if isinstance(filtros['plaza'], list) else [filtros['plaza']]
        where_clauses.append("plaza IN (%s)" * len(plazas))
        params.extend(plazas)

    if 'modelo' in filtros and filtros['modelo']:
        modelos = filtros['modelo'] if isinstance(filtros['modelo'], list) else [filtros['modelo']]
        where_clauses.append("modelo IN (%s)" * len(modelos))
        params.extend(modelos)

    if 'busqueda' in filtros and filtros['busqueda']:
        busqueda = f"%{filtros['busqueda']}%"
        where_clauses.append("(nombre LIKE %s OR descripcion LIKE %s OR sku LIKE %s)")
        params.extend([busqueda] * 3)

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    order_sql = {
        'precio_asc': "precio_base ASC",
        'precio_desc': "precio_base DESC",
        'nombre': "nombre ASC",
    }.get(orden, "precio_base ASC")

    offset = (pagina - 1) * por_pagina

    cursor.execute(f"""
        SELECT COUNT(*) as total FROM productos_base {where_sql}
    """, params)
    total = cursor.fetchone()['total']
    total_paginas = (total + por_pagina - 1) // por_pagina

    cursor.execute(f"""
        SELECT * FROM productos_base {where_sql}
        ORDER BY {order_sql}
        LIMIT %s OFFSET %s
    """, params + [por_pagina, offset])

    productos = cursor.fetchall()

    for p in productos:
        modelo = p['modelo'] or ''
        linea = p['linea'] or ''
        p['display_nombre'] = MODELO_DISPLAY.get(modelo, modelo.capitalize())
        p['display_linea'] = LINEA_DISPLAY.get(linea, linea.capitalize())
        p['display_plaza'] = get_plaza(p['medida'])
        p['precio'] = p['precio_base']  # Asignar para consistencia en templates/código
        p['precio_fmt'] = format_price(p['precio_base'])
        p['fotos'] = get_fotos_producto(p['sku'])
        p['foto_principal'] = p['fotos'][0]
        p['stock_disponible'] = get_stock_disponible_sku(cursor, p['sku'])

    return productos, total_paginas

@tienda_bp.route('/', methods=['GET'])
def home():
    db = get_db()
    cursor = db.cursor()

    try:
        filtros = {
            'tipo': request.args.getlist('tipo'),
            'linea': request.args.getlist('linea'),
            'plaza': request.args.getlist('plaza'),
            'modelo': request.args.getlist('modelo'),
            'busqueda': request.args.get('q'),
        }

        pagina = int(request.args.get('pagina', 1))
        orden = request.args.get('orden', 'precio_asc')

        productos, total_paginas = get_productos(cursor, filtros, pagina, orden=orden)

        filter_qs = '&'.join([f"{k}={v}" for k, vs in filtros.items() if vs for v in (vs if isinstance(vs, list) else [vs])])

        carrito_count = sum(item['cantidad'] for item in session.get('carrito', []))

        return render_template('tienda/home.html',
            productos=productos,
            pagina=pagina,
            total_paginas=total_paginas,
            orden=orden,
            filtros=filtros,
            filter_qs=filter_qs,
            busqueda=filtros.get('busqueda', ''),
            carrito_count=carrito_count,
            LINEA_DISPLAY=LINEA_DISPLAY,
            MODELO_DISPLAY=MODELO_DISPLAY,
        )
    finally:
        cursor.close()
        db.close()

# ── DETALLE PRODUCTO ───────────────────────────────────────────────────────────

@tienda_bp.route('/producto/<sku>')
def detalle_producto(sku):
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT * FROM productos_base WHERE sku = %s", (sku,))
        producto = cursor.fetchone()

        if not producto:
            return "Producto no encontrado", 404

        modelo = producto['modelo'] or ''
        linea = producto['linea'] or ''
        producto['display_nombre'] = MODELO_DISPLAY.get(modelo, modelo.capitalize())
        producto['display_linea'] = LINEA_DISPLAY.get(linea, linea.capitalize())
        producto['display_plaza'] = get_plaza(producto['medida'])
        producto['precio'] = producto['precio_base']  # Asignar para consistencia
        producto['precio_fmt'] = format_price(producto['precio_base'])
        producto['fotos'] = get_fotos_producto(sku)
        producto['stock_disponible'] = get_stock_disponible_sku(cursor, sku)

        carrito = session.get('carrito', [])
        en_carrito = next((item for item in carrito if item['sku'] == sku), None)

        carrito_count = sum(item['cantidad'] for item in carrito)

        return render_template('tienda/detalle.html',
            p=producto,
            en_carrito=en_carrito,
            carrito_count=carrito_count,
        )
    finally:
        cursor.close()
        db.close()

# ── CARRITO ────────────────────────────────────────────────────────────────────

def get_carrito():
    return session.get('carrito', [])

def set_carrito(carrito):
    session['carrito'] = carrito

almohadas_list = ['CLASICA','SUBLIME','CERVICAL','RENOVATION','PLATINO','DORAL','DUAL','EXCLUSIVE']

@tienda_bp.route('/carrito/agregar', methods=['POST'])
def agregar_carrito():
    data = request.json
    sku = data.get('sku')
    nombre = data.get('nombre')
    precio = float(data.get('precio'))
    cantidad = int(data.get('cantidad', 1))

    if not sku or not nombre or precio <= 0 or cantidad <= 0:
        return jsonify({'ok': False, 'msg': 'Datos inválidos'}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        stock = get_stock_disponible_sku(cursor, sku)
        if stock < cantidad:
            return jsonify({'ok': False, 'msg': f'Stock insuficiente (disponible: {stock})'}), 400

        carrito = get_carrito()
        es_almohada = sku in almohadas_list

        # Restricciones
        tiene_colchones = any(item['sku'].startswith(('C', 'S')) for item in carrito)
        if es_almohada and tiene_colchones:
            return jsonify({'ok': False, 'msg': 'No se pueden mezclar almohadas con colchones'}), 400
        if not es_almohada and any(item['sku'] in almohadas_list for item in carrito):
            return jsonify({'ok': False, 'msg': 'No se pueden mezclar colchones con almohadas'}), 400

        if es_almohada:
            total_almohadas = sum(item['cantidad'] for item in carrito if item['sku'] in almohadas_list) + cantidad
            if total_almohadas > 6:
                return jsonify({'ok': False, 'msg': 'Máximo 6 almohadas por compra'}), 400
        else:
            total_colchones_me2 = sum(item['cantidad'] for item in carrito if 'me2' in get_shipping_info([item])[0])
            if total_colchones_me2 + cantidad > 1:
                return jsonify({'ok': False, 'msg': 'Máximo 1 colchón ME2 por compra'}), 400

        item = next((i for i in carrito if i['sku'] == sku), None)
        if item:
            item['cantidad'] += cantidad
        else:
            carrito.append({'sku': sku, 'nombre': nombre, 'precio': precio, 'cantidad': cantidad})

        set_carrito(carrito)

        return jsonify({
            'ok': True,
            'total_items': sum(i['cantidad'] for i in carrito),
            'sku_tipo': 'almohada' if es_almohada else 'colchon'
        })
    finally:
        cursor.close()
        db.close()

@tienda_bp.route('/carrito/actualizar', methods=['POST'])
def actualizar_carrito():
    data = request.json
    sku = data.get('sku')
    delta = int(data.get('delta', 1))

    if not sku or delta == 0:
        return jsonify({'ok': False, 'msg': 'Datos inválidos'}), 400

    carrito = get_carrito()
    item = next((i for i in carrito if i['sku'] == sku), None)
    if not item:
        return jsonify({'ok': False, 'msg': 'Item no encontrado'}), 400

    nueva_cant = item['cantidad'] + delta

    db = get_db()
    cursor = db.cursor()
    try:
        stock = get_stock_disponible_sku(cursor, sku)
        if nueva_cant > stock:
            return jsonify({'ok': False, 'msg': f'Stock insuficiente (disponible: {stock})'}), 400
        if nueva_cant <= 0:
            carrito = [i for i in carrito if i['sku'] != sku]
        else:
            es_almohada = sku in almohadas_list
            if es_almohada:
                total_almohadas = sum(i['cantidad'] for i in carrito if i['sku'] in almohadas_list) + delta
                if total_almohadas > 6:
                    return jsonify({'ok': False, 'msg': 'Máximo 6 almohadas'}), 400
            item['cantidad'] = nueva_cant

        set_carrito(carrito)

        return jsonify({
            'ok': True,
            'cantidad_sku': max(0, nueva_cant),
            'total_items': sum(i['cantidad'] for i in carrito),
            'subtotal_fmt': format_price(sum(i['precio'] * i['cantidad'] for i in carrito)),
            'total_item_fmt': format_price(item['precio'] * max(0, nueva_cant)) if nueva_cant > 0 else ''
        })
    finally:
        cursor.close()
        db.close()

@tienda_bp.route('/carrito/eliminar', methods=['POST'])
def eliminar_carrito():
    data = request.json
    sku = data.get('sku')

    if not sku:
        return jsonify({'ok': False, 'msg': 'SKU requerido'}), 400

    carrito = [i for i in get_carrito() if i['sku'] != sku]
    set_carrito(carrito)

    subtotal = sum(i['precio'] * i['cantidad'] for i in carrito)

    return jsonify({
        'ok': True,
        'total_items': sum(i['cantidad'] for i in carrito),
        'subtotal_fmt': format_price(subtotal)
    })

@tienda_bp.route('/carrito/vaciar', methods=['POST'])
def vaciar_carrito():
    set_carrito([])
    return jsonify({'ok': True})

@tienda_bp.route('/carrito')
def ver_carrito():
    carrito = get_carrito()
    subtotal = sum(item['precio'] * item['cantidad'] for item in carrito)
    subtotal_fmt = format_price(subtotal)
    shipping_tipo, _ = get_shipping_info(carrito)
    carrito_count = sum(item['cantidad'] for item in carrito)

    return render_template('tienda/carrito.html',
        carrito=carrito,
        subtotal_fmt=subtotal_fmt,
        shipping_tipo=shipping_tipo,
        carrito_count=carrito_count,
    )

# ── ENVÍOS ─────────────────────────────────────────────────────────────────────

def get_dimensions(sku):
    """Retorna dict with length, width, height (cm), weight (kg)."""
    almohadas = almohadas_list
    if sku in almohadas:
        return {'length': 62, 'width': 40, 'height': 12, 'weight': 1.8}

    if sku.startswith('CCO') or sku.startswith('CCP'):
        medida = sku.split('_')[0][3:] if '_' in sku else sku[3:]
        weights = {'80': 14.8, '100': 19.2, '140': 23, '160': 27}
        peso = weights.get(medida, 20)
        return {'length': 115, 'width': 45, 'height': 45, 'weight': peso}

    # Para colchones chicos (80/90/100), estimado enrollado; ajustá valores
    if sku[0] in ('C', 'S') and sku[-3:] in ('080', '090', '100'):
        return {'length': 100, 'width': 30, 'height': 30, 'weight': 15}  # Ajustá con espesor real

    return None  # Sin dims, no ME2

def calculate_package_dimensions(carrito):
    """Calculate total package for ME2: sum weights (kg), estimate size (cm)."""
    total_weight = 0
    max_length = 0
    max_width = 0
    total_height = 0  # Assume stackable
    for item in carrito:
        dims = get_dimensions(item['sku'])
        if not dims:
            return None
        total_weight += dims['weight'] * item['cantidad']
        max_length = max(max_length, dims['length'])
        max_width = max(max_width, dims['width'])
        total_height += dims['height'] * item['cantidad']  # Stack height
    if total_height > 105:  # Max for ME2
        total_height = 105  # Cap, but may not be accurate
    return f"{int(max_length)}x{int(max_width)}x{int(total_height)},{int(total_weight * 1000)}"  # grams

def get_shipping_info(carrito):
    """Clasifica carrito: me2_paid (almohadas), me2_free (chicos/compac), zipnova (grandes), mixed."""
    tipos = set()
    for item in carrito:
        sku = item['sku']
        if sku in almohadas_list:
            tipos.add('me2_paid')
        elif sku.startswith('CCO') or sku.startswith('CCP'):
            tipos.add('me2_free')
        elif sku[0] in ('C', 'S') and int(sku[-3:]) <= 100:
            tipos.add('me2_free')
        else:
            tipos.add('zipnova')

    if len(tipos) > 1:
        return 'mixed', None
    return tipos.pop() if tipos else None, None

# ── CHECKOUT ───────────────────────────────────────────────────────────────────

@tienda_bp.route('/checkout', methods=['POST'])
def checkout():
    carrito = get_carrito()
    if not carrito:
        return redirect(url_for('tienda.ver_carrito'))

    base_url = os.getenv('APP_BASE_URL')

    sdk = get_mp_sdk()

    items = []
    for item in carrito:
        item_data = {
            'id': item['sku'],
            'title': item['nombre'],
            'quantity': int(item['cantidad']),
            'unit_price': float(item['precio']),
            'currency_id': 'ARS',
        }
        items.append(item_data)

    shipping_tipo, _ = get_shipping_info(carrito)

    shipments = None
    dimensions_str = calculate_package_dimensions(carrito)
    if shipping_tipo in ('me2_paid', 'me2_free') and dimensions_str:
        shipments = {
            'mode': 'me2',
            'free_shipping': shipping_tipo == 'me2_free',
            'dimensions': dimensions_str,
            'receiver_address': {'zip_code': '1407'}
        }
    else:
        if shipping_tipo in ('me2_paid', 'me2_free'):
            logger.warning("No usando ME2 porque faltan dimensions")

    preference_data = {
        'items': items,
        'back_urls': {
            'success': f"{base_url}/tienda/pago/exito",
            'failure': f"{base_url}/tienda/pago/error",
            'pending': f"{base_url}/tienda/pago/pendiente",
        },
        'auto_return': 'approved',
        'notification_url': f"{base_url}/tienda/webhook/mp",
        'statement_descriptor': 'MERCADOMUEBLES',
        'payment_methods': {
            'installments': 12,
        },
    }

    if shipments:
        preference_data['shipments'] = shipments

    logger.debug(f"Creando preferencia con data: {json.dumps(preference_data, default=str)}")

    result = sdk.preference().create(preference_data)
    preference = result.get('response', {})

    if 'id' not in preference:
        logger.error(f"Error creando preferencia MP: {result}")
        return redirect(url_for('tienda.ver_carrito'))

    # Guardar preference_id en session para verificar después
    session['mp_preference_id'] = preference['id']

    # Redirigir al checkout de MP
    return redirect(preference['init_point'])


@tienda_bp.route('/pago/exito')
def pago_exito():
    payment_id     = request.args.get('payment_id')
    status         = request.args.get('status')
    preference_id  = request.args.get('preference_id')

    # Limpiar carrito
    session.pop('carrito', None)
    session.pop('mp_preference_id', None)

    return render_template('tienda/pago_exito.html',
        payment_id    = payment_id,
        carrito_count = 0,
    )


@tienda_bp.route('/pago/pendiente')
def pago_pendiente():
    return render_template('tienda/pago_pendiente.html', carrito_count=0)


@tienda_bp.route('/pago/error')
def pago_error():
    return render_template('tienda/pago_error.html', carrito_count=0)

# ── WEBHOOK MERCADO PAGO ───────────────────────────────────────────────────────

@tienda_bp.route('/webhook/mp', methods=['POST'])
def webhook_mp():
    """
    Recibe notificaciones de MP, verifica el pago y descuenta stock.
    """
    data = request.get_json() or {}
    topic = data.get('type') or request.args.get('topic')
    resource_id = data.get('data', {}).get('id') or request.args.get('id')

    if topic not in ('payment', 'merchant_order'):
        return jsonify({'ok': True}), 200

    try:
        sdk = get_mp_sdk()

        if topic == 'payment':
            payment_info = sdk.payment().get(resource_id)
            payment      = payment_info.get('response', {})
            status       = payment.get('status')

            if status != 'approved':
                return jsonify({'ok': True}), 200

            # Extraer items del pago
            metadata = payment.get('metadata', {})
            items    = payment.get('additional_info', {}).get('items', [])
            _descontar_stock(items)

        return jsonify({'ok': True}), 200

    except Exception as e:
        logger.error(f"Error webhook MP: {e}")
        return jsonify({'error': str(e)}), 500


def _descontar_stock(items):
    """Descuenta stock de los productos pagados."""
    db = get_db()
    cursor = db.cursor()

    try:
        for item in items:
            titulo = item.get('title', '')
            qty    = int(item.get('quantity', 1))

            # Buscar SKU por nombre del producto
            cursor.execute("""
                SELECT sku FROM productos_base
                WHERE nombre LIKE %s AND tipo = 'colchon'
                LIMIT 1
            """, (f'%{titulo}%',))
            row = cursor.fetchone()
            if not row:
                continue

            sku = row['sku']
            cursor.execute("""
                UPDATE productos_base SET stock_actual = GREATEST(0, stock_actual - %s)
                WHERE sku = %s
            """, (qty, sku))

            # Si es conjunto también descontar base
            # Nota: Si conjunto_configuracion no existe, esto fallará en producción; comentado temporalmente
            # cursor.execute("""
            #     SELECT base_sku_default, cantidad_bases
            #     FROM conjunto_configuracion WHERE colchon_sku = %s AND activo = 1
            # """, (sku,))
            # cfg = cursor.fetchone()
            # if cfg and 'sommier' in titulo.lower():
            #     cant_bases = int(cfg['cantidad_bases'] or 1) * qty
            #     cursor.execute("""
            #         UPDATE productos_base SET stock_actual = GREATEST(0, stock_actual - %s)
            #         WHERE sku = %s
            #     """, (cant_bases, cfg['base_sku_default']))

        db.commit()
        logger.info(f"Stock descontado para {len(items)} items")

    except Exception as e:
        db.rollback()
        logger.error(f"Error descontando stock: {e}")
    finally:
        cursor.close()
        db.close()