# ============================================================================
# AUDITORÍA ML - SECCIONES INDEPENDIENTES
# Reemplazar el bloque completo de auditoría en app.py
# ============================================================================

# ============================================================================
# HELPER: CALCULAR STOCK DISPONIBLE (compartido por los 3 tipos de auditoría)
# ============================================================================

def calcular_stock_por_sku():
    """
    Calcula stock disponible para todos los SKUs (base + combos).
    Devuelve dict: { sku: { nombre, stock_fisico, stock_disponible } }
    """
    # 1. Obtener stock físico de productos base
    productos_base_query = query_db('''
        SELECT 
            sku, 
            nombre, 
            tipo, 
            stock_actual,
            COALESCE(stock_full, 0) as stock_full
        FROM productos_base 
        ORDER BY tipo, nombre
    ''')
    
    # 2. Ventas activas descomponiendo combos
    ventas_activas = query_db('''
        SELECT 
            COALESCE(pb_comp.sku, iv.sku) as sku,
            SUM(iv.cantidad * COALESCE(c.cantidad_necesaria, 1)) as vendido
        FROM items_venta iv
        JOIN ventas v ON iv.venta_id = v.id
        LEFT JOIN productos_compuestos pc ON iv.sku = pc.sku
        LEFT JOIN componentes c ON c.producto_compuesto_id = pc.id
        LEFT JOIN productos_base pb_comp ON c.producto_base_id = pb_comp.id
        WHERE v.estado_entrega = 'pendiente'
        GROUP BY sku
    ''')
    
    ventas_dict = {v['sku']: int(v['vendido']) for v in ventas_activas}
    
    # 3. Calcular stock disponible por SKU base
    stock_por_sku = {}
    
    for prod in productos_base_query:
        sku = prod['sku']
        vendido = ventas_dict.get(sku, 0)
        
        if '_DEP' in sku or '_FULL' in sku:
            stock_fisico = int(prod['stock_actual'])
            stock_disponible = stock_fisico - vendido
        elif prod['tipo'] == 'almohada':
            stock_dep = int(prod['stock_actual'])
            stock_full = int(prod['stock_full'])
            stock_fisico = stock_dep + stock_full
            stock_disponible = stock_fisico - vendido
        else:
            stock_fisico = int(prod['stock_actual'])
            stock_disponible = stock_fisico - vendido
        
        stock_por_sku[sku] = {
            'nombre': prod['nombre'],
            'stock_fisico': stock_fisico,
            'stock_disponible': stock_disponible
        }
    
    # 4. Calcular stock disponible de combos
    try:
        productos_combos = query_db('''
            SELECT sku, nombre
            FROM productos_compuestos
            WHERE activo = 1
            ORDER BY nombre
        ''')
        
        if productos_combos:
            for combo in productos_combos:
                sku_combo = combo['sku']
                componentes = query_db('''
                    SELECT pb.sku, c.cantidad_necesaria 
                    FROM componentes c
                    JOIN productos_base pb ON c.producto_base_id = pb.id
                    JOIN productos_compuestos pc ON c.producto_compuesto_id = pc.id
                    WHERE pc.sku = %s
                ''', (sku_combo,))
                
                stock_disponible_combo = 999999
                for comp in componentes:
                    sku_comp = comp['sku']
                    cant_necesaria = int(comp['cantidad_necesaria'])
                    prod_comp = stock_por_sku.get(sku_comp)
                    if prod_comp:
                        combos_posibles = prod_comp['stock_disponible'] // cant_necesaria if cant_necesaria > 0 else 0
                        stock_disponible_combo = min(stock_disponible_combo, combos_posibles)
                    else:
                        stock_disponible_combo = 0
                        break
                
                if stock_disponible_combo == 999999 or stock_disponible_combo < 0:
                    stock_disponible_combo = 0
                
                stock_por_sku[sku_combo] = {
                    'nombre': combo['nombre'],
                    'stock_fisico': 0,
                    'stock_disponible': stock_disponible_combo
                }
    except Exception as e:
        print(f"Error calculando combos: {str(e)}")
    
    return stock_por_sku


