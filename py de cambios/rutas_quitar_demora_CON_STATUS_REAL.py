# ============================================================================
# RUTAS QUITAR DEMORA - CON STATUS REAL DE ML
# ============================================================================

@app.route('/quitar-demora-mla', methods=['POST'])
def quitar_demora_mla():
    """Reducir demora a 1 día (ML no permite quitarla completamente)"""
    
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
    
    # ML restaura automáticamente - reducir a 1 día es el mínimo
    success, message = actualizar_handling_time_ml(mla, 1, access_token)
    
    if success:
        flash(f'✅ Demora reducida a 1 día en {mla} (mínimo permitido por ML)', 'success')
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
            
            # Mapear status de ML a español
            status_ml = datos_ml.get('status', 'unknown')
            
            if status_ml == 'active':
                estado_texto = 'Activa'
            elif status_ml == 'paused':
                estado_texto = 'Pausada'
            elif status_ml == 'closed':
                estado_texto = 'Cerrada'
            elif status_ml == 'under_review':
                estado_texto = 'En revisión'
            elif status_ml == 'inactive':
                estado_texto = 'Inactiva'
            else:
                estado_texto = status_ml.capitalize()
            
            pubs_lista.append({
                'mla': row['mla_id'],
                'titulo': datos_ml['titulo'],
                'stock_actual': datos_ml['stock'],
                'demora': datos_ml.get('demora'),
                'estado': estado_texto,
                'status_raw': status_ml
            })
        else:
            pubs_lista.append({
                'mla': row['mla_id'],
                'titulo': row['titulo_ml'] or 'Sin título',
                'stock_actual': '-',
                'demora': None,
                'estado': 'Activa' if row['activo'] else 'Pausada',
                'status_raw': 'active' if row['activo'] else 'paused'
            })
    
    return render_template('cargar_stock_ml.html',
                         sku_buscado=sku,
                         publicaciones=pubs_lista,
                         es_sku_con_z=sku.endswith('Z'))


@app.route('/quitar-demora-masivo', methods=['POST'])
def quitar_demora_masivo():
    """Reducir demora a 1 día en todas (ML no permite quitarla)"""
    
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
    mensajes_error = []
    
    for row in mlas:
        mla = row['mla_id']
        
        # Reducir a 1 día (mínimo que acepta ML)
        success, message = actualizar_handling_time_ml(mla, 1, access_token)
        
        if success:
            exitos += 1
        else:
            errores += 1
            mensajes_error.append(message)
    
    if exitos > 0:
        flash(f'✅ Demora reducida a 1 día en {exitos} publicaciones (mínimo permitido por ML)', 'success')
    if errores > 0:
        flash(f'⚠️ {errores} publicaciones con errores', 'warning')
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
            
            # Mapear status de ML a español
            status_ml = datos_ml.get('status', 'unknown')
            
            if status_ml == 'active':
                estado_texto = 'Activa'
            elif status_ml == 'paused':
                estado_texto = 'Pausada'
            elif status_ml == 'closed':
                estado_texto = 'Cerrada'
            elif status_ml == 'under_review':
                estado_texto = 'En revisión'
            elif status_ml == 'inactive':
                estado_texto = 'Inactiva'
            else:
                estado_texto = status_ml.capitalize()
            
            pubs_lista.append({
                'mla': row['mla_id'],
                'titulo': datos_ml['titulo'],
                'stock_actual': datos_ml['stock'],
                'demora': datos_ml.get('demora'),
                'estado': estado_texto,
                'status_raw': status_ml
            })
        else:
            pubs_lista.append({
                'mla': row['mla_id'],
                'titulo': row['titulo_ml'] or 'Sin título',
                'stock_actual': '-',
                'demora': None,
                'estado': 'Activa' if row['activo'] else 'Pausada',
                'status_raw': 'active' if row['activo'] else 'paused'
            })
    
    return render_template('cargar_stock_ml.html',
                         sku_buscado=sku,
                         publicaciones=pubs_lista,
                         es_sku_con_z=sku.endswith('Z'))
