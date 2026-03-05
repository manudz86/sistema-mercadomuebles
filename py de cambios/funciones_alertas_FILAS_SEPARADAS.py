# ============================================================================
# REEMPLAZAR ESTAS 3 FUNCIONES EN app.py
# Sistema de alertas con filas separadas para normales y Z
# ============================================================================

# ─── FUNCIÓN 1: Sincronizar stock 0 (publicaciones normales) ───
@app.route('/alertas/<int:alerta_id>/sincronizar-ml', methods=['POST'])
def sincronizar_ml_desde_alerta(alerta_id):
    """
    Poner stock en 0 en las publicaciones NORMALES (sin Z)
    Procesa solo la parte NORMAL de la alerta
    """
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay token de ML configurado', 'error')
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
        
        # Obtener publicaciones NORMALES (sin Z)
        publicaciones = query_db(
            'SELECT * FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE',
            (sku,)
        )
        
        if not publicaciones:
            flash(f'⚠️ No hay publicaciones de ML mapeadas para el SKU {sku}', 'warning')
            return redirect(url_for('alertas_ml'))
        
        # Actualizar stock en cada publicación
        resultados = []
        errores = []
        
        for pub in publicaciones:
            mla_id = pub['mla_id']
            success, message = actualizar_stock_ml(mla_id, 0, access_token)
            
            if success:
                resultados.append(f"{mla_id}: {message}")
            else:
                errores.append(f"{mla_id}: {message}")
        
        # ✅ LÓGICA DE PROCESAMIENTO INDEPENDIENTE
        sku_con_z = f"{sku}Z"
        tiene_variante_z = len(query_db(
            'SELECT 1 FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE LIMIT 1',
            (sku_con_z,)
        )) > 0
        
        tipo_procesado_actual = alerta.get('tipo_procesado')
        
        if tiene_variante_z:
            # Tiene variante Z - solo marcar que procesamos la parte normal
            if tipo_procesado_actual == 'z':
                # Ya se había procesado Z → ahora marcar como ambos y cerrar alerta
                execute_db(
                    "UPDATE alertas_stock SET tipo_procesado = 'ambos', estado = 'procesada', fecha_procesada = NOW() WHERE id = %s",
                    (alerta_id,)
                )
            else:
                # Solo marcar que se procesó la parte normal
                execute_db(
                    "UPDATE alertas_stock SET tipo_procesado = 'normal' WHERE id = %s",
                    (alerta_id,)
                )
        else:
            # No tiene variante Z - cerrar la alerta directamente
            execute_db(
                "UPDATE alertas_stock SET tipo_procesado = 'ambos', estado = 'procesada', fecha_procesada = NOW() WHERE id = %s",
                (alerta_id,)
            )
        
        # Mostrar resultados
        if resultados:
            flash(f'✅ Stock actualizado en ML: {", ".join(resultados)}', 'success')
        
        if errores:
            flash(f'❌ Errores: {", ".join(errores)}', 'error')
    
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('alertas_ml'))


# ─── FUNCIÓN 2: Configurar demora (publicaciones con Z) ───
@app.route('/alertas/<int:alerta_id>/configurar-demora-ml', methods=['POST'])
def configurar_demora_ml_desde_alerta(alerta_id):
    """
    Configurar días de demora en las publicaciones CON Z
    Procesa solo la parte CON Z de la alerta
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
        sku_con_z = f"{sku}Z"
        
        # Obtener publicaciones CON Z
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
        
        # ✅ LÓGICA DE PROCESAMIENTO INDEPENDIENTE
        tiene_variante_normal = len(query_db(
            'SELECT 1 FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE LIMIT 1',
            (sku,)
        )) > 0
        
        tipo_procesado_actual = alerta.get('tipo_procesado')
        
        if tiene_variante_normal:
            # Tiene variante normal - solo marcar que procesamos la parte Z
            if tipo_procesado_actual == 'normal':
                # Ya se había procesado normal → ahora marcar como ambos y cerrar alerta
                execute_db(
                    "UPDATE alertas_stock SET tipo_procesado = 'ambos', estado = 'procesada', fecha_procesada = NOW() WHERE id = %s",
                    (alerta_id,)
                )
            else:
                # Solo marcar que se procesó la parte Z
                execute_db(
                    "UPDATE alertas_stock SET tipo_procesado = 'z' WHERE id = %s",
                    (alerta_id,)
                )
        else:
            # No tiene variante normal - cerrar la alerta directamente
            execute_db(
                "UPDATE alertas_stock SET tipo_procesado = 'ambos', estado = 'procesada', fecha_procesada = NOW() WHERE id = %s",
                (alerta_id,)
            )
        
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


# ─── FUNCIÓN 3: alertas_ml - misma que antes, sin cambios ───
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
