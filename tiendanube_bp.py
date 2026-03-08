# tiendanube_bp.py
# Blueprint Flask para integración con Tiendanube
# Maneja: OAuth, webhooks de órdenes, sincronización de stock
#
# Integrar en app.py:
#   from tiendanube_bp import tiendanube_bp
#   app.register_blueprint(tiendanube_bp)

import os
import json
import hmac
import hashlib
import logging
import requests
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, redirect, session, url_for, render_template_string

logger = logging.getLogger(__name__)

tiendanube_bp = Blueprint('tiendanube', __name__, url_prefix='/tiendanube')

# ─────────────────────────────────────────────
# CONFIG (leer desde variables de entorno)
# ─────────────────────────────────────────────
TN_CLIENT_ID     = os.environ.get('TN_CLIENT_ID', '')
TN_CLIENT_SECRET = os.environ.get('TN_CLIENT_SECRET', '')
TN_REDIRECT_URI  = os.environ.get('TN_REDIRECT_URI', 'http://localhost:5000/tiendanube/callback')
TN_API_BASE      = 'https://api.tiendanube.com/v1'
TN_AUTH_URL      = 'https://www.tiendanube.com/apps/authorize/token'

# ─────────────────────────────────────────────
# HELPERS DB
# ─────────────────────────────────────────────
def get_db():
    """Reutiliza la conexión DB del app principal."""
    from app import get_db_connection
    return get_db_connection()

def get_tn_config():
    """Obtiene el token y store_id guardado en DB."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tiendanube_config ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    cursor.close()
    db.close()
    return row

def get_store_id():
    config = get_tn_config()
    return config['store_id'] if config else None

def get_access_token():
    config = get_tn_config()
    return config['access_token'] if config else None

# ─────────────────────────────────────────────
# API CLIENT
# ─────────────────────────────────────────────
def tn_request(method, endpoint, data=None, params=None):
    """Hace una request autenticada a la API de Tiendanube."""
    store_id = get_store_id()
    token    = get_access_token()
    if not store_id or not token:
        raise Exception("Tiendanube no configurado. Completá el OAuth primero.")
    
    url = f"{TN_API_BASE}/{store_id}/{endpoint}"
    headers = {
        'Authentication': f'bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': f'SistemaCannon/{TN_CLIENT_ID} (manu@cannon.com.ar)'
    }
    
    resp = requests.request(method, url, headers=headers, json=data, params=params, timeout=30)
    
    if resp.status_code == 429:
        logger.warning("Tiendanube rate limit alcanzado")
        raise Exception("Rate limit Tiendanube (429)")
    
    resp.raise_for_status()
    return resp.json() if resp.content else {}

# ─────────────────────────────────────────────
# OAUTH
# ─────────────────────────────────────────────
@tiendanube_bp.route('/auth')
def auth():
    """Inicia el flujo OAuth con Tiendanube."""
    auth_url = (
        f"https://www.tiendanube.com/apps/{TN_CLIENT_ID}/authorize"
        f"?redirect_uri={TN_REDIRECT_URI}"
    )
    return redirect(auth_url)

@tiendanube_bp.route('/callback')
def callback():
    """Recibe el código OAuth y obtiene el access token."""
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'No se recibió código OAuth'}), 400
    
    resp = requests.post(TN_AUTH_URL, data={
        'client_id':     TN_CLIENT_ID,
        'client_secret': TN_CLIENT_SECRET,
        'grant_type':    'authorization_code',
        'code':          code,
    })
    
    if not resp.ok:
        logger.error(f"Error OAuth Tiendanube: {resp.text}")
        return jsonify({'error': 'Error obteniendo token', 'detalle': resp.text}), 400
    
    data = resp.json()
    logger.info(f"TN OAuth response completa: {data}")
    
    # Tiendanube puede devolver el store_id en distintos campos según la versión
    store_id = (
        data.get('user_id') or
        data.get('store_id') or
        data.get('id') or
        str(data.get('userId', ''))
    )
    access_token = data.get('access_token')
    
    if not store_id or not access_token:
        return jsonify({
            'error': 'Respuesta OAuth incompleta',
            'data_recibida': data
        }), 400
    
    store_id = str(store_id)
    
    # Guardar en DB
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO tiendanube_config (store_id, access_token, scope, user_id)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            access_token = VALUES(access_token),
            scope = VALUES(scope),
            fecha_actualizacion = CURRENT_TIMESTAMP
    """, (store_id, access_token, data.get('scope', ''), store_id))
    db.commit()
    cursor.close()
    db.close()
    
    logger.info(f"Tiendanube OAuth completado. Store ID: {store_id}")
    return redirect(url_for('tiendanube.status'))

