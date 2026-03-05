# ============================================================================
# RUTAS: ACCIONES MÚLTIPLES EN VENTAS EN PROCESO
# Agregar en app.py después de las rutas individuales de proceso
# ============================================================================

@app.route('/ventas/proceso/volver-activas-multiple', methods=['POST'])
def proceso_volver_activas_multiple():
    """
    Volver múltiples ventas en proceso a activas
    Devuelve stock de todas
    """
    try:
        venta_ids = request.form.getlist('venta_ids')
        
        if not venta_ids:
            flash('❌ No se seleccionaron ventas', 'error')
            return redirect(url_for('ventas_proceso'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ventas_procesadas = 0
        
        for venta_id in venta_ids:
            try:
                # Obtener venta
                cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
                venta = cursor.fetchone()
                
                if not venta or venta['estado_entrega'] != 'en_proceso':
                    continue
                
                # Obtener items
                cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
                items = cursor.fetchall()
                
                # DEVOLVER STOCK (porque ya se había descontado)
                for item in items:
                    devolver_stock_item(cursor, item, venta['ubicacion_despacho'])
                
                # Actualizar estado a 'pendiente' (volver a activas)
                cursor.execute('''
                    UPDATE ventas 
                    SET estado_entrega = 'pendiente',
                        fecha_modificacion = NOW()
                    WHERE id = %s
                ''', (venta_id,))
                
                ventas_procesadas += 1
            
            except Exception as e:
                print(f"⚠️ Error al procesar venta {venta_id}: {str(e)}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if ventas_procesadas == 0:
            flash('❌ No se pudieron procesar las ventas seleccionadas', 'error')
        else:
            flash(f'✅ {ventas_procesadas} venta(s) devueltas a Ventas Activas. Stock restaurado.', 'success')
        
        # Mantener filtros
        filtros = {}
        if request.form.get('buscar'):
            filtros['buscar'] = request.form.get('buscar')
        if request.form.get('zona'):
            filtros['zona'] = request.form.get('zona')
        if request.form.get('metodo_envio'):
            filtros['metodo_envio'] = request.form.get('metodo_envio')
        
        return redirect(url_for('ventas_proceso', **filtros))
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ventas_proceso'))


@app.route('/ventas/proceso/marcar-entregadas-multiple', methods=['POST'])
def proceso_marcar_entregadas_multiple():
    """
    Marcar múltiples ventas en proceso como entregadas
    NO toca stock (ya estaba descontado)
    """
    try:
        venta_ids = request.form.getlist('venta_ids')
        
        if not venta_ids:
            flash('❌ No se seleccionaron ventas', 'error')
            return redirect(url_for('ventas_proceso'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ventas_procesadas = 0
        
        for venta_id in venta_ids:
            try:
                # Verificar que esté en proceso
                cursor.execute('SELECT estado_entrega FROM ventas WHERE id = %s', (venta_id,))
                venta = cursor.fetchone()
                
                if not venta or venta['estado_entrega'] != 'en_proceso':
                    continue
                
                # Actualizar estado Y FECHA DE ENTREGA (NO descuenta stock)
                cursor.execute('''
                    UPDATE ventas 
                    SET estado_entrega = 'entregada',
                        fecha_entrega = NOW(),
                        fecha_modificacion = NOW()
                    WHERE id = %s
                ''', (venta_id,))
                
                ventas_procesadas += 1
            
            except Exception as e:
                print(f"⚠️ Error al procesar venta {venta_id}: {str(e)}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if ventas_procesadas == 0:
            flash('❌ No se pudieron procesar las ventas seleccionadas', 'error')
        else:
            flash(f'✅ {ventas_procesadas} venta(s) marcadas como Entregadas.', 'success')
        
        # Mantener filtros
        filtros = {}
        if request.form.get('buscar'):
            filtros['buscar'] = request.form.get('buscar')
        if request.form.get('zona'):
            filtros['zona'] = request.form.get('zona')
        if request.form.get('metodo_envio'):
            filtros['metodo_envio'] = request.form.get('metodo_envio')
        
        return redirect(url_for('ventas_proceso', **filtros))
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ventas_proceso'))


@app.route('/ventas/proceso/cancelar-multiple', methods=['POST'])
def proceso_cancelar_multiple():
    """
    Cancelar múltiples ventas en proceso y DEVOLVER stock
    """
    try:
        venta_ids = request.form.getlist('venta_ids')
        motivo_cancelacion = request.form.get('motivo_cancelacion', '').strip()
        
        if not venta_ids:
            flash('❌ No se seleccionaron ventas', 'error')
            return redirect(url_for('ventas_proceso'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ventas_procesadas = 0
        
        for venta_id in venta_ids:
            try:
                # Obtener venta
                cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
                venta = cursor.fetchone()
                
                if not venta or venta['estado_entrega'] != 'en_proceso':
                    continue
                
                # Obtener items
                cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
                items = cursor.fetchall()
                
                # DEVOLVER STOCK
                for item in items:
                    devolver_stock_item(cursor, item, venta['ubicacion_despacho'])
                
                # Actualizar estado y agregar motivo si existe
                if motivo_cancelacion:
                    notas_actuales = venta.get('notas', '') or ''
                    notas_nuevas = f"{notas_actuales}\n[CANCELACIÓN MÚLTIPLE] {motivo_cancelacion}".strip()
                    
                    cursor.execute('''
                        UPDATE ventas 
                        SET estado_entrega = 'cancelada',
                            notas = %s,
                            fecha_modificacion = NOW()
                        WHERE id = %s
                    ''', (notas_nuevas, venta_id))
                else:
                    cursor.execute('''
                        UPDATE ventas 
                        SET estado_entrega = 'cancelada',
                            fecha_modificacion = NOW()
                        WHERE id = %s
                    ''', (venta_id,))
                
                ventas_procesadas += 1
            
            except Exception as e:
                print(f"⚠️ Error al procesar venta {venta_id}: {str(e)}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if ventas_procesadas == 0:
            flash('❌ No se pudieron procesar las ventas seleccionadas', 'error')
        else:
            mensaje = f'✅ {ventas_procesadas} venta(s) canceladas. Stock devuelto correctamente.'
            if motivo_cancelacion:
                mensaje += f' Motivo: {motivo_cancelacion}'
            flash(mensaje, 'success')
        
        # Mantener filtros
        filtros = {}
        if request.form.get('buscar'):
            filtros['buscar'] = request.form.get('buscar')
        if request.form.get('zona'):
            filtros['zona'] = request.form.get('zona')
        if request.form.get('metodo_envio'):
            filtros['metodo_envio'] = request.form.get('metodo_envio')
        
        return redirect(url_for('ventas_proceso', **filtros))
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ventas_proceso'))