# ============================================================================
# PÁGINA PRINCIPAL DE AUDITORÍA (sin barrido, solo estructura)
# ============================================================================

@app.route('/auditoria-ml', methods=['GET'])
def auditoria_ml():
    """Renderiza la página de auditoría. Los datos se cargan vía AJAX por sección."""
    return render_template('auditoria_ml.html')


# ============================================================================
# ENDPOINT AJAX: EJECUTAR AUDITORÍA POR TIPO
# GET /auditoria-ml/run/<tipo>
# tipo: 'pausadas_sin_stock' | 'pausadas_con_stock' | 'demoras'
# ============================================================================

@app.route('/auditoria-ml/run/<tipo>', methods=['GET'])
def auditoria_ml_run(tipo):
    """
    Ejecuta un tipo específico de auditoría y devuelve JSON con los resultados.
    """
    if tipo not in ['pausadas_sin_stock', 'pausadas_con_stock', 'demoras']:
        return jsonify({'error': 'Tipo de auditoría inválido'}), 400
    
    access_token = cargar_ml_token()
    if not access_token:
        return jsonify({'error': 'No hay token de ML configurado'}), 401
    
    try:
        # Calcular stock local
        stock_por_sku = calcular_stock_por_sku()
        
        # Obtener publicaciones relevantes de la BD
        if tipo == 'demoras':
            # Solo SKUs que terminan en Z
            publicaciones_db = query_db("""
                SELECT mla_id, sku, titulo_ml 
                FROM sku_mla_mapeo 
                WHERE activo = TRUE AND sku LIKE '%Z'
                ORDER BY sku
            """)
        else:
            publicaciones_db = query_db("""
                SELECT mla_id, sku, titulo_ml 
                FROM sku_mla_mapeo 
                WHERE activo = TRUE
                ORDER BY sku
            """)
        
        resultados = []
        
        for pub in publicaciones_db:
            mla_id = pub['mla_id']
            sku = pub['sku']
            
            # Obtener stock local del SKU (con fallback sin Z)
            stock_info = stock_por_sku.get(sku)
            if not stock_info and sku.endswith('Z'):
                stock_info = stock_por_sku.get(sku[:-1])
            
            if not stock_info:
                continue
            
            stock_disponible = stock_info['stock_disponible']
            
            # Solo consultar ML si hay stock local relevante
            if tipo in ['pausadas_sin_stock', 'pausadas_con_stock'] and stock_disponible <= 0:
                continue
            if tipo == 'demoras' and stock_disponible <= 0:
                continue
            
            # Consultar datos de ML
            datos_ml = obtener_datos_ml(mla_id, access_token)
            status_ml = datos_ml.get('status', 'unknown')
            stock_ml = datos_ml.get('stock', 0)
            demora_ml = datos_ml.get('demora')
            
            item_base = {
                'mla': mla_id,
                'sku': sku,
                'titulo': datos_ml.get('titulo', pub.get('titulo_ml', '')),
                'stock_disponible': stock_disponible,
                'stock_ml': stock_ml,
                'status': status_ml
            }
            
            if tipo == 'pausadas_sin_stock':
                if status_ml == 'paused' and stock_ml == 0 and stock_disponible > 0:
                    resultados.append(item_base)
            
            elif tipo == 'pausadas_con_stock':
                if status_ml == 'paused' and stock_ml > 0 and stock_disponible > 0:
                    resultados.append(item_base)
            
            elif tipo == 'demoras':
                if demora_ml and demora_ml != 'Sin especificar':
                    try:
                        import re
                        numeros = re.findall(r'\d+', str(demora_ml))
                        if numeros and int(numeros[0]) > 1:
                            item_base['demora'] = demora_ml
                            resultados.append(item_base)
                    except Exception as e:
                        print(f"Error parseando demora '{demora_ml}': {e}")
        
        print(f"✅ Auditoría '{tipo}': {len(resultados)} resultados")
        return jsonify({'tipo': tipo, 'resultados': resultados, 'total': len(resultados)})
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ACCIONES - Devuelven JSON para que el frontend refresque solo la sección
# ============================================================================

