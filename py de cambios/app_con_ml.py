"""
ACTUALIZACIÓN DE app.py - INTEGRACIÓN MERCADO LIBRE

INSTRUCCIONES:
1. Copiá las funciones de MERCADO LIBRE al final de tu app.py (antes del if __name__ == '__main__')
2. Copiá las rutas nuevas donde están las otras rutas de ventas
3. Guardá tu ACCESS_TOKEN en config/ml_token.json
"""

# ============================================================================
# AGREGAR ESTAS IMPORTS AL PRINCIPIO DE TU app.py (junto con los otros imports)
# ============================================================================
import requests  # pip install requests

# ============================================================================
# FUNCIONES AUXILIARES: MERCADO LIBRE
# Agregar ANTES del if __name__ == '__main__' al final de app.py
# ============================================================================

def cargar_ml_token():
    """Cargar ACCESS_TOKEN desde config/ml_token.json"""
    try:
        token_path = 'config/ml_token.json'
        if os.path.exists(token_path):
            with open(token_path, 'r') as f:
                data = json.load(f)
                return data.get('access_token')
        return None
    except Exception as e:
        print(f"Error cargando token ML: {e}")
        return None


def guardar_ml_token(token_data):
    """Guardar datos del token en config/ml_token.json"""
    try:
        os.makedirs('config', exist_ok=True)
        with open('config/ml_token.json', 'w') as f:
            json.dump(token_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error guardando token ML: {e}")
        return False


def obtener_ordenes_ml(access_token, limit=20):
    """
    Obtener órdenes de Mercado Libre
    Retorna: (success, data_o_error)
    """
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        # 1. Obtener USER_ID
        user_response = requests.get('https://api.mercadolibre.com/users/me', headers=headers)
        
        if user_response.status_code != 200:
            return False, f"Error obteniendo usuario: {user_response.status_code}"
        
        user_id = user_response.json()['id']
        
        # 2. Buscar órdenes como vendedor
        orders_url = f"https://api.mercadolibre.com/orders/search?seller={user_id}&sort=date_desc&limit={limit}"
        orders_response = requests.get(orders_url, headers=headers)
        
        if orders_response.status_code != 200:
            return False, f"Error obteniendo órdenes: {orders_response.status_code}"
        
        orders_data = orders_response.json()
        return True, orders_data['results']
        
    except Exception as e:
        return False, str(e)


def procesar_orden_ml(orden):
    """
    Procesar una orden de ML y extraer datos relevantes
    Retorna diccionario con datos formateados
    """
    # Fecha
    fecha = datetime.fromisoformat(orden['date_created'].replace('Z', '+00:00'))
    
    # Items/Productos
    items = []
    for item in orden['order_items']:
        items.append({
            'sku': item['item'].get('seller_sku', ''),
            'titulo': item['item']['title'],
            'cantidad': item['quantity'],
            'precio': item['unit_price']
        })
    
    # Comprador
    buyer = orden.get('buyer', {})
    comprador_nombre = f"{buyer.get('first_name', '')} {buyer.get('last_name', '')}".strip()
    comprador_nickname = buyer.get('nickname', '')
    
    # Total
    total = orden['total_amount']
    
    # Estado
    estado = orden['status']
    
    # Shipping
    shipping_id = orden.get('shipping', {}).get('id', '')
    
    return {
        'id': orden['id'],
        'fecha': fecha,
        'comprador_nombre': comprador_nombre,
        'comprador_nickname': comprador_nickname,
        'items': items,
        'total': total,
        'estado': estado,
        'shipping_id': shipping_id
    }


def verificar_sku_en_bd(sku):
    """
    Verificar si un SKU existe en la base de datos
    Retorna: (existe, tipo_producto, nombre)
    """
    # Buscar en productos_base
    prod = query_one('SELECT tipo, nombre FROM productos_base WHERE sku = %s', (sku,))
    if prod:
        return True, prod['tipo'], prod['nombre']
    
    # Buscar en productos_compuestos
    combo = query_one('SELECT nombre FROM productos_compuestos WHERE sku = %s', (sku,))
    if combo:
        return True, 'combo', combo['nombre']
    
    return False, None, None


# ============================================================================
# RUTAS: MERCADO LIBRE
# Agregar DESPUÉS de la ruta /ventas/activas en app.py
# ============================================================================

@app.route('/ventas/ml/configurar_token', methods=['GET', 'POST'])
def ml_configurar_token():
    """Página para configurar/actualizar el ACCESS_TOKEN de Mercado Libre"""
    if request.method == 'POST':
        access_token = request.form.get('access_token', '').strip()
        
        if not access_token:
            flash('❌ Debes ingresar un ACCESS_TOKEN', 'error')
            return redirect(url_for('ml_configurar_token'))
        
        # Guardar token
        token_data = {
            'access_token': access_token,
            'fecha_configuracion': datetime.now().isoformat()
        }
        
        if guardar_ml_token(token_data):
            flash('✅ Token configurado correctamente', 'success')
            return redirect(url_for('ventas_activas'))
        else:
            flash('❌ Error al guardar token', 'error')
    
    # Verificar si ya hay token
    token_actual = cargar_ml_token()
    
    return render_template('ml_configurar_token.html', token_actual=token_actual)


@app.route('/ventas/ml/importar')
def ml_importar_ordenes():
    """
    Traer órdenes de Mercado Libre y mostrarlas para seleccionar
    """
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay ACCESS_TOKEN configurado. Configuralo primero.', 'error')
        return redirect(url_for('ml_configurar_token'))
    
    # Obtener órdenes de ML
    success, result = obtener_ordenes_ml(access_token, limit=30)
    
    if not success:
        flash(f'❌ Error al obtener órdenes de ML: {result}', 'error')
        return redirect(url_for('ventas_activas'))
    
    # Procesar órdenes
    ordenes_procesadas = []
    for orden in result:
        # Solo mostrar órdenes pagadas y no canceladas
        if orden['status'] in ['paid']:
            orden_data = procesar_orden_ml(orden)
            
            # Verificar SKU en BD
            for item in orden_data['items']:
                sku = item['sku']
                if sku:
                    existe, tipo, nombre = verificar_sku_en_bd(sku)
                    item['existe_en_bd'] = existe
                    item['tipo_producto'] = tipo
                    item['nombre_bd'] = nombre
                else:
                    item['existe_en_bd'] = False
                    item['tipo_producto'] = None
                    item['nombre_bd'] = None
            
            ordenes_procesadas.append(orden_data)
    
    return render_template('ml_importar_ordenes.html', ordenes=ordenes_procesadas)


@app.route('/ventas/ml/seleccionar/<orden_id>')
def ml_seleccionar_orden(orden_id):
    """
    Seleccionar una orden de ML y preparar datos para nueva venta
    """
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay ACCESS_TOKEN configurado', 'error')
        return redirect(url_for('ml_configurar_token'))
    
    # Obtener orden específica
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f'https://api.mercadolibre.com/orders/{orden_id}', headers=headers)
        
        if response.status_code != 200:
            flash('❌ Error al obtener orden de ML', 'error')
            return redirect(url_for('ventas_activas'))
        
        orden = response.json()
        orden_data = procesar_orden_ml(orden)
        
        # Verificar mapeo de SKU
        items_sin_mapear = []
        items_mapeados = []
        
        for item in orden_data['items']:
            sku = item['sku']
            if sku:
                existe, tipo, nombre = verificar_sku_en_bd(sku)
                if existe:
                    items_mapeados.append({
                        'sku_ml': sku,
                        'sku_bd': sku,
                        'titulo': item['titulo'],
                        'cantidad': item['cantidad'],
                        'precio': item['precio'],
                        'nombre_bd': nombre
                    })
                else:
                    items_sin_mapear.append(item)
            else:
                items_sin_mapear.append(item)
        
        # Si hay items sin mapear, mostrar página de mapeo
        if items_sin_mapear:
            # Obtener todos los productos disponibles para mapear
            productos_bd = query_db('SELECT sku, nombre, tipo FROM productos_base ORDER BY nombre')
            combos_bd = query_db('SELECT sku, nombre FROM productos_compuestos ORDER BY nombre')
            
            return render_template('ml_mapear_productos.html',
                                 orden_id=orden_id,
                                 items_sin_mapear=items_sin_mapear,
                                 items_mapeados=items_mapeados,
                                 productos_bd=productos_bd,
                                 combos_bd=combos_bd,
                                 orden_data=orden_data)
        
        # Si todos están mapeados, redirigir a nueva venta con datos precargados
        return redirect(url_for('nueva_venta_ml',
                              orden_id=orden_id,
                              items=json.dumps(items_mapeados),
                              cliente=orden_data['comprador_nombre'],
                              mla_code=orden_data['comprador_nickname'],
                              total=orden_data['total']))
        
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'error')
        return redirect(url_for('ventas_activas'))


