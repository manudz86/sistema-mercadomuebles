@app.route('/ventas/ml/mapear', methods=['POST'])
def ml_guardar_mapeo():
    """
    Guardar mapeo - Obtiene shipping completo y billing info
    Con normalización automática de SKU (quita Z)
    GUARDA FECHA REAL DE VENTA Y DATOS DE FACTURACIÓN EN SESIÓN
    ✅ CORREGIDO: No sobrescribe costo_envio
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
            orden_data = procesar_orden_ml(orden)
            
            # OBTENER SHIPPING COMPLETO
            if orden_data['shipping']['shipping_id']:
                shipping_completo = obtener_shipping_completo(
                    orden_data['shipping']['shipping_id'],
                    access_token
                )
                # ✅ CORREGIDO: Ya no sobrescribimos costo_envio
                orden_data['shipping'] = shipping_completo
            
            # ✅ NUEVO: OBTENER BILLING INFO
            billing_data = None
            try:
                billing_response = requests.get(
                    f'https://api.mercadolibre.com/orders/{orden_id}/billing_info',
                    headers=headers
                )
                
                if billing_response.status_code == 200:
                    billing_data = billing_response.json()
            except:
                pass
            
            # ✅ GUARDAR EN SESIÓN CON FECHA REAL Y BILLING
            from flask import session
            session['ml_orden_id'] = orden_id
            session['ml_items'] = items_mapeados
            session['ml_comprador_nombre'] = orden_data['comprador_nombre']
            session['ml_comprador_nickname'] = orden_data['comprador_nickname']
            session['ml_shipping'] = orden_data['shipping']
            session['ml_fecha_venta'] = orden_data['fecha'].isoformat()
            session['ml_billing_data'] = billing_data
        else:
            from flask import session
            session['ml_orden_id'] = orden_id
            session['ml_items'] = items_mapeados
            session['ml_comprador_nombre'] = ''
            session['ml_comprador_nickname'] = ''
            session['ml_shipping'] = {}
            session['ml_fecha_venta'] = datetime.now().isoformat()
            session['ml_billing_data'] = None
    
    except Exception as e:
        from flask import session
        session['ml_orden_id'] = orden_id
        session['ml_items'] = items_mapeados
        session['ml_comprador_nombre'] = ''
        session['ml_comprador_nickname'] = ''
        session['ml_shipping'] = {}
        session['ml_fecha_venta'] = datetime.now().isoformat()
        session['ml_billing_data'] = None
        import traceback
        traceback.print_exc()
    
    flash('✅ Productos mapeados correctamente', 'success')
    return redirect(url_for('nueva_venta_desde_ml'))