@app.route('/auditoria-ml/activar', methods=['POST'])
def auditoria_activar_publicaciones():
    """Activar (despausar) publicaciones seleccionadas. Devuelve JSON."""
    
    mlas_seleccionadas = request.json.get('mlas', []) if request.is_json else request.form.getlist('mlas[]')
    
    if not mlas_seleccionadas:
        return jsonify({'error': 'No se seleccionaron publicaciones'}), 400
    
    access_token = cargar_ml_token()
    if not access_token:
        return jsonify({'error': 'No hay token de ML configurado'}), 401
    
    exitos = 0
    errores = []
    
    for mla in mlas_seleccionadas:
        try:
            url = f'https://api.mercadolibre.com/items/{mla}'
            headers = {'Authorization': f'Bearer {access_token}'}
            data = {'status': 'active'}
            
            response = requests.put(url, headers=headers, json=data)
            
            if response.status_code == 200:
                exitos += 1
            else:
                errores.append(f'{mla}: {response.status_code}')
        except Exception as e:
            errores.append(f'{mla}: {str(e)}')
    
    return jsonify({'exitos': exitos, 'errores': errores, 'total': len(mlas_seleccionadas)})


@app.route('/auditoria-ml/cargar-stock', methods=['POST'])
def auditoria_cargar_stock():
    """Cargar stock en publicaciones seleccionadas. Devuelve JSON."""
    
    # Acepta JSON: { mla_stock: ["MLA123:5", "MLA456:3"] }
    # O form: mla_stock[] = "MLA123:5"
    if request.is_json:
        mlas_data = request.json.get('mla_stock', [])
    else:
        mlas_data = request.form.getlist('mla_stock')
    
    if not mlas_data:
        return jsonify({'error': 'No se seleccionaron publicaciones'}), 400
    
    access_token = cargar_ml_token()
    if not access_token:
        return jsonify({'error': 'No hay token de ML configurado'}), 401
    
    exitos = 0
    errores = []
    
    for item in mlas_data:
        try:
            mla, stock_str = item.split(':')
            stock = int(stock_str)
            success, message = actualizar_stock_ml(mla, stock, access_token)
            if success:
                exitos += 1
            else:
                errores.append(f'{mla}: {message}')
        except Exception as e:
            errores.append(f'{item}: {str(e)}')
    
    return jsonify({'exitos': exitos, 'errores': errores, 'total': len(mlas_data)})


@app.route('/auditoria-ml/reducir-demora', methods=['POST'])
def auditoria_reducir_demora():
    """Reducir demora a 1 día en publicaciones seleccionadas. Devuelve JSON."""
    
    mlas_seleccionadas = request.json.get('mlas', []) if request.is_json else request.form.getlist('mlas_demora[]')
    
    if not mlas_seleccionadas:
        return jsonify({'error': 'No se seleccionaron publicaciones'}), 400
    
    access_token = cargar_ml_token()
    if not access_token:
        return jsonify({'error': 'No hay token de ML configurado'}), 401
    
    exitos = 0
    errores = []
    
    for mla in mlas_seleccionadas:
        try:
            success, message = actualizar_handling_time_ml(mla, 1, access_token)
            if success:
                exitos += 1
            else:
                errores.append(f'{mla}: {message}')
        except Exception as e:
            errores.append(f'{mla}: {str(e)}')
    
    return jsonify({'exitos': exitos, 'errores': errores, 'total': len(mlas_seleccionadas)})
