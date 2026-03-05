# ============================================================================
# AGREGAR/REEMPLAZAR ESTAS FUNCIONES EN app.py
# ============================================================================

# ─── FUNCIÓN 1: Actualizar handling_time (tiempo de demora) en ML ───
def actualizar_handling_time_ml(mla_id, dias, access_token):
    """
    Actualizar el tiempo de disponibilidad (handling_time) en ML
    
    Args:
        mla_id: ID de la publicación
        dias: Cantidad de días de demora
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
        
        # Actualizar solo handling_time
        data = {
            "sale_terms": [
                {
                    "id": "MANUFACTURING_TIME",
                    "value_name": f"{dias} días"
                }
            ]
        }
        
        response = requests.put(
            f'https://api.mercadolibre.com/items/{mla_id}',
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return True, f"Demora configurada a {dias} días"
        else:
            error_data = response.json()
            error_msg = error_data.get('message', 'Error desconocido')
            return False, f"Error ML: {error_msg}"
    
    except Exception as e:
        return False, f"Error: {str(e)}"


# ─── FUNCIÓN 2: Sincronizar variantes con Z (demora) ───
@app.route('/alertas/<int:alerta_id>/configurar-demora-ml', methods=['POST'])
def configurar_demora_ml_desde_alerta(alerta_id):
    """
    Configurar días de demora en las publicaciones CON Z del SKU de la alerta
    """
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay token de ML configurado', 'error')
        return redirect(url_for('alertas_ml'))
    
    # Obtener días de demora del formulario
    dias_demora = request.form.get('dias_demora', type=int)
    
    if not dias_demora or dias_demora < 1 or dias_demora > 90:
        flash('❌ Los días de demora deben estar entre 1 y 90', 'error')
        return redirect(url_for('alertas_ml'))
    
    try:
        # Obtener la alerta
        alerta = query_db('SELECT * FROM alertas_stock WHERE id = %s', (alerta_id,))
        if alerta:
            alerta = alerta[0]
        
        if not alerta:
            flash('❌ Alerta no encontrada', 'error')
            return redirect(url_for('alertas_ml'))
        
        sku = alerta['sku']
        sku_con_z = f"{sku}Z"  # Buscar variante con Z
        
        # Obtener publicaciones CON Z de este SKU
        publicaciones = query_db(
            'SELECT * FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE',
            (sku_con_z,)
        )
        
        if not publicaciones:
            flash(f'⚠️ No hay publicaciones con Z mapeadas para {sku_con_z}', 'warning')
            return redirect(url_for('alertas_ml'))
        
        # Actualizar demora en cada publicación
        resultados = []
        errores = []
        
        for pub in publicaciones:
            mla_id = pub['mla_id']
            success, message = actualizar_handling_time_ml(mla_id, dias_demora, access_token)
            
            if success:
                resultados.append(f"{mla_id}: {message}")
            else:
                errores.append(f"{mla_id}: {message}")
        
        # Mostrar resultados
        if resultados:
            flash(f'✅ Demora configurada en ML: {", ".join(resultados)}', 'success')
        
        if errores:
            flash(f'❌ Errores: {", ".join(errores)}', 'error')
    
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('alertas_ml'))


# ─── FUNCIÓN 3: alertas_ml ACTUALIZADA - detecta variantes con Z ───
@app.route('/alertas')
def alertas_ml():
    """Ver alertas de stock pendientes con info de publicaciones ML (normales y con Z)"""
    alertas = []
    try:
        alertas_raw = query_db('''
            SELECT * FROM alertas_stock 
            WHERE estado = 'pendiente'
            ORDER BY stock_disponible ASC, fecha_creacion DESC
        ''')
        
        # Enriquecer cada alerta con info de publicaciones ML
        for alerta in alertas_raw:
            sku = alerta['sku']
            
            # Publicaciones normales (sin Z)
            publicaciones = query_db(
                'SELECT mla_id, titulo_ml FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE',
                (sku,)
            )
            
            # Publicaciones con variante Z
            sku_con_z = f"{sku}Z"
            publicaciones_z = query_db(
                'SELECT mla_id, titulo_ml FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE',
                (sku_con_z,)
            )
            
            alerta['publicaciones_ml'] = publicaciones
            alerta['tiene_ml'] = len(publicaciones) > 0
            alerta['publicaciones_ml_z'] = publicaciones_z
            alerta['tiene_ml_z'] = len(publicaciones_z) > 0
            alertas.append(alerta)
    
    except Exception as e:
        flash(f'Error al cargar alertas: {str(e)}', 'error')
    
    return render_template('alertas.html', alertas=alertas)


# ─── FUNCIÓN 4: Mapeo automático al importar - quita la Z del SKU ───
def normalizar_sku_ml(sku_ml):
    """
    Quitar la Z del final del SKU de ML si existe
    Ejemplo: CEX140Z → CEX140
    """
    if sku_ml and sku_ml.endswith('Z'):
        return sku_ml[:-1]  # Quitar último carácter
    return sku_ml


# ─── ACTUALIZAR la función ml_guardar_mapeo para usar normalización ───
# Buscar en app.py la función ml_guardar_mapeo y actualizar esta sección:

# ANTES (en ml_guardar_mapeo):
# for item in items_sin_mapear:
#     sku_bd = form.get(f"mapeo_{idx}")
#     items_mapeados.append({
#         'sku_ml': item['sku'],
#         'sku_bd': sku_bd,
#         ...
#     })

# DESPUÉS (agregar normalización):
# for item in items_sin_mapear:
#     sku_ml_original = item['sku']
#     sku_bd = form.get(f"mapeo_{idx}")
#     
#     # Si no se encontró mapeo manual, intentar normalizar (quitar Z)
#     if not sku_bd:
#         sku_normalizado = normalizar_sku_ml(sku_ml_original)
#         if sku_normalizado != sku_ml_original:
#             existe, tipo, nombre = verificar_sku_en_bd(sku_normalizado)
#             if existe:
#                 sku_bd = sku_normalizado
#     
#     items_mapeados.append({
#         'sku_ml': sku_ml_original,
#         'sku_bd': sku_bd,
#         ...
#     })


# ─── ACTUALIZAR la función ml_seleccionar_orden para normalización automática ───
# Buscar esta sección en ml_seleccionar_orden:

# ANTES:
# for item in orden_data['items']:
#     sku = item['sku']
#     if sku:
#         existe, tipo, nombre = verificar_sku_en_bd(sku)
#         if existe:
#             items_mapeados.append(...)
#         else:
#             items_sin_mapear.append(item)

# DESPUÉS:
# for item in orden_data['items']:
#     sku_ml = item['sku']
#     if sku_ml:
#         # Primero intentar con el SKU original
#         existe, tipo, nombre = verificar_sku_en_bd(sku_ml)
#         
#         # Si no existe, intentar quitando la Z
#         if not existe:
#             sku_normalizado = normalizar_sku_ml(sku_ml)
#             if sku_normalizado != sku_ml:
#                 existe, tipo, nombre = verificar_sku_en_bd(sku_normalizado)
#                 if existe:
#                     # Usar el SKU normalizado
#                     sku_ml = sku_normalizado
#         
#         if existe:
#             items_mapeados.append({
#                 'sku_ml': item['sku'],  # Mantener original para referencia
#                 'sku_bd': sku_ml,  # Usar normalizado si fue necesario
#                 'titulo': item['titulo'],
#                 'cantidad': item['cantidad'],
#                 'precio': item['precio'],
#                 'nombre_bd': nombre
#             })
#         else:
#             items_sin_mapear.append(item)
#     else:
#         items_sin_mapear.append(item)
