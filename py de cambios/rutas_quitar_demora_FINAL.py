# ============================================================================
# RUTAS ACTUALIZADAS - QUITAR DEMORA CORRECTAMENTE
# Usando la función que elimina MANUFACTURING_TIME del array
# ============================================================================

@app.route('/quitar-demora-mla', methods=['POST'])
def quitar_demora_mla():
    """Quitar demora de una publicación específica"""
    
    mla = request.form.get('mla')
    sku = request.form.get('sku')
    
    if not mla or not sku:
        flash('Faltan datos', 'danger')
        return redirect(url_for('cargar_stock_ml'))
    
    # Obtener token dinámico
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('cargar_stock_ml'))
    
    # Usar función corregida que elimina MANUFACTURING_TIME
    success, message = quitar_handling_time_ml(mla, access_token)
    
    if success:
        flash(f'✅ {message}', 'success')
    else:
        flash(f'❌ {message}', 'danger')
    
    # Volver a la búsqueda con datos actualizados
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


@app.route('/quitar-demora-masivo', methods=['POST'])
def quitar_demora_masivo():
    """Quitar demora de todas las publicaciones de un SKU"""
    
    sku = request.form.get('sku')
    
    if not sku:
        flash('Falta el SKU', 'danger')
        return redirect(url_for('cargar_stock_ml'))
    
    # Obtener token dinámico
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('cargar_stock_ml'))
    
    # Obtener todas las publicaciones del SKU
    mlas = query_db(
        "SELECT mla_id FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE",
        (sku,)
    )
    
    exitos = 0
    errores = 0
    ya_sin_demora = 0
    mensajes_error = []
    
    for row in mlas:
        mla = row['mla_id']
        
        # Usar función corregida
        success, message = quitar_handling_time_ml(mla, access_token)
        
        if success:
            if "ya estaba sin demora" in message:
                ya_sin_demora += 1
            else:
                exitos += 1
        else:
            errores += 1
            mensajes_error.append(message)
    
    # Mensajes informativos
    if exitos > 0:
        flash(f'✅ Demora quitada de {exitos} publicaciones', 'success')
    
    if ya_sin_demora > 0:
        flash(f'ℹ️ {ya_sin_demora} publicaciones ya estaban sin demora', 'info')
    
    if errores > 0:
        flash(f'⚠️ {errores} publicaciones con errores', 'warning')
        # Mostrar primeros 3 errores
        for msg in mensajes_error[:3]:
            flash(msg, 'warning')
    
    # Volver a mostrar resultados actualizados
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
