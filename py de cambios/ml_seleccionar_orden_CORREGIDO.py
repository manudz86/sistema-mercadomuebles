@app.route('/ventas/ml/seleccionar/<orden_id>')
def ml_seleccionar_orden(orden_id):
    """
    Seleccionar orden - Con normalización automática de SKU (quita Z)
    GUARDA FECHA REAL DE VENTA Y DATOS DE FACTURACIÓN EN SESIÓN
    ✅ CORREGIDO: No sobrescribe costo_envio (ya viene del shipment)
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
        orden_data = procesar_orden_ml(orden)
        
        # OBTENER SHIPPING COMPLETO
        if orden_data['shipping']['shipping_id']:
            shipping_completo = obtener_shipping_completo(
                orden_data['shipping']['shipping_id'],
                access_token
            )
            # ✅ CORREGIDO: Ya no sobrescribimos costo_envio
            # porque obtener_shipping_completo() ya lo captura del shipment
            orden_data['shipping'] = shipping_completo
        
        # ✅ NUEVO: OBTENER BILLING INFO (FACTURACIÓN)
        billing_data = None
        try:
            billing_response = requests.get(
                f'https://api.mercadolibre.com/orders/{orden_id}/billing_info',
                headers=headers
            )
            
            if billing_response.status_code == 200:
                billing_data = billing_response.json()
                print(f"✅ Billing info obtenida para orden {orden_id}")
            else:
                print(f"ℹ️ No hay billing info para orden {orden_id} (Consumidor Final)")
        
        except Exception as e:
            print(f"⚠️ Error al obtener billing info: {str(e)}")
        
        # Verificar mapeo de SKU CON NORMALIZACIÓN AUTOMÁTICA
        items_sin_mapear = []
        items_mapeados = []
        
        for item in orden_data['items']:
            sku_ml_original = item['sku']
            if sku_ml_original:
                existe, tipo, nombre = verificar_sku_en_bd(sku_ml_original)
                sku_a_usar = sku_ml_original
                
                if not existe and sku_ml_original.endswith('Z'):
                    sku_normalizado = sku_ml_original[:-1]
                    existe, tipo, nombre = verificar_sku_en_bd(sku_normalizado)
                    if existe:
                        sku_a_usar = sku_normalizado
                        print(f"✅ Mapeo automático: {sku_ml_original} → {sku_normalizado}")
                
                if existe:
                    items_mapeados.append({
                        'sku_ml': sku_ml_original,
                        'sku_bd': sku_a_usar,
                        'titulo': item['titulo'],
                        'cantidad': item['cantidad'],
                        'precio': item['precio'],
                        'nombre_bd': nombre
                    })
                else:
                    items_sin_mapear.append(item)
            else:
                items_sin_mapear.append(item)
        
        # Mapeo manual si hay productos sin mapear
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
        
        # ✅ GUARDAR EN SESIÓN CON FECHA REAL DE ML Y BILLING INFO
        from flask import session
        session['ml_orden_id'] = orden_id
        session['ml_items'] = items_mapeados
        session['ml_comprador_nombre'] = orden_data['comprador_nombre']
        session['ml_comprador_nickname'] = orden_data['comprador_nickname']
        session['ml_shipping'] = orden_data['shipping']
        session['ml_fecha_venta'] = orden_data['fecha'].isoformat()
        
        # ✅ NUEVO: Guardar billing info en sesión
        if billing_data:
            session['ml_billing_data'] = billing_data
        else:
            session['ml_billing_data'] = None
        
        flash('✅ Productos mapeados correctamente', 'success')
        return redirect(url_for('nueva_venta_desde_ml'))
        
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ventas_activas'))
