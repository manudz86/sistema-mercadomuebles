# ============================================================================
# RUTAS: ACCIONES MÚLTIPLES EN VENTAS ACTIVAS
# Agregar en app.py después de las rutas individuales de activas
# ============================================================================

@app.route('/ventas/activas/pasar-proceso-multiple', methods=['POST'])
def pasar_a_proceso_multiple():
    """
    Pasar múltiples ventas a proceso de envío
    Descuenta stock con verificación
    """
    try:
        venta_ids = request.form.getlist('venta_ids')
        
        if not venta_ids:
            flash('❌ No se seleccionaron ventas', 'error')
            return redirect(url_for('ventas_activas'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ventas_procesadas = 0
        ventas_sin_stock = []
        
        for venta_id in venta_ids:
            try:
                # Obtener venta
                cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
                venta = cursor.fetchone()
                
                if not venta or venta['estado_entrega'] != 'pendiente':
                    continue
                
                # Obtener items
                cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
                items = cursor.fetchall()
                
                # VERIFICAR STOCK ANTES DE DESCONTAR
                hay_stock, errores = verificar_stock_disponible(cursor, items, venta['ubicacion_despacho'])
                
                if not hay_stock:
                    # No hay stock - agregar a lista de errores
                    ventas_sin_stock.append({
                        'numero': venta['numero_venta'],
                        'errores': errores
                    })
                    continue
                
                # HAY STOCK - PROCEDER CON DESCUENTO
                for item in items:
                    descontar_stock_item(cursor, item, venta['ubicacion_despacho'])
                
                # Actualizar estado
                cursor.execute('''
                    UPDATE ventas 
                    SET estado_entrega = 'en_proceso',
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
        
        # MENSAJES
        if ventas_procesadas > 0:
            flash(f'✅ {ventas_procesadas} venta(s) pasadas a Proceso de Envío. Stock descontado.', 'success')
        
        if ventas_sin_stock:
            mensaje_html = '<div class="alert alert-warning"><strong>⚠️ Algunas ventas no se pudieron procesar por falta de stock:</strong><ul class="mt-2">'
            for v in ventas_sin_stock:
                mensaje_html += f'<li><strong>{v["numero"]}</strong><ul class="list-unstyled ms-3">'
                for error in v['errores']:
                    mensaje_html += f'<li class="text-danger"><small>{error}</small></li>'
                mensaje_html += '</ul></li>'
            mensaje_html += '</ul></div>'
            flash(mensaje_html, 'error_stock')
        
        if ventas_procesadas == 0 and not ventas_sin_stock:
            flash('❌ No se pudieron procesar las ventas seleccionadas', 'error')
        
        # Mantener filtros
        filtros = {}
        for key in ['buscar', 'zona', 'metodo_envio', 'tipo_entrega', 'estado_pago']:
            if request.form.get(key):
                filtros[key] = request.form.get(key)
        
        return redirect(url_for('ventas_activas', **filtros))
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ventas_activas'))


@app.route('/ventas/activas/marcar-entregadas-multiple', methods=['POST'])
def marcar_entregadas_multiple():
    """
    Marcar múltiples ventas como entregadas
    Descuenta stock si no se descontó, con verificación
    """
    try:
        venta_ids = request.form.getlist('venta_ids')
        
        if not venta_ids:
            flash('❌ No se seleccionaron ventas', 'error')
            return redirect(url_for('ventas_activas'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ventas_procesadas = 0
        ventas_sin_stock = []
        
        for venta_id in venta_ids:
            try:
                # Obtener venta
                cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
                venta = cursor.fetchone()
                
                if not venta or venta['estado_entrega'] != 'pendiente':
                    continue
                
                # Si está pendiente, necesita descontar stock
                cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
                items = cursor.fetchall()
                
                # VERIFICAR STOCK ANTES DE DESCONTAR
                hay_stock, errores = verificar_stock_disponible(cursor, items, venta['ubicacion_despacho'])
                
                if not hay_stock:
                    # No hay stock - agregar a lista de errores
                    ventas_sin_stock.append({
                        'numero': venta['numero_venta'],
                        'errores': errores
                    })
                    continue
                
                # HAY STOCK - DESCONTAR
                for item in items:
                    descontar_stock_item(cursor, item, venta['ubicacion_despacho'])
                
                # Actualizar estado Y FECHA DE ENTREGA
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
        
        # MENSAJES
        if ventas_procesadas > 0:
            flash(f'✅ {ventas_procesadas} venta(s) marcadas como Entregadas.', 'success')
        
        if ventas_sin_stock:
            mensaje_html = '<div class="alert alert-warning"><strong>⚠️ Algunas ventas no se pudieron marcar como entregadas por falta de stock:</strong><ul class="mt-2">'
            for v in ventas_sin_stock:
                mensaje_html += f'<li><strong>{v["numero"]}</strong><ul class="list-unstyled ms-3">'
                for error in v['errores']:
                    mensaje_html += f'<li class="text-danger"><small>{error}</small></li>'
                mensaje_html += '</ul></li>'
            mensaje_html += '</ul></div>'
            flash(mensaje_html, 'error_stock')
        
        if ventas_procesadas == 0 and not ventas_sin_stock:
            flash('❌ No se pudieron procesar las ventas seleccionadas', 'error')
        
        # Mantener filtros
        filtros = {}
        for key in ['buscar', 'zona', 'metodo_envio', 'tipo_entrega', 'estado_pago']:
            if request.form.get(key):
                filtros[key] = request.form.get(key)
        
        return redirect(url_for('ventas_activas', **filtros))
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ventas_activas'))


@app.route('/ventas/activas/cancelar-multiple', methods=['POST'])
def cancelar_ventas_multiple():
    """
    Cancelar múltiples ventas
    NO descuenta stock (porque son ventas pendientes)
    """
    try:
        venta_ids = request.form.getlist('venta_ids')
        
        if not venta_ids:
            flash('❌ No se seleccionaron ventas', 'error')
            return redirect(url_for('ventas_activas'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ventas_procesadas = 0
        
        for venta_id in venta_ids:
            try:
                # Verificar que exista y esté pendiente
                cursor.execute('SELECT id FROM ventas WHERE id = %s AND estado_entrega = %s', (venta_id, 'pendiente'))
                venta = cursor.fetchone()
                
                if not venta:
                    continue
                
                # Actualizar estado
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
            flash('❌ No se pudieron cancelar las ventas seleccionadas', 'error')
        else:
            flash(f'✅ {ventas_procesadas} venta(s) canceladas. No se descontó stock.', 'info')
        
        # Mantener filtros
        filtros = {}
        for key in ['buscar', 'zona', 'metodo_envio', 'tipo_entrega', 'estado_pago']:
            if request.form.get(key):
                filtros[key] = request.form.get(key)
        
        return redirect(url_for('ventas_activas', **filtros))
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ventas_activas'))
