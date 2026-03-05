# ============================================================================
# FUNCIÓN AUXILIAR: EXTRAER DATOS DE BILLING_INFO
# Agregar en app.py después de las funciones de ML
# ============================================================================

def extraer_billing_info_ml(billing_data):
    """
    Extraer datos de facturación del formato de ML
    
    ML devuelve los datos en formato:
    {
      "billing_info": {
        "additional_info": [
          {"type": "BUSINESS_NAME", "value": "FERNANDEZ GONZALO JAVIER"},
          {"type": "DOC_TYPE", "value": "CUIT"},
          ...
        ]
      }
    }
    
    Returns:
        dict con los datos extraídos
    """
    datos = {
        'business_name': None,
        'doc_type': None,
        'doc_number': None,
        'taxpayer_type': None,
        'city': None,
        'street': None,
        'state': None,
        'zip_code': None
    }
    
    try:
        # Obtener billing_info
        billing_info = billing_data.get('billing_info', {})
        
        # Doc type y number están en el nivel principal
        datos['doc_type'] = billing_info.get('doc_type')
        datos['doc_number'] = billing_info.get('doc_number')
        
        # Los demás datos están en additional_info
        additional_info = billing_info.get('additional_info', [])
        
        # Crear diccionario para búsqueda fácil
        info_dict = {}
        for item in additional_info:
            tipo = item.get('type')
            valor = item.get('value')
            if tipo and valor:
                info_dict[tipo] = valor
        
        # Extraer campos
        datos['business_name'] = info_dict.get('BUSINESS_NAME')
        datos['taxpayer_type'] = info_dict.get('TAXPAYER_TYPE_ID')
        datos['city'] = info_dict.get('CITY_NAME')
        datos['street'] = info_dict.get('STREET_NAME')
        datos['state'] = info_dict.get('STATE_NAME')
        datos['zip_code'] = info_dict.get('ZIP_CODE')
        
        # Si no hay doc_type en el nivel principal, intentar de additional_info
        if not datos['doc_type']:
            datos['doc_type'] = info_dict.get('DOC_TYPE')
        if not datos['doc_number']:
            datos['doc_number'] = info_dict.get('DOC_NUMBER')
        
        print(f"✅ Datos de facturación extraídos:")
        print(f"   • Razón social: {datos['business_name']}")
        print(f"   • {datos['doc_type']}: {datos['doc_number']}")
        print(f"   • Condición IVA: {datos['taxpayer_type']}")
        
    except Exception as e:
        print(f"⚠️ Error al extraer billing_info: {str(e)}")
    
    return datos


# ============================================================================
# ACTUALIZAR FUNCIÓN: ml_seleccionar_orden
# REEMPLAZAR LA FUNCIÓN COMPLETA en app.py
# ============================================================================

@app.route('/ventas/ml/seleccionar/<orden_id>')
def ml_seleccionar_orden(orden_id):
    """
    Seleccionar orden - Con normalización automática de SKU (quita Z)
    GUARDA FECHA REAL DE VENTA Y DATOS DE FACTURACIÓN EN SESIÓN
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
            shipping_completo['costo_envio'] = orden_data['shipping']['costo_envio']
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


# ============================================================================
# ACTUALIZAR FUNCIÓN: ml_guardar_mapeo
# REEMPLAZAR LA FUNCIÓN COMPLETA en app.py
# ============================================================================

@app.route('/ventas/ml/mapear', methods=['POST'])
def ml_guardar_mapeo():
    """
    Guardar mapeo - Obtiene shipping completo y billing info
    Con normalización automática de SKU (quita Z)
    GUARDA FECHA REAL DE VENTA Y DATOS DE FACTURACIÓN EN SESIÓN
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
                shipping_completo['costo_envio'] = orden_data['shipping']['costo_envio']
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