@tiendanube_bp.route('/status')
def status():
    """Muestra el estado de la conexión con Tiendanube."""
    config = get_tn_config()
    if not config:
        return jsonify({'conectado': False, 'mensaje': 'No configurado. Ir a /tiendanube/auth'})
    
    try:
        store_info = tn_request('GET', 'store')
        return jsonify({
            'conectado': True,
            'store_id': config['store_id'],
            'tienda': store_info.get('name'),
            'plan': store_info.get('plan_name'),
            'token_desde': str(config['fecha_creacion'])
        })
    except Exception as e:
        return jsonify({'conectado': True, 'store_id': config['store_id'], 'error_api': str(e)})

# ─────────────────────────────────────────────
# WEBHOOKS (Tiendanube notifica órdenes)
# ─────────────────────────────────────────────
def verify_webhook_signature(payload_bytes, signature_header):
    """Verifica que el webhook venga realmente de Tiendanube."""
    if not TN_CLIENT_SECRET:
        return True  # En dev, no verificar
    expected = hmac.new(
        TN_CLIENT_SECRET.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header or '')

@tiendanube_bp.route('/webhook/orders', methods=['POST'])
def webhook_orders():
    """
    Webhook que Tiendanube llama cuando hay una orden nueva/actualizada.
    Configurar en el panel de Tiendanube → Apps → Webhooks:
      URL: https://tudominio.com/tiendanube/webhook/orders
      Evento: order/paid
    """
    payload_bytes = request.get_data()
    signature = request.headers.get('X-Linkedstore-Token', '')
    
    if not verify_webhook_signature(payload_bytes, signature):
        logger.warning("Webhook Tiendanube: firma inválida")
        return jsonify({'error': 'Firma inválida'}), 401
    
    try:
        orden = request.get_json()
        return procesar_orden_tiendanube(orden)
    except Exception as e:
        logger.error(f"Error procesando webhook TN: {e}")
        return jsonify({'error': str(e)}), 500

