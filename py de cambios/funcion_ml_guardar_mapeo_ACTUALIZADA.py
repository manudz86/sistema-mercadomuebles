# ============================================================================
# REEMPLAZAR la función ml_guardar_mapeo en app.py
# ============================================================================

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
    
    # Obtener datos del comprador Y ENVÍO de la orden
    access_token = cargar_ml_token()
    
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f'https://api.mercadolibre.com/orders/{orden_id}', headers=headers)
        
        if response.status_code == 200:
            orden = response.json()
            orden_data = procesar_orden_ml(orden)
            
            # Guardar en sesión TODO (items + datos del comprador + shipping)
            from flask import session
            session['ml_orden_id'] = orden_id
            session['ml_items'] = items_mapeados
            session['ml_comprador_nombre'] = orden_data['comprador_nombre']
            session['ml_comprador_nickname'] = orden_data['comprador_nickname']
            session['ml_shipping'] = orden_data['shipping']  # ✨ NUEVO
        else:
            # Si falla, solo guardar items
            from flask import session
            session['ml_orden_id'] = orden_id
            session['ml_items'] = items_mapeados
            session['ml_comprador_nombre'] = ''
            session['ml_comprador_nickname'] = ''
            session['ml_shipping'] = {}  # ✨ NUEVO (vacío)
    
    except Exception as e:
        # Si hay error, solo guardar items
        from flask import session
        session['ml_orden_id'] = orden_id
        session['ml_items'] = items_mapeados
        session['ml_comprador_nombre'] = ''
        session['ml_comprador_nickname'] = ''
        session['ml_shipping'] = {}  # ✨ NUEVO (vacío)
    
    flash('✅ Productos mapeados correctamente', 'success')
    return redirect(url_for('nueva_venta_desde_ml'))