@app.route('/ventas/ml/mapear', methods=['POST'])
def ml_guardar_mapeo():
    """
    Guardar mapeo de productos ML → BD y continuar a nueva venta
    """
    orden_id = request.form.get('orden_id')
    
    # Items ya mapeados (vienen como JSON)
    items_mapeados = json.loads(request.form.get('items_mapeados', '[]'))
    
    # Items que se mapearon ahora
    items_form = request.form.getlist('item_sku_ml')
    
    for i, sku_ml in enumerate(items_form):
        sku_bd = request.form.get(f'mapeo_{i}')
        titulo = request.form.get(f'titulo_{i}')
        cantidad = int(request.form.get(f'cantidad_{i}'))
        precio = float(request.form.get(f'precio_{i}'))
        
        if sku_bd:
            # Verificar que existe en BD
            existe, tipo, nombre = verificar_sku_en_bd(sku_bd)
            if existe:
                items_mapeados.append({
                    'sku_ml': sku_ml,
                    'sku_bd': sku_bd,
                    'titulo': titulo,
                    'cantidad': cantidad,
                    'precio': precio,
                    'nombre_bd': nombre
                })
    
    # Guardar en sesión para usarlo en nueva venta
    from flask import session
    session['ml_orden_id'] = orden_id
    session['ml_items'] = items_mapeados
    
    flash('✅ Productos mapeados correctamente', 'success')
    return redirect(url_for('nueva_venta_desde_ml'))


@app.route('/ventas/nueva/ml')
def nueva_venta_desde_ml():
    """
    Crear nueva venta con datos precargados desde ML
    """
    from flask import session
    
    if 'ml_items' not in session:
        flash('❌ No hay datos de ML para importar', 'error')
        return redirect(url_for('ventas_activas'))
    
    ml_items = session.get('ml_items', [])
    ml_orden_id = session.get('ml_orden_id', '')
    
    # Limpiar sesión
    session.pop('ml_items', None)
    session.pop('ml_orden_id', None)
    
    # Obtener datos necesarios para el formulario
    productos = query_db('SELECT * FROM productos_base ORDER BY nombre')
    combos = query_db('SELECT * FROM productos_compuestos ORDER BY nombre')
    
    return render_template('nueva_venta_ml.html',
                         productos=productos,
                         combos=combos,
                         ml_items=ml_items,
                         ml_orden_id=ml_orden_id)


# ============================================================================
# FIN DE CÓDIGO NUEVO
# ============================================================================