def procesar_orden_tiendanube(orden):
    """
    Procesa una orden de Tiendanube:
    1. Guarda la orden en tiendanube_ordenes
    2. Descuenta stock de productos_base (colchón + base si es conjunto)
    """
    order_id       = orden.get('id')
    payment_status = orden.get('payment_status', '')
    
    # Solo procesar órdenes pagadas
    if payment_status not in ('paid', 'authorized'):
        logger.info(f"Orden TN #{order_id} ignorada (estado: {payment_status})")
        return jsonify({'ok': True, 'accion': 'ignorada', 'motivo': payment_status})
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Verificar si ya fue procesada
        cursor.execute(
            "SELECT id, procesada FROM tiendanube_ordenes WHERE tiendanube_order_id = %s",
            (order_id,)
        )
        existente = cursor.fetchone()
        if existente and existente['procesada']:
            return jsonify({'ok': True, 'accion': 'ya_procesada'})
        
        # Guardar/actualizar la orden
        cliente = orden.get('contact', {})
        cursor.execute("""
            INSERT INTO tiendanube_ordenes 
                (tiendanube_order_id, estado, payment_status, total, 
                 cliente_nombre, cliente_email, datos_json, fecha_orden)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                estado = VALUES(estado),
                payment_status = VALUES(payment_status),
                datos_json = VALUES(datos_json)
        """, (
            order_id,
            orden.get('status', 'open'),
            payment_status,
            orden.get('total', 0),
            f"{cliente.get('name', '')}",
            cliente.get('email', ''),
            json.dumps(orden, ensure_ascii=False),
            orden.get('created_at', datetime.now().isoformat())
        ))
        db.commit()
        
        # Descontar stock por cada ítem
        productos_descontados = []
        errores = []
        
        for item in orden.get('products', []):
            variant_id = item.get('variant_id')
            quantity   = item.get('quantity', 1)
            
            # Buscar mapeo
            cursor.execute("""
                SELECT m.*, cc.base_sku_default
                FROM sku_tiendanube_mapeo m
                LEFT JOIN conjunto_configuracion cc ON cc.colchon_sku = m.sku_interno
                WHERE m.tiendanube_variant_id = %s AND m.activo = 1
            """, (variant_id,))
            mapeo = cursor.fetchone()
            
            if not mapeo:
                errores.append(f"Variante {variant_id} sin mapeo")
                logger.warning(f"Orden TN #{order_id}: variante {variant_id} sin mapeo en sku_tiendanube_mapeo")
                continue
            
            sku_colchon = mapeo['sku_interno']
            
            # Descontar colchón
            cursor.execute("""
                UPDATE productos_base 
                SET stock_actual = GREATEST(0, stock_actual - %s)
                WHERE sku = %s
            """, (quantity, sku_colchon))
            productos_descontados.append(f"{sku_colchon} x{quantity}")
            
            # Si es conjunto, descontar también la base
            if mapeo['tipo'] == 'conjunto':
                base_sku = mapeo['base_sku'] or mapeo.get('base_sku_default')
                if base_sku:
                    cursor.execute("""
                        UPDATE productos_base
                        SET stock_actual = GREATEST(0, stock_actual - %s)
                        WHERE sku = %s
                    """, (quantity, base_sku))
                    productos_descontados.append(f"{base_sku} x{quantity} (base conjunto)")
                else:
                    errores.append(f"Conjunto {sku_colchon} sin base configurada")
        
        # Marcar orden como procesada
        cursor.execute("""
            UPDATE tiendanube_ordenes 
            SET procesada = 1, fecha_procesada = CURRENT_TIMESTAMP
            WHERE tiendanube_order_id = %s
        """, (order_id,))
        db.commit()
        
        logger.info(f"Orden TN #{order_id} procesada. Stock descontado: {productos_descontados}")
        
        return jsonify({
            'ok': True,
            'order_id': order_id,
            'descontados': productos_descontados,
            'errores': errores
        })
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error procesando orden TN #{order_id}: {e}")
        raise
    finally:
        cursor.close()
        db.close()

