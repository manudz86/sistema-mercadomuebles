# ============================================================================
# RUTA BUSCAR SKU - ACTUALIZADA CON STATUS REAL DE ML
# ============================================================================

@app.route('/buscar-sku-ml', methods=['POST'])
def buscar_sku_ml():
    """Buscar publicaciones de ML por SKU"""
    
    sku_buscado = request.form.get('sku_buscar', '').strip().upper()
    
    if not sku_buscado:
        flash('Debes ingresar un SKU', 'warning')
        return redirect(url_for('cargar_stock_ml'))
    
    # Detectar si el SKU termina en Z
    es_sku_con_z = sku_buscado.endswith('Z')
    
    # Obtener token
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay token de ML configurado', 'warning')
        # Buscar sin datos de ML
        query = """
            SELECT mla_id, titulo_ml, activo
            FROM sku_mla_mapeo
            WHERE sku = %s AND activo = TRUE
            ORDER BY mla_id
        """
        
        resultados = query_db(query, (sku_buscado,))
        
        publicaciones = []
        for row in resultados:
            publicaciones.append({
                'mla': row['mla_id'],
                'titulo': row['titulo_ml'] or 'Sin título',
                'stock_actual': '-',
                'demora': None,
                'estado': 'Activa' if row['activo'] else 'Pausada'
            })
        
        return render_template('cargar_stock_ml.html',
                             sku_buscado=sku_buscado,
                             publicaciones=publicaciones,
                             es_sku_con_z=es_sku_con_z)
    
    # Buscar publicaciones en BD
    query = """
        SELECT mla_id, titulo_ml, activo
        FROM sku_mla_mapeo
        WHERE sku = %s AND activo = TRUE
        ORDER BY mla_id
    """
    
    resultados = query_db(query, (sku_buscado,))
    
    publicaciones = []
    for row in resultados:
        mla_id = row['mla_id']
        
        # Consultar datos actuales de ML (incluye status real)
        datos_ml = obtener_datos_ml(mla_id, access_token)
        
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
        
        publicaciones.append({
            'mla': mla_id,
            'titulo': datos_ml['titulo'],
            'stock_actual': datos_ml['stock'],
            'demora': datos_ml.get('demora'),
            'estado': estado_texto,  # ← ESTADO REAL DE ML
            'status_raw': status_ml   # ← Para usar en badges
        })
    
    return render_template('cargar_stock_ml.html',
                         sku_buscado=sku_buscado,
                         publicaciones=publicaciones,
                         es_sku_con_z=es_sku_con_z,
                         mensaje=None,
                         mensaje_tipo=None)
