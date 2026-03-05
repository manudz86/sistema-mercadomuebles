# ============================================================================
# ACTUALIZAR ESTAS FUNCIONES EN app.py
# Ahora pasan access_token a procesar_orden_ml
# ============================================================================

# ===== FUNCIÓN 1: ml_importar_ordenes =====
@app.route('/ventas/ml/importar')
def ml_importar_ordenes():
    """
    Traer órdenes de Mercado Libre y mostrarlas para seleccionar
    NO muestra órdenes ya importadas
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
            orden_id = venta['numero_venta'].replace('ML-', '')
            ordenes_importadas.add(orden_id)
    except Exception as e:
        print(f"Error al obtener órdenes importadas: {e}")
    
    # Procesar órdenes
    ordenes_procesadas = []
    for orden in result:
        # Verificar si ya fue importada
        orden_id = str(orden['id'])
        if orden_id in ordenes_importadas:
            continue
        
        # Solo mostrar órdenes pagadas
        if orden['status'] in ['paid']:
            # 🔧 CAMBIO: Pasar access_token
            orden_data = procesar_orden_ml(orden, access_token)
            
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


# ===== FUNCIÓN 2: ml_seleccionar_orden =====
@app.route('/ventas/ml/seleccionar/<orden_id>')
def ml_seleccionar_orden(orden_id):
    """
    Seleccionar una orden de ML y preparar datos para nueva venta
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
        # 🔧 CAMBIO: Pasar access_token
        orden_data = procesar_orden_ml(orden, access_token)
        
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
            productos_bd = query_db('SELECT sku, nombre, tipo FROM productos_base ORDER BY nombre')
            combos_bd = query_db('SELECT sku, nombre FROM productos_compuestos ORDER BY nombre')
            
            return render_template('ml_mapear_productos.html',
                                 orden_id=orden_id,
                                 items_sin_mapear=items_sin_mapear,
                                 items_mapeados=items_mapeados,
                                 productos_bd=productos_bd,
                                 combos_bd=combos_bd,
                                 orden_data=orden_data)
        
        # Si todos están mapeados, guardar en sesión
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
        return redirect(url_for('ventas_activas'))


# ===== FUNCIÓN 3: ml_guardar_mapeo =====
@app.route('/ventas/ml/mapear', methods=['POST'])
def ml_guardar_mapeo():
    """
    Guardar mapeo de productos ML → BD y continuar a nueva venta
    """
    orden_id = request.form.get('orden_id')
    
    # Items ya mapeados
    items_mapeados = json.loads(request.form.get('items_mapeados', '[]'))
    
    # Items que se mapearon ahora
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
    
    # Obtener datos completos de la orden
    access_token = cargar_ml_token()
    
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f'https://api.mercadolibre.com/orders/{orden_id}', headers=headers)
        
        if response.status_code == 200:
            orden = response.json()
            # 🔧 CAMBIO: Pasar access_token
            orden_data = procesar_orden_ml(orden, access_token)
            
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
    
    flash('✅ Productos mapeados correctamente', 'success')
    return redirect(url_for('nueva_venta_desde_ml'))
