# ============================================================================
# FUNCIÓN HELPER PARA QUITAR DEMORA (basada en la que funciona)
# ============================================================================

def quitar_handling_time_ml(mla_id, access_token):
    """
    Quitar el tiempo de disponibilidad (handling_time) en ML
    
    Args:
        mla_id: ID de la publicación
        access_token: Token de ML
    
    Returns:
        (success: bool, message: str)
    """
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # IMPORTANTE: Primero traer la publicación actual
        response_get = requests.get(
            f'https://api.mercadolibre.com/items/{mla_id}',
            headers=headers
        )
        
        if response_get.status_code != 200:
            return False, "Error obteniendo publicación"
        
        item_data = response_get.json()
        
        # Filtrar sale_terms para quitar MANUFACTURING_TIME
        sale_terms_actuales = item_data.get('sale_terms', [])
        sale_terms_sin_demora = [
            term for term in sale_terms_actuales
            if term.get('id') != 'MANUFACTURING_TIME'
        ]
        
        # Actualizar sin MANUFACTURING_TIME
        data = {
            "sale_terms": sale_terms_sin_demora
        }
        
        response = requests.put(
            f'https://api.mercadolibre.com/items/{mla_id}',
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return True, f"Demora quitada de {mla_id}"
        else:
            error_data = response.json()
            error_msg = error_data.get('message', 'Error desconocido')
            return False, f"Error ML: {error_msg}"
    
    except Exception as e:
        return False, f"Error: {str(e)}"


# ============================================================================
# RUTAS ACTUALIZADAS USANDO LA FUNCIÓN HELPER
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
    
    # Usar función helper
    success, message = quitar_handling_time_ml(mla, access_token)
    
    if success:
        flash(f'✅ {message}', 'success')
    else:
        flash(f'❌ {message}', 'danger')
    
    # Volver a la búsqueda
    publicaciones = query_db(
        "SELECT mla_id, titulo_ml, activo FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE",
        (sku,)
    )
    
    pubs_lista = []
    for row in publicaciones:
        pubs_lista.append({
            'mla': row['mla_id'],
            'titulo': row['titulo_ml'],
            'stock_actual': '-',
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
    mensajes_error = []
    
    for row in mlas:
        mla = row['mla_id']
        
        # Usar función helper
        success, message = quitar_handling_time_ml(mla, access_token)
        
        if success:
            exitos += 1
        else:
            errores += 1
            mensajes_error.append(message)
    
    if exitos > 0:
        flash(f'✅ Demora quitada de {exitos} publicaciones', 'success')
    if errores > 0:
        flash(f'⚠️ {errores} publicaciones con errores', 'warning')
        # Mostrar primeros 3 errores
        for msg in mensajes_error[:3]:
            flash(msg, 'warning')
    
    # Volver a mostrar resultados
    publicaciones = query_db(
        "SELECT mla_id, titulo_ml, activo FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE",
        (sku,)
    )
    
    pubs_lista = []
    for row in publicaciones:
        pubs_lista.append({
            'mla': row['mla_id'],
            'titulo': row['titulo_ml'],
            'stock_actual': '-',
            'estado': 'Activa' if row['activo'] else 'Pausada'
        })
    
    return render_template('cargar_stock_ml.html',
                         sku_buscado=sku,
                         publicaciones=pubs_lista,
                         es_sku_con_z=sku.endswith('Z'))
