@app.route('/ventas/historicas/volver-activas-multiple', methods=['POST'])
def historicas_volver_activas_multiple():
    """
    Volver múltiples ventas históricas a ventas activas
    Usa la misma lógica que historicas_volver_activas() individual
    Mantiene filtros después de la acción
    """
    try:
        venta_ids = request.form.getlist('venta_ids')
        
        if not venta_ids:
            flash('❌ No se seleccionaron ventas', 'error')
            return redirect(url_for('ventas_historicas'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ventas_procesadas = 0
        ventas_con_stock_devuelto = 0
        ventas_sin_stock = 0
        
        for venta_id in venta_ids:
            try:
                # Obtener venta
                cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
                venta = cursor.fetchone()
                
                if not venta:
                    continue
                
                estado_anterior = venta['estado_entrega']
                
                # Verificar que sea histórica
                if estado_anterior not in ['entregada', 'cancelada']:
                    continue
                
                # ========================================
                # LÓGICA SEGÚN ESTADO ANTERIOR
                # (igual que historicas_volver_activas)
                # ========================================
                
                if estado_anterior == 'cancelada':
                    # CANCELADA → ACTIVA
                    # NO devolver stock (porque nunca se descontó)
                    cursor.execute('''
                        UPDATE ventas 
                        SET estado_entrega = 'pendiente',
                            fecha_modificacion = NOW()
                        WHERE id = %s
                    ''', (venta_id,))
                    
                    ventas_procesadas += 1
                    ventas_sin_stock += 1
                
                elif estado_anterior == 'entregada':
                    # ENTREGADA → ACTIVA
                    # SÍ devolver stock (porque se descontó cuando se entregó)
                    cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
                    items = cursor.fetchall()
                    
                    # Devolver stock de cada item usando la función existente
                    for item in items:
                        devolver_stock_item(cursor, item, venta['ubicacion_despacho'])
                    
                    # Cambiar estado a pendiente
                    cursor.execute('''
                        UPDATE ventas 
                        SET estado_entrega = 'pendiente',
                            fecha_modificacion = NOW()
                        WHERE id = %s
                    ''', (venta_id,))
                    
                    ventas_procesadas += 1
                    ventas_con_stock_devuelto += 1
            
            except Exception as e:
                # Si falla una venta, continuar con las demás
                print(f"⚠️ Error al procesar venta {venta_id}: {str(e)}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # ========================================
        # MENSAJE DE ÉXITO
        # ========================================
        if ventas_procesadas == 0:
            flash('❌ No se pudieron procesar las ventas seleccionadas', 'error')
        else:
            mensaje = f'✅ {ventas_procesadas} venta(s) devueltas a Ventas Activas.'
            
            if ventas_con_stock_devuelto > 0:
                mensaje += f' Stock restaurado en {ventas_con_stock_devuelto} venta(s).'
            
            if ventas_sin_stock > 0:
                mensaje += f' {ventas_sin_stock} cancelada(s) sin cambios en stock.'
            
            flash(mensaje, 'success')
        
        # ========================================
        # ✅ MANTENER FILTROS
        # ========================================
        filtros = {}
        if request.form.get('buscar'):
            filtros['buscar'] = request.form.get('buscar')
        if request.form.get('estado'):
            filtros['estado'] = request.form.get('estado')
        if request.form.get('periodo'):
            filtros['periodo'] = request.form.get('periodo')
        if request.form.get('metodo_envio'):
            filtros['metodo_envio'] = request.form.get('metodo_envio')
        if request.form.get('zona'):
            filtros['zona'] = request.form.get('zona')
        if request.form.get('canal'):
            filtros['canal'] = request.form.get('canal')
        
        return redirect(url_for('ventas_historicas', **filtros))
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ventas_historicas'))
