# ============================================================================
# ESTRATEGIA OPTIMIZADA
# ============================================================================
# 
# PROBLEMA: Hacer request a /shipments/{id} para cada orden al listar = LENTO
# SOLUCIÓN: Solo obtener datos de shipping cuando el usuario SELECCIONA una orden
#
# ============================================================================

# ===== FUNCIÓN 1: procesar_orden_ml (SIN obtener shipping) =====
def procesar_orden_ml_simple(orden):
    """
    Procesar orden de ML SIN obtener detalles de shipping
    Usar al LISTAR órdenes (más rápido)
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
    
    # Shipping (solo ID, sin detalles)
    shipping = orden.get('shipping', {})
    shipping_id = shipping.get('id', '')
    
    shipping_data = {
        'tiene_envio': bool(shipping_id),
        'shipping_id': shipping_id,
        'metodo_envio': '',
        'direccion': '',
        'ciudad': '',
        'provincia': '',
        'codigo_postal': '',
        'zona': ''
    }
    
    return {
        'id': orden['id'],
        'fecha': fecha,
        'comprador_nombre': comprador_nombre,
        'comprador_nickname': comprador_nickname,
        'items': items,
        'total': total,
        'estado': estado,
        'shipping': shipping_data
    }


# ===== FUNCIÓN 2: obtener_shipping_completo (nueva) =====
def obtener_shipping_completo(shipping_id, access_token):
    """
    Obtener detalles completos de shipping desde ML
    Usar solo cuando se SELECCIONA una orden específica
    """
    shipping_data = {
        'tiene_envio': True,
        'shipping_id': shipping_id,
        'metodo_envio': '',
        'direccion': '',
        'ciudad': '',
        'provincia': '',
        'codigo_postal': '',
        'zona': ''
    }
    
    if not shipping_id or not access_token:
        return shipping_data
    
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f'https://api.mercadolibre.com/shipments/{shipping_id}', headers=headers)
        
        if response.status_code != 200:
            print(f"⚠️ Error al obtener shipment {shipping_id}: {response.status_code}")
            return shipping_data
        
        shipment = response.json()
        
        # Método de envío
        shipping_mode = shipment.get('shipping_option', {}).get('shipping_method_id', '')
        logistic_type = shipment.get('logistic_type', '')
        
        if logistic_type == 'fulfillment':
            shipping_data['metodo_envio'] = 'Full'
        elif logistic_type == 'cross_docking':
            shipping_data['metodo_envio'] = 'Flex'
        elif 'mercadoenvios' in str(shipping_mode).lower():
            shipping_data['metodo_envio'] = 'Mercadoenvios'
        else:
            shipping_data['metodo_envio'] = 'Mercadoenvios'
        
        # Dirección
        receiver_address = shipment.get('receiver_address', {})
        
        if receiver_address:
            # Dirección completa
            address_line = receiver_address.get('address_line', '')
            street_name = receiver_address.get('street_name', '')
            street_number = receiver_address.get('street_number', '')
            floor = receiver_address.get('floor', '')
            apartment = receiver_address.get('apartment', '')
            
            if address_line:
                shipping_data['direccion'] = address_line
            elif street_name and street_number:
                direccion = f"{street_name} {street_number}"
                if floor:
                    direccion += f" Piso {floor}"
                if apartment:
                    direccion += f" Depto {apartment}"
                shipping_data['direccion'] = direccion
            
            # Ciudad y provincia (CONVERTIR A STRING)
            city = receiver_address.get('city', {})
            state = receiver_address.get('state', {})
            
            # 🔧 ARREGLO: Convertir a string antes de usar
            if isinstance(city, dict):
                shipping_data['ciudad'] = str(city.get('name', ''))
            else:
                shipping_data['ciudad'] = str(city) if city else ''
            
            if isinstance(state, dict):
                shipping_data['provincia'] = str(state.get('name', ''))
            else:
                shipping_data['provincia'] = str(state) if state else ''
            
            shipping_data['codigo_postal'] = str(receiver_address.get('zip_code', ''))
            
            # Inferir zona
            ciudad_lower = shipping_data['ciudad'].lower()
            provincia_lower = shipping_data['provincia'].lower()
            
            if 'capital federal' in ciudad_lower or 'ciudad' in ciudad_lower or 'caba' in ciudad_lower or 'autonoma' in provincia_lower:
                shipping_data['zona'] = 'Capital'
            elif any(x in ciudad_lower for x in ['plata', 'quilmes', 'avellaneda', 'berazategui', 'florencio varela', 'lanus']):
                shipping_data['zona'] = 'Sur'
            elif any(x in ciudad_lower for x in ['san isidro', 'tigre', 'pilar', 'escobar', 'san fernando']):
                shipping_data['zona'] = 'Norte-Noroeste'
            elif any(x in ciudad_lower for x in ['moron', 'merlo', 'ituzaingo', 'hurlingham', 'moreno']):
                shipping_data['zona'] = 'Oeste'
    
    except Exception as e:
        print(f"⚠️ Error al procesar shipping {shipping_id}: {str(e)}")
    
    return shipping_data


# ===== FUNCIÓN 3: ml_importar_ordenes (OPTIMIZADA) =====
@app.route('/ventas/ml/importar')
def ml_importar_ordenes():
    """
    Traer órdenes de ML - OPTIMIZADO
    NO obtiene detalles de shipping (más rápido)
    """
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay ACCESS_TOKEN configurado. Configuralo primero.', 'error')
        return redirect(url_for('ml_configurar_token'))
    
    # Obtener órdenes de ML
    success, result = obtener_ordenes_ml(access_token, limit=50)
    
    if not success:
        flash(f'❌ Error al obtener órdenes de ML: {result}', 'error')
        return redirect(url_for('ventas_activas'))
    
    # Obtener IDs de órdenes ya importadas
    ordenes_importadas = set()
    try:
        ventas_ml = query_db("SELECT numero_venta FROM ventas WHERE numero_venta LIKE 'ML-%'")
        for venta in ventas_ml:
            # Extraer solo el número después de "ML-"
            numero = venta['numero_venta'].replace('ML-', '').strip()
            ordenes_importadas.add(numero)
        
        print(f"📊 Órdenes ya importadas: {len(ordenes_importadas)}")
        if ordenes_importadas:
            print(f"   Ejemplos: {list(ordenes_importadas)[:5]}")
    except Exception as e:
        print(f"⚠️ Error al obtener órdenes importadas: {e}")
    
    # Procesar órdenes
    ordenes_procesadas = []
    for orden in result:
        # Verificar si ya fue importada
        orden_id = str(orden['id'])
        
        if orden_id in ordenes_importadas:
            print(f"⏭️ Orden {orden_id} ya importada, saltando...")
            continue
        
        # Solo mostrar órdenes pagadas
        if orden['status'] in ['paid']:
            # 🔧 OPTIMIZACIÓN: Usar versión simple (sin shipping)
            orden_data = procesar_orden_ml_simple(orden)
            
            # Verificar SKU
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
    
    print(f"✅ Órdenes a mostrar: {len(ordenes_procesadas)}")
    
    return render_template('ml_importar_ordenes.html', ordenes=ordenes_procesadas)


# ===== FUNCIÓN 4: ml_seleccionar_orden (CON shipping completo) =====
@app.route('/ventas/ml/seleccionar/<orden_id>')
def ml_seleccionar_orden(orden_id):
    """
    Seleccionar orden - AQUÍ SÍ obtiene shipping completo
    """
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay ACCESS_TOKEN configurado', 'error')
        return redirect(url_for('ml_configurar_token'))
    
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f'https://api.mercadolibre.com/orders/{orden_id}', headers=headers)
        
        if response.status_code != 200:
            flash('❌ Error al obtener orden de ML', 'error')
            return redirect(url_for('ventas_activas'))
        
        orden = response.json()
        
        # Procesar orden (básico)
        orden_data = procesar_orden_ml_simple(orden)
        
        # 🔧 OBTENER SHIPPING COMPLETO solo para esta orden
        if orden_data['shipping']['shipping_id']:
            shipping_completo = obtener_shipping_completo(
                orden_data['shipping']['shipping_id'],
                access_token
            )
            orden_data['shipping'] = shipping_completo
        
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
        
        # Mapeo
        if items_sin_mapear:
            productos_bd = query_db('SELECT sku, nombre, tipo FROM productos_base ORDER BY nombre')
            combos_bd = query_db('SELECT sku, nombre FROM productos_compuestos ORDER BY nombre')
            
            return render_template('ml_mapear_productos.html',
                                 orden_id=orden_id,
                                 items_sin_mapear=items_sin_mapear,
                                 items_mapeados=items_mapeados,
                                 productos_bd=productos_bd,
                                 combos_bd=combos_bd,
                                 orden_data=orden_data)
        
        # Guardar en sesión
        from flask import session
        session['ml_orden_id'] = orden_id
        session['ml_items'] = items_mapeados
        session['ml_comprador_nombre'] = orden_data['comprador_nombre']
        session['ml_comprador_nickname'] = orden_data['comprador_nickname']
        session['ml_shipping'] = orden_data['shipping']
        
        flash('✅ Productos mapeados correctamente', 'success')
        return redirect(url_for('nueva_venta_desde_ml'))
        
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ventas_activas'))


# ===== FUNCIÓN 5: ml_guardar_mapeo (CON shipping completo) =====
@app.route('/ventas/ml/mapear', methods=['POST'])
def ml_guardar_mapeo():
    """
    Guardar mapeo - Obtiene shipping completo
    """
    orden_id = request.form.get('orden_id')
    items_mapeados = json.loads(request.form.get('items_mapeados', '[]'))
    items_form = request.form.getlist('item_sku_ml')
    
    for i, sku_ml in enumerate(items_form):
        sku_bd = request.form.get(f'mapeo_{i}')
        titulo = request.form.get(f'titulo_{i}')
        cantidad = int(request.form.get(f'cantidad_{i}'))
        precio = float(request.form.get(f'precio_{i}'))
        
        if sku_bd:
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
    
    access_token = cargar_ml_token()
    
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f'https://api.mercadolibre.com/orders/{orden_id}', headers=headers)
        
        if response.status_code == 200:
            orden = response.json()
            orden_data = procesar_orden_ml_simple(orden)
            
            # 🔧 OBTENER SHIPPING COMPLETO
            if orden_data['shipping']['shipping_id']:
                shipping_completo = obtener_shipping_completo(
                    orden_data['shipping']['shipping_id'],
                    access_token
                )
                orden_data['shipping'] = shipping_completo
            
            from flask import session
            session['ml_orden_id'] = orden_id
            session['ml_items'] = items_mapeados
            session['ml_comprador_nombre'] = orden_data['comprador_nombre']
            session['ml_comprador_nickname'] = orden_data['comprador_nickname']
            session['ml_shipping'] = orden_data['shipping']
        else:
            from flask import session
            session['ml_orden_id'] = orden_id
            session['ml_items'] = items_mapeados
            session['ml_comprador_nombre'] = ''
            session['ml_comprador_nickname'] = ''
            session['ml_shipping'] = {}
    
    except Exception as e:
        from flask import session
        session['ml_orden_id'] = orden_id
        session['ml_items'] = items_mapeados
        session['ml_comprador_nombre'] = ''
        session['ml_comprador_nickname'] = ''
        session['ml_shipping'] = {}
        import traceback
        traceback.print_exc()
    
    flash('✅ Productos mapeados correctamente', 'success')
    return redirect(url_for('nueva_venta_desde_ml'))
