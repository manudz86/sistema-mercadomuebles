# ============================================================================
# RUTAS CARGAR STOCK - ACTUALIZADAS CON REFRESH DE DATOS ML
# ============================================================================

@app.route('/cargar-stock-mla', methods=['POST'])
def cargar_stock_mla():
    """Cargar stock en una publicación específica"""
    
    mla = request.form.get('mla')
    sku = request.form.get('sku')
    stock_nuevo = request.form.get('stock_nuevo')
    
    if not mla or not sku or not stock_nuevo:
        flash('Faltan datos', 'danger')
        return redirect(url_for('cargar_stock_ml'))
    
    # Obtener token dinámico
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('cargar_stock_ml'))
    
    try:
        stock_nuevo = int(stock_nuevo)
        
        # Usar la función helper actualizar_stock_ml
        success, message = actualizar_stock_ml(mla, stock_nuevo, access_token)
        
        if success:
            flash(f'✅ {message}', 'success')
        else:
            flash(f'❌ {message}', 'danger')
    
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    
    # Volver a mostrar resultados CON DATOS ACTUALIZADOS DE ML
    publicaciones = query_db(
        "SELECT mla_id, titulo_ml, activo FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE",
        (sku,)
    )
    
    pubs_lista = []
    access_token_refresh = cargar_ml_token()
    
    for row in publicaciones:
        if access_token_refresh:
            datos_ml = obtener_datos_ml(row['mla_id'], access_token_refresh)
            pubs_lista.append({
                'mla': row['mla_id'],
                'titulo': datos_ml['titulo'],
                'stock_actual': datos_ml['stock'],
                'demora': datos_ml.get('demora'),
                'estado': 'Activa' if row['activo'] else 'Pausada'
            })
        else:
            pubs_lista.append({
                'mla': row['mla_id'],
                'titulo': row['titulo_ml'] or 'Sin título',
                'stock_actual': '-',
                'demora': None,
                'estado': 'Activa' if row['activo'] else 'Pausada'
            })
    
    return render_template('cargar_stock_ml.html',
                         sku_buscado=sku,
                         publicaciones=pubs_lista,
                         es_sku_con_z=sku.endswith('Z'))


@app.route('/cargar-stock-masivo', methods=['POST'])
def cargar_stock_masivo():
    """Cargar el mismo stock en todas las publicaciones de un SKU"""
    
    sku = request.form.get('sku')
    stock_nuevo = request.form.get('stock_nuevo')
    
    if not sku or not stock_nuevo:
        flash('Faltan datos', 'danger')
        return redirect(url_for('cargar_stock_ml'))
    
    # Obtener token dinámico
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('cargar_stock_ml'))
    
    try:
        stock_nuevo = int(stock_nuevo)
        
        # Obtener todas las publicaciones del SKU
        mlas = query_db(
            "SELECT mla_id FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE",
            (sku,)
        )
        
        exitos = 0
        errores = 0
        mensajes_error = []
        
        for row in mlas:
            mla = row['mla_id']
            
            # Usar la función helper actualizar_stock_ml
            success, message = actualizar_stock_ml(mla, stock_nuevo, access_token)
            
            if success:
                exitos += 1
            else:
                errores += 1
                mensajes_error.append(f"{mla}: {message}")
        
        if exitos > 0:
            flash(f'✅ Stock cargado en {exitos} publicaciones: {stock_nuevo} unidades', 'success')
        if errores > 0:
            flash(f'⚠️ {errores} publicaciones con errores', 'warning')
            if mensajes_error:
                for msg in mensajes_error[:3]:  # Mostrar solo los primeros 3 errores
                    flash(msg, 'warning')
    
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    
    # Volver a mostrar resultados CON DATOS ACTUALIZADOS DE ML
    publicaciones = query_db(
        "SELECT mla_id, titulo_ml, activo FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE",
        (sku,)
    )
    
    pubs_lista = []
    access_token_refresh = cargar_ml_token()
    
    for row in publicaciones:
        if access_token_refresh:
            datos_ml = obtener_datos_ml(row['mla_id'], access_token_refresh)
            pubs_lista.append({
                'mla': row['mla_id'],
                'titulo': datos_ml['titulo'],
                'stock_actual': datos_ml['stock'],
                'demora': datos_ml.get('demora'),
                'estado': 'Activa' if row['activo'] else 'Pausada'
            })
        else:
            pubs_lista.append({
                'mla': row['mla_id'],
                'titulo': row['titulo_ml'] or 'Sin título',
                'stock_actual': '-',
                'demora': None,
                'estado': 'Activa' if row['activo'] else 'Pausada'
            })
    
    return render_template('cargar_stock_ml.html',
                         sku_buscado=sku,
                         publicaciones=pubs_lista,
                         es_sku_con_z=sku.endswith('Z'))