# ─────────────────────────────────────────────
# SINCRONIZACIÓN DE STOCK
# ─────────────────────────────────────────────
@tiendanube_bp.route('/sync/stock', methods=['POST'])
def sync_stock():
    """
    Sincroniza el stock actual de la DB hacia Tiendanube.
    Llamar: POST /tiendanube/sync/stock
    Body JSON: {"skus": ["CEX140", "CRE80"]} — o vacío para sincronizar todos
    """
    body = request.get_json() or {}
    skus_filtro = body.get('skus', [])
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        if skus_filtro:
            placeholders = ','.join(['%s'] * len(skus_filtro))
            cursor.execute(f"""
                SELECT m.tiendanube_variant_id, m.sku_interno, m.tipo,
                       p.stock_actual
                FROM sku_tiendanube_mapeo m
                JOIN productos_base p ON p.sku = m.sku_interno
                WHERE m.activo = 1 AND m.sku_interno IN ({placeholders})
            """, skus_filtro)
        else:
            cursor.execute("""
                SELECT m.tiendanube_variant_id, m.sku_interno, m.tipo,
                       p.stock_actual
                FROM sku_tiendanube_mapeo m
                JOIN productos_base p ON p.sku = m.sku_interno
                WHERE m.activo = 1
            """)
        
        variantes = cursor.fetchall()
        actualizadas = []
        errores = []
        
        for v in variantes:
            variant_id = v['tiendanube_variant_id']
            stock = v['stock_actual']
            
            # Para conjuntos, el stock es el mínimo entre colchón y base
            if v['tipo'] == 'conjunto':
                cursor.execute("""
                    SELECT LEAST(p.stock_actual, pb.stock_actual) as stock_conjunto
                    FROM sku_tiendanube_mapeo m
                    JOIN productos_base p ON p.sku = m.sku_interno
                    JOIN conjunto_configuracion cc ON cc.colchon_sku = m.sku_interno
                    JOIN productos_base pb ON pb.sku = cc.base_sku_default
                    WHERE m.tiendanube_variant_id = %s
                """, (variant_id,))
                row = cursor.fetchone()
                if row:
                    stock = row['stock_conjunto']
            
            try:
                # Actualizar stock en Tiendanube vía API
                product_id = _get_product_id_for_variant(cursor, variant_id)
                tn_request('PUT', f'products/{product_id}/variants/{variant_id}', {
                    'stock': stock
                })
                actualizadas.append({'variant_id': variant_id, 'sku': v['sku_interno'], 'stock': stock})
            except Exception as e:
                errores.append({'variant_id': variant_id, 'sku': v['sku_interno'], 'error': str(e)})
        
        return jsonify({
            'ok': True,
            'actualizadas': len(actualizadas),
            'errores': len(errores),
            'detalle_errores': errores
        })
    
    finally:
        cursor.close()
        db.close()

def _get_product_id_for_variant(cursor, variant_id):
    cursor.execute(
        "SELECT tiendanube_product_id FROM sku_tiendanube_mapeo WHERE tiendanube_variant_id = %s",
        (variant_id,)
    )
    row = cursor.fetchone()
    return row['tiendanube_product_id'] if row else None

# ─────────────────────────────────────────────
# GESTIÓN DE MAPEOS
# ─────────────────────────────────────────────
@tiendanube_bp.route('/mapeos', methods=['GET'])
def listar_mapeos():
    """Lista todos los mapeos SKU ↔ Tiendanube."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT m.*, p.nombre, p.stock_actual
        FROM sku_tiendanube_mapeo m
        LEFT JOIN productos_base p ON p.sku = m.sku_interno
        ORDER BY m.tipo, m.sku_interno
    """)
    mapeos = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(mapeos)

