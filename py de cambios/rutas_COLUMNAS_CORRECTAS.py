# ============================================================================
# RUTAS CARGAR STOCK ML - CORREGIDAS CON COLUMNAS REALES
# ============================================================================

@app.route('/cargar-stock-ml', methods=['GET'])
def cargar_stock_ml():
    """Mostrar página para cargar stock en ML"""
    return render_template('cargar_stock_ml.html',
                         sku_buscado=None,
                         publicaciones=[],
                         es_sku_con_z=False,
                         mensaje=None,
                         mensaje_tipo=None)


@app.route('/buscar-sku-ml', methods=['POST'])
def buscar_sku_ml():
    """Buscar publicaciones de ML por SKU"""
    
    sku_buscado = request.form.get('sku_buscar', '').strip().upper()
    
    if not sku_buscado:
        flash('Debes ingresar un SKU', 'warning')
        return redirect(url_for('cargar_stock_ml'))
    
    # Detectar si el SKU termina en Z
    es_sku_con_z = sku_buscado.endswith('Z')
    
    # Buscar publicaciones - COLUMNAS CORREGIDAS
    query = """
        SELECT mla_id, titulo_ml, activo
        FROM sku_mla_mapeo
        WHERE sku = %s AND activo = TRUE
        ORDER BY mla_id
    """
    
    resultados = query_db(query, (sku_buscado,))
    
    publicaciones = []
    for row in resultados:
        # Para cada MLA, consultar el stock actual desde la API de ML
        publicaciones.append({
            'mla': row['mla_id'],
            'titulo': row['titulo_ml'],
            'stock_actual': '-',  # No está en BD, se puede consultar de ML si se necesita
            'estado': 'Activa' if row['activo'] else 'Pausada'
        })
    
    return render_template('cargar_stock_ml.html',
                         sku_buscado=sku_buscado,
                         publicaciones=publicaciones,
                         es_sku_con_z=es_sku_con_z,
                         mensaje=None,
                         mensaje_tipo=None)


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
    
    try:
        # Actualizar handling_time en ML (20 días por defecto)
        url = f'https://api.mercadolibre.com/items/{mla}'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        data = {
            'shipping': {
                'local_pick_up': False,
                'free_shipping': False,
                'mode': 'not_specified',
                'methods': [],
                'dimensions': None,
                'tags': ['self_service_in'],
                'logistic_type': 'default'
            },
            'sale_terms': [
                {'id': 'MANUFACTURING_TIME', 'value_name': '20 días'}
            ]
        }
        
        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code == 200:
            flash(f'✅ Demora quitada de {mla}', 'success')
        else:
            flash(f'❌ Error al quitar demora de {mla}: {response.text}', 'danger')
    
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    
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
    
    for row in mlas:
        mla = row['mla_id']
        try:
            url = f'https://api.mercadolibre.com/items/{mla}'
            headers = {'Authorization': f'Bearer {access_token}'}
            
            data = {
                'shipping': {
                    'local_pick_up': False,
                    'free_shipping': False,
                    'mode': 'not_specified',
                    'methods': [],
                    'dimensions': None,
                    'tags': ['self_service_in'],
                    'logistic_type': 'default'
                },
                'sale_terms': [
                    {'id': 'MANUFACTURING_TIME', 'value_name': '20 días'}
                ]
            }
            
            response = requests.put(url, headers=headers, json=data)
            
            if response.status_code == 200:
                exitos += 1
            else:
                errores += 1
        
        except Exception as e:
            errores += 1
    
    if exitos > 0:
        flash(f'✅ Demora quitada de {exitos} publicaciones', 'success')
    if errores > 0:
        flash(f'⚠️ {errores} publicaciones con errores', 'warning')
    
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
