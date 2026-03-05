# ============================================================================
# FUNCIÓN PARA OBTENER DATOS DE ML (CON DEMORA)
# ============================================================================

def obtener_datos_ml(mla_id, access_token):
    """
    Obtener título, stock y demora actual de una publicación de ML
    
    Returns:
        dict con 'titulo', 'stock' y 'demora'
    """
    try:
        url = f'https://api.mercadolibre.com/items/{mla_id}'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extraer demora si existe
            demora = None
            sale_terms = data.get('sale_terms', [])
            for term in sale_terms:
                if term.get('id') == 'MANUFACTURING_TIME':
                    demora = term.get('value_name', 'Sin especificar')
                    break
            
            return {
                'titulo': data.get('title', 'Sin título'),
                'stock': data.get('available_quantity', 0),
                'demora': demora  # ← NUEVO: días de demora o None
            }
        else:
            return {'titulo': 'Error', 'stock': 0, 'demora': None}
    
    except Exception as e:
        return {'titulo': 'Error', 'stock': 0, 'demora': None}


# ============================================================================
# RUTA BUSCAR SKU - ACTUALIZADA CON DEMORA
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
        
        # Consultar datos actuales de ML
        datos_ml = obtener_datos_ml(mla_id, access_token)
        
        publicaciones.append({
            'mla': mla_id,
            'titulo': datos_ml['titulo'],
            'stock_actual': datos_ml['stock'],
            'demora': datos_ml['demora'],  # ← NUEVO
            'estado': 'Activa' if row['activo'] else 'Pausada'
        })
    
    return render_template('cargar_stock_ml.html',
                         sku_buscado=sku_buscado,
                         publicaciones=publicaciones,
                         es_sku_con_z=es_sku_con_z,
                         mensaje=None,
                         mensaje_tipo=None)