@tiendanube_bp.route('/mapeos', methods=['POST'])
def crear_mapeo():
    """
    Crea un mapeo SKU interno ↔ variante Tiendanube.
    Body: {
        "sku_interno": "CEX140",
        "tiendanube_product_id": 123456,
        "tiendanube_variant_id": 789012,
        "tipo": "colchon",  // o "conjunto"
        "base_sku": "BASE_GRIS140"  // solo si tipo=conjunto
    }
    """
    data = request.get_json()
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO sku_tiendanube_mapeo 
            (sku_interno, tiendanube_product_id, tiendanube_variant_id, tipo, base_sku)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            sku_interno = VALUES(sku_interno),
            tiendanube_product_id = VALUES(tiendanube_product_id),
            tipo = VALUES(tipo),
            base_sku = VALUES(base_sku)
    """, (
        data['sku_interno'],
        data['tiendanube_product_id'],
        data['tiendanube_variant_id'],
        data.get('tipo', 'colchon'),
        data.get('base_sku')
    ))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({'ok': True, 'id': cursor.lastrowid})

# ─────────────────────────────────────────────
# ÓRDENES
# ─────────────────────────────────────────────
@tiendanube_bp.route('/ordenes', methods=['GET'])
def listar_ordenes():
    """Lista las últimas 100 órdenes recibidas de Tiendanube."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT tiendanube_order_id, estado, payment_status, total,
               cliente_nombre, cliente_email, procesada,
               fecha_orden, fecha_procesada
        FROM tiendanube_ordenes
        ORDER BY fecha_creacion DESC
        LIMIT 100
    """)
    ordenes = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(ordenes)



# ============================================================
# AGREGAR ESTAS RUTAS AL FINAL DE tiendanube_bp.py
# (antes del último bloque si hay alguno)
# ============================================================

import time

# Mapeo de ancho → plaza (para mostrar en TN)
PLAZA_MAP = {
    '80':  '1 Plaza',
    '90':  '1½ Plaza',
    '100': '1½ Plaza',
    '130': '1½ Plaza',
    '140': '2 Plazas',
    '150': '2 Plazas',
    '160': 'Queen Size (160x200)',
    '180': 'King Size (180x200)',
    '200': 'King Size (200x200)',
}

# Catálogo completo: modelo → lista de SKUs de colchón
# True = también se vende en conjunto, False = solo colchón
CATALOGO = {
    # ── LÍNEA ESPUMA ──────────────────────────────────────────
    'Colchón Cannon Tropical': {
        'linea': 'espuma',
        'descripcion': 'Colchón de espuma de alta densidad, ideal para cuartos de invitados o uso ocasional. Tela ticking rayada. Fabricado por Cannon.',
        'conjunto': False,
        'skus': ['CTR80', 'CTR90', 'CTR100'],
    },
    'Colchón Cannon Princess 20cm': {
        'linea': 'espuma',
        'descripcion': 'Colchón de espuma 20cm de altura con tela ticking premium. Excelente relación precio-confort. Disponible solo o en conjunto con sommier.',
        'conjunto': True,
        'skus': ['CPR8020', 'CPR9020', 'CPR10020', 'CPR14020'],
    },
    'Colchón Cannon Princess 23cm': {
        'linea': 'espuma',
        'descripcion': 'Colchón de espuma 23cm de altura, mayor volumen y confort. Tela ticking premium. Disponible solo o en conjunto con sommier.',
        'conjunto': True,
        'skus': ['CPR8023', 'CPR9023', 'CPR10023', 'CPR14023'],
    },
    'Colchón Cannon Exclusive 25cm': {
        'linea': 'espuma',
        'descripcion': 'Colchón de espuma premium 25cm de altura. Tela jacquard de alta gama. Excelente soporte y durabilidad. Disponible solo o en conjunto con sommier.',
        'conjunto': True,
        'skus': ['CEX80', 'CEX90', 'CEX100', 'CEX140', 'CEX150', 'CEX160', 'CEX180', 'CEX200'],
    },
    'Colchón Cannon Exclusive con Pillow 29cm': {
        'linea': 'espuma',
        'descripcion': 'Colchón de espuma premium 29cm con pillow top incorporado para mayor suavidad superficial. El más completo de la línea espuma. Disponible solo o en conjunto.',
        'conjunto': True,
        'skus': ['CEXP80', 'CEXP90', 'CEXP100', 'CEXP140', 'CEXP150', 'CEXP160', 'CEXP180', 'CEXP200'],
    },
    'Colchón Cannon Renovation': {
        'linea': 'espuma',
        'descripcion': 'Colchón de espuma de alta densidad con tecnología de renovación. Ideal para uso diario. Tela ticking de alta resistencia. Disponible solo o en conjunto con sommier.',
        'conjunto': True,
        'skus': ['CRE80', 'CRE90', 'CRE100', 'CRE140', 'CRE150', 'CRE160', 'CRE180', 'CRE200'],
    },
    'Colchón Cannon Renovation Europillow': {
        'linea': 'espuma',
        'descripcion': 'Colchón Renovation con europillow incorporado para mayor altura y suavidad superficial. El tope de la línea Renovation. Disponible solo o en conjunto con sommier.',
        'conjunto': True,
        'skus': ['CREP80', 'CREP90', 'CREP100', 'CREP140', 'CREP150', 'CREP160', 'CREP180', 'CREP200'],
    },
    # ── LÍNEA RESORTES ────────────────────────────────────────
    'Colchón Cannon Soñar (Resortes)': {
        'linea': 'resortes',
        'descripcion': 'Colchón de resortes bonell, el modelo de entrada a la línea resortes Cannon. Excelente soporte y ventilación natural. Disponible solo o en conjunto con sommier.',
        'conjunto': True,
        'skus': ['CSO80', 'CSO90', 'CSO100', 'CSO140'],
    },
    'Colchón Cannon Doral (Resortes)': {
        'linea': 'resortes',
        'descripcion': 'Colchón de resortes bonell con mayor densidad de resortes. Soporte firme y distribución uniforme del peso. Disponible solo o en conjunto con sommier.',
        'conjunto': True,
        'skus': ['CDO80', 'CDO90', 'CDO100', 'CDO140', 'CDO150', 'CDO160', 'CDO180', 'CDO200'],
    },
    'Colchón Cannon Doral con Pillow (Resortes)': {
        'linea': 'resortes',
        'descripcion': 'Colchón Doral con pillow top para mayor suavidad superficial manteniendo el soporte de resortes. Disponible solo o en conjunto con sommier.',
        'conjunto': True,
        'skus': ['CDOP140', 'CDOP150', 'CDOP160', 'CDOP180', 'CDOP200'],
    },
    'Colchón Cannon Sublime Europillow (Resortes)': {
        'linea': 'resortes',
        'descripcion': 'El tope de línea de resortes Cannon. Europillow de alta densidad sobre sistema de resortes premium. Máximo confort y durabilidad. Disponible solo o en conjunto con sommier.',
        'conjunto': True,
        'skus': ['CSUP140', 'CSUP150', 'CSUP160', 'CSUP180', 'CSUP200'],
    },
    # ── COLCHÓN EN CAJA ───────────────────────────────────────
    'Colchón en Caja Cannon Compac': {
        'linea': 'box',
        'descripcion': 'Colchón de espuma enrollado al vacío que llega en caja. Fácil de transportar e instalar. Se expande completamente en pocas horas. Solo colchón.',
        'conjunto': False,
        'skus': ['CCO80_DEP', 'CCO100_DEP', 'CCO140_DEP', 'CCO160_DEP'],
    },
    'Colchón en Caja Cannon Compac Plus Pocket': {
        'linea': 'box',
        'descripcion': 'Colchón en caja con tecnología pocket coil enrollado al vacío. Mayor confort que el Compac estándar. Fácil transporte e instalación. Solo colchón.',
        'conjunto': False,
        'skus': ['CCP80_DEP', 'CCP100_DEP', 'CCP140_DEP', 'CCP160_DEP'],
    },
}

ALMOHADAS_SKUS = ['CLASICA', 'CERVICAL', 'DORAL', 'RENOVATION', 'PLATINO', 'EXCLUSIVE', 'DUAL', 'SUBLIME']


def _get_medida_info(medida_str):
    """Devuelve (medida_completa, plaza) a partir de '140x190'."""
    if not medida_str:
        return '', ''
    ancho = medida_str.split('x')[0]
    plaza = PLAZA_MAP.get(ancho, medida_str)
    return medida_str, plaza


def _crear_producto_tn(nombre, descripcion, variantes, categoria_id=None):
    """
    Crea un producto en Tiendanube con sus variantes.
    variantes = lista de dicts con keys: sku, precio, stock, medida, tipo
    Retorna el producto creado con sus variant IDs.
    """
    # Construir lista de variantes para la API
    tn_variantes = []
    for v in variantes:
        medida, plaza = _get_medida_info(v['medida'])
        variante = {
            'price': str(v['precio']),
            'stock': v['stock'],
            'sku': v['sku'],
            'attributes': [
                {'name': 'Medida', 'value': medida},
                {'name': 'Tipo', 'value': v['tipo']},
            ]
        }
        if v['stock'] == 0:
            variante['stock_management'] = True
        tn_variantes.append(variante)

    payload = {
        'name': {'es': nombre},
        'description': {'es': descripcion},
        'attributes': ['Medida', 'Tipo'],
        'variants': tn_variantes,
        'published': True,
    }

    if categoria_id:
        payload['categories'] = [{'id': categoria_id}]

    store_id = get_store_id()
    token = get_access_token()
    headers = {
        'Authentication': f'bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': f'SistemaCannon/{TN_CLIENT_ID} (manu@cannon.com.ar)'
    }
    url = f"{TN_API_BASE}/{store_id}/products"
    debug_resp = requests.post(url, headers=headers, json=payload, timeout=30)
    logger.error(f"TN 422 debug: {debug_resp.text}")
    debug_resp.raise_for_status()
    resultado = debug_resp.json()
        time.sleep(0.5)  # rate limiting cortesía
        return resultado


@tiendanube_bp.route('/crear-catalogo', methods=['POST'])
def crear_catalogo():
    """
    Crea todos los productos del catálogo Cannon en Tiendanube vía API
    y guarda los mapeos en sku_tiendanube_mapeo.

    POST /tiendanube/crear-catalogo
    Body opcional: {"solo_modelo": "Colchón Cannon Exclusive 25cm"}  → para crear uno solo
    """
    body = request.get_json() or {}
    solo_modelo = body.get('solo_modelo')  # para crear uno solo y testear

    db = get_db()
    cursor = db.cursor()

    creados = []
    errores = []

    try:
        # ── Traer precios y stock de la DB ──────────────────
        cursor.execute("""
            SELECT sku, medida, precio_base, stock_actual
            FROM productos_base
            WHERE tipo = 'colchon'
        """)
        colchones_db = {row['sku']: row for row in cursor.fetchall()}

        cursor.execute("""
            SELECT sku, medida, precio_base, stock_actual
            FROM productos_base
            WHERE tipo = 'base'
        """)
        bases_db = {row['sku']: row for row in cursor.fetchall()}

        cursor.execute("""
            SELECT colchon_sku, base_sku_default, cantidad_bases
            FROM conjunto_configuracion
            WHERE activo = 1
        """)
        conjuntos_cfg = {row['colchon_sku']: row for row in cursor.fetchall()}

        # ── Iterar catálogo ─────────────────────────────────
        modelos = CATALOGO.items()
        if solo_modelo:
            modelos = [(k, v) for k, v in CATALOGO.items() if k == solo_modelo]

        for nombre_modelo, cfg in modelos:
            logger.info(f"Creando producto: {nombre_modelo}")
            variantes = []

            for sku in cfg['skus']:
                if sku not in colchones_db:
                    errores.append(f"SKU {sku} no encontrado en DB")
                    continue

                col = colchones_db[sku]
                medida = col['medida'] or ''
                precio_colchon = float(col['precio_base'] or 0)
                stock_colchon = int(col['stock_actual'] or 0)

                # Variante: Solo Colchón
                variantes.append({
                    'sku': sku,
                    'medida': medida,
                    'tipo': 'Solo Colchón',
                    'precio': precio_colchon,
                    'stock': stock_colchon,
                    'tipo_mapeo': 'colchon',
                    'base_sku': None,
                })

                # Variante: Conjunto (si aplica)
                if cfg['conjunto'] and sku in conjuntos_cfg:
                    cfg_conj = conjuntos_cfg[sku]
                    base_sku = cfg_conj['base_sku_default']
                    cant_bases = int(cfg_conj['cantidad_bases'] or 1)

                    precio_base = 0
                    stock_base = 999
                    if base_sku in bases_db:
                        precio_base = float(bases_db[base_sku]['precio_base'] or 0) * cant_bases
                        stock_base = int(bases_db[base_sku]['stock_actual'] or 0)

                    precio_conjunto = precio_colchon + precio_base
                    stock_conjunto = min(stock_colchon, stock_base)

                    variantes.append({
                        'sku': f"{sku}_CONJ",
                        'medida': medida,
                        'tipo': 'Conjunto con Sommier',
                        'precio': precio_conjunto,
                        'stock': stock_conjunto,
                        'tipo_mapeo': 'conjunto',
                        'base_sku': base_sku,
                    })

            if not variantes:
                errores.append(f"Sin variantes para {nombre_modelo}")
                continue

            try:
                # Crear producto en TN
                producto_tn = _crear_producto_tn(
                    nombre_modelo,
                    cfg['descripcion'],
                    variantes
                )

                product_id = producto_tn.get('id')
                variantes_tn = producto_tn.get('variants', [])

                if not product_id:
                    errores.append(f"No se obtuvo product_id para {nombre_modelo}")
                    continue

                # Mapear variantes: el orden devuelto por TN coincide con el enviado
                for i, v_tn in enumerate(variantes_tn):
                    variant_id = v_tn.get('id')
                    if i >= len(variantes):
                        break
                    v_local = variantes[i]

                    cursor.execute("""
                        INSERT INTO sku_tiendanube_mapeo
                            (sku_interno, tiendanube_product_id, tiendanube_variant_id, tipo, base_sku)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            tiendanube_product_id = VALUES(tiendanube_product_id),
                            tipo = VALUES(tipo),
                            base_sku = VALUES(base_sku)
                    """, (
                        v_local['sku'],
                        product_id,
                        variant_id,
                        v_local['tipo_mapeo'],
                        v_local['base_sku'],
                    ))

                db.commit()
                creados.append({
                    'modelo': nombre_modelo,
                    'product_id': product_id,
                    'variantes': len(variantes_tn),
                })
                logger.info(f"✅ {nombre_modelo} creado. ID: {product_id}, variantes: {len(variantes_tn)}")

            except Exception as e:
                errores.append(f"Error creando {nombre_modelo}: {str(e)}")
                logger.error(f"Error creando {nombre_modelo}: {e}")

        # ── Almohadas ────────────────────────────────────────
        if not solo_modelo or solo_modelo == 'Almohadas Cannon':
            cursor.execute("""
                SELECT sku, nombre, precio_base, stock_actual
                FROM productos_base
                WHERE tipo = 'almohada'
                ORDER BY nombre
            """)
            almohadas = cursor.fetchall()

            if almohadas:
                variantes_alm = []
                for alm in almohadas:
                    variantes_alm.append({
                        'sku': alm['sku'],
                        'medida': '70x40',
                        'tipo': alm['nombre'].replace('Almohada ', ''),
                        'precio': float(alm['precio_base'] or 0),
                        'stock': int(alm['stock_actual'] or 0),
                        'tipo_mapeo': 'almohada',
                        'base_sku': None,
                    })

                try:
                    producto_tn = _crear_producto_tn(
                        'Almohadas Cannon',
                        'Almohadas Cannon de diferentes modelos y tecnologías. Visco cervical, visco clásica, memory foam, látex y más. Medida estándar 70x40cm.',
                        variantes_alm
                    )
                    product_id = producto_tn.get('id')
                    variantes_tn = producto_tn.get('variants', [])

                    for i, v_tn in enumerate(variantes_tn):
                        if i >= len(variantes_alm):
                            break
                        cursor.execute("""
                            INSERT INTO sku_tiendanube_mapeo
                                (sku_interno, tiendanube_product_id, tiendanube_variant_id, tipo, base_sku)
                            VALUES (%s, %s, %s, %s, NULL)
                            ON DUPLICATE KEY UPDATE
                                tiendanube_product_id = VALUES(tiendanube_product_id),
                                tipo = VALUES(tipo)
                        """, (
                            variantes_alm[i]['sku'],
                            product_id,
                            v_tn.get('id'),
                            'almohada',
                        ))

                    db.commit()
                    creados.append({
                        'modelo': 'Almohadas Cannon',
                        'product_id': product_id,
                        'variantes': len(variantes_tn),
                    })
                    logger.info(f"✅ Almohadas creadas. ID: {product_id}")

                except Exception as e:
                    errores.append(f"Error creando almohadas: {str(e)}")

        return jsonify({
            'ok': True,
            'productos_creados': len(creados),
            'errores': len(errores),
            'detalle_creados': creados,
            'detalle_errores': errores,
        })

    except Exception as e:
        db.rollback()
        logger.error(f"Error general crear_catalogo: {e}")
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        db.close()

