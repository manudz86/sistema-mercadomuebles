# ============================================================================
# AUDITORÍA DE INCONSISTENCIAS ML
# ============================================================================

@app.route('/auditoria-ml', methods=['GET'])
def auditoria_ml():
    """
    Auditoría completa de inconsistencias entre ML y stock local
    """
    
    # Obtener token
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('index'))
    
    try:
        # 1. Obtener stock local de todos los productos
        productos_query = """
            SELECT 
                p.sku,
                p.nombre,
                p.stock AS stock_fisico,
                (p.stock - COALESCE(
                    (SELECT SUM(cantidad) 
                     FROM ventas_items vi 
                     JOIN ventas v ON vi.venta_id = v.id 
                     WHERE vi.sku = p.sku 
                     AND v.estado_entrega = 'pendiente'), 
                    0)
                ) AS stock_disponible
            FROM productos p
            WHERE p.activo = TRUE
        """
        productos = query_db(productos_query)
        
        # Crear diccionario de stock por SKU
        stock_por_sku = {}
        for prod in productos:
            stock_por_sku[prod['sku']] = {
                'nombre': prod['nombre'],
                'stock_fisico': prod['stock_fisico'],
                'stock_disponible': prod['stock_disponible']
            }
        
        # 2. Obtener todas las publicaciones de ML
        publicaciones_db = query_db("""
            SELECT mla_id, sku, titulo_ml 
            FROM sku_mla_mapeo 
            WHERE activo = TRUE
            ORDER BY sku
        """)
        
        # 3. Consultar estado de cada publicación en ML
        pausadas_con_stock = []
        sin_stock_ml = []
        con_demora_y_stock = []
        
        for pub in publicaciones_db:
            mla_id = pub['mla_id']
            sku = pub['sku']
            
            # Obtener stock local del SKU
            stock_info = stock_por_sku.get(sku)
            if not stock_info:
                continue  # SKU no existe en productos
            
            stock_disponible = stock_info['stock_disponible']
            
            # Consultar datos de ML
            datos_ml = obtener_datos_ml(mla_id, access_token)
            status_ml = datos_ml.get('status', 'unknown')
            stock_ml = datos_ml.get('stock', 0)
            demora_ml = datos_ml.get('demora')
            
            # CASO 1: Pausada pero con stock local
            if status_ml == 'paused' and stock_disponible > 0:
                pausadas_con_stock.append({
                    'mla': mla_id,
                    'sku': sku,
                    'titulo': datos_ml['titulo'],
                    'stock_disponible': stock_disponible,
                    'stock_ml': stock_ml
                })
            
            # CASO 2: Sin stock en ML pero con stock local
            if stock_ml == 0 and stock_disponible > 0 and status_ml == 'active':
                sin_stock_ml.append({
                    'mla': mla_id,
                    'sku': sku,
                    'titulo': datos_ml['titulo'],
                    'stock_disponible': stock_disponible,
                    'stock_ml': 0
                })
            
            # CASO 3: Con demora pero con stock local (solo SKUs con Z)
            if sku.endswith('Z') and demora_ml and stock_disponible > 0:
                # Extraer días de demora
                try:
                    dias_demora = int(demora_ml.split()[0]) if demora_ml else 0
                    if dias_demora > 1:  # Solo si tiene más de 1 día
                        con_demora_y_stock.append({
                            'mla': mla_id,
                            'sku': sku,
                            'titulo': datos_ml['titulo'],
                            'stock_disponible': stock_disponible,
                            'demora': demora_ml,
                            'status': status_ml
                        })
                except:
                    pass
        
        return render_template('auditoria_ml.html',
                             pausadas_con_stock=pausadas_con_stock,
                             sin_stock_ml=sin_stock_ml,
                             con_demora_y_stock=con_demora_y_stock,
                             total_pausadas=len(pausadas_con_stock),
                             total_sin_stock=len(sin_stock_ml),
                             total_con_demora=len(con_demora_y_stock))
    
    except Exception as e:
        flash(f'❌ Error al auditar: {str(e)}', 'danger')
        import traceback
        traceback.print_exc()
        return redirect(url_for('index'))


# ============================================================================
# ACCIONES DE CORRECCIÓN MASIVA
# ============================================================================

@app.route('/auditoria-ml/activar', methods=['POST'])
def auditoria_activar_publicaciones():
    """Activar (despausar) publicaciones seleccionadas"""
    
    mlas_seleccionadas = request.form.getlist('mlas[]')
    
    if not mlas_seleccionadas:
        flash('⚠️ No se seleccionaron publicaciones', 'warning')
        return redirect(url_for('auditoria_ml'))
    
    access_token = cargar_ml_token()
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('auditoria_ml'))
    
    exitos = 0
    errores = 0
    
    for mla in mlas_seleccionadas:
        try:
            # Activar publicación en ML
            url = f'https://api.mercadolibre.com/items/{mla}'
            headers = {'Authorization': f'Bearer {access_token}'}
            data = {'status': 'active'}
            
            response = requests.put(url, headers=headers, json=data)
            
            if response.status_code == 200:
                exitos += 1
            else:
                errores += 1
        except:
            errores += 1
    
    if exitos > 0:
        flash(f'✅ {exitos} publicaciones activadas correctamente', 'success')
    if errores > 0:
        flash(f'⚠️ {errores} publicaciones con errores', 'warning')
    
    return redirect(url_for('auditoria_ml'))


@app.route('/auditoria-ml/cargar-stock', methods=['POST'])
def auditoria_cargar_stock():
    """Cargar stock en publicaciones seleccionadas"""
    
    mlas_data = request.form.getlist('mla_stock')
    
    if not mlas_data:
        flash('⚠️ No se seleccionaron publicaciones', 'warning')
        return redirect(url_for('auditoria_ml'))
    
    access_token = cargar_ml_token()
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('auditoria_ml'))
    
    exitos = 0
    errores = 0
    
    # Formato: "MLA123:5" (mla:stock)
    for item in mlas_data:
        try:
            mla, stock_str = item.split(':')
            stock = int(stock_str)
            
            # Usar función helper existente
            success, message = actualizar_stock_ml(mla, stock, access_token)
            
            if success:
                exitos += 1
            else:
                errores += 1
        except:
            errores += 1
    
    if exitos > 0:
        flash(f'✅ Stock cargado en {exitos} publicaciones', 'success')
    if errores > 0:
        flash(f'⚠️ {errores} publicaciones con errores', 'warning')
    
    return redirect(url_for('auditoria_ml'))


@app.route('/auditoria-ml/reducir-demora', methods=['POST'])
def auditoria_reducir_demora():
    """Reducir demora a 1 día en publicaciones seleccionadas"""
    
    mlas_seleccionadas = request.form.getlist('mlas_demora[]')
    
    if not mlas_seleccionadas:
        flash('⚠️ No se seleccionaron publicaciones', 'warning')
        return redirect(url_for('auditoria_ml'))
    
    access_token = cargar_ml_token()
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('auditoria_ml'))
    
    exitos = 0
    errores = 0
    
    for mla in mlas_seleccionadas:
        try:
            # Usar función helper existente
            success, message = actualizar_handling_time_ml(mla, 1, access_token)
            
            if success:
                exitos += 1
            else:
                errores += 1
        except:
            errores += 1
    
    if exitos > 0:
        flash(f'✅ Demora reducida a 1 día en {exitos} publicaciones', 'success')
    if errores > 0:
        flash(f'⚠️ {errores} publicaciones con errores', 'warning')
    
    return redirect(url_for('auditoria_ml'))
