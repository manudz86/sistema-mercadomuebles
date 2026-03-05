# ============================================================================
# AGREGAR ESTAS FUNCIONES Y RUTAS A app.py
# ============================================================================

# ─── FUNCIÓN HELPER: Actualizar stock en ML ───
def actualizar_stock_ml(mla_id, cantidad, access_token):
    """
    Actualizar stock de una publicación en Mercado Libre
    
    Args:
        mla_id: ID de la publicación (ej: MLA603027006)
        cantidad: Nueva cantidad de stock (0 para pausar ventas)
        access_token: Token de ML
    
    Returns:
        (success: bool, message: str)
    """
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "available_quantity": cantidad
        }
        
        response = requests.put(
            f'https://api.mercadolibre.com/items/{mla_id}',
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return True, f"Stock actualizado a {cantidad} en ML"
        else:
            error_data = response.json()
            error_msg = error_data.get('message', 'Error desconocido')
            return False, f"Error ML: {error_msg}"
    
    except Exception as e:
        return False, f"Error: {str(e)}"


# ─── FUNCIÓN HELPER: Pausar publicación en ML ───
def pausar_publicacion_ml(mla_id, access_token):
    """
    Pausar una publicación en Mercado Libre
    
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
        
        data = {
            "status": "paused"
        }
        
        response = requests.put(
            f'https://api.mercadolibre.com/items/{mla_id}',
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return True, "Publicación pausada en ML"
        else:
            error_data = response.json()
            error_msg = error_data.get('message', 'Error desconocido')
            return False, f"Error ML: {error_msg}"
    
    except Exception as e:
        return False, f"Error: {str(e)}"


# ─── RUTA NUEVA: Sincronizar stock con ML desde alertas ───
@app.route('/alertas/<int:alerta_id>/sincronizar-ml', methods=['POST'])
def sincronizar_ml_desde_alerta(alerta_id):
    """
    Poner stock en 0 en las publicaciones de ML asociadas al SKU de la alerta
    """
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay token de ML configurado', 'error')
        return redirect(url_for('alertas_ml'))
    
    try:
        # Obtener la alerta
        alerta = query_db('SELECT * FROM alertas_stock WHERE id = %s', (alerta_id,), one=True)
        
        if not alerta:
            flash('❌ Alerta no encontrada', 'error')
            return redirect(url_for('alertas_ml'))
        
        sku = alerta['sku']
        
        # Obtener publicaciones de ML asociadas a este SKU
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
        
        # Marcar alerta como procesada
        execute_db(
            "UPDATE alertas_stock SET estado = 'procesada', fecha_procesada = NOW() WHERE id = %s",
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


# ─── RUTA ACTUALIZADA: alertas_ml con info de publicaciones ───
@app.route('/alertas')
def alertas_ml():
    """Ver alertas de stock pendientes con info de publicaciones ML"""
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
            
            # Obtener publicaciones ML asociadas
            publicaciones = query_db(
                'SELECT mla_id, titulo_ml FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE',
                (sku,)
            )
            
            alerta['publicaciones_ml'] = publicaciones
            alerta['tiene_ml'] = len(publicaciones) > 0
            alertas.append(alerta)
    
    except Exception as e:
        flash(f'Error al cargar alertas: {str(e)}', 'error')
    
    return render_template('alertas.html', alertas=alertas)
