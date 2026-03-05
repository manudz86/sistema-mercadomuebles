# ============================================================================
# RUTAS ACTUALIZADAS CON VERIFICACIÓN DE STOCK
# Reemplazar estas 3 funciones en app.py
# ============================================================================

# ==================================================
# RUTA 1: Pasar a Proceso (Ventas Activas)
# ==================================================

@app.route('/ventas/activas/<int:venta_id>/proceso', methods=['POST'])
def pasar_a_proceso(venta_id):
    """Pasar venta a proceso de envío (descuenta stock con verificación)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener venta
        cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('Venta no encontrada', 'error')
            return redirect(url_for('ventas_activas'))
        
        # Obtener items
        cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
        items = cursor.fetchall()
        
        # ========================================
        # VERIFICAR STOCK ANTES DE DESCONTAR
        # ========================================
        hay_stock, errores = verificar_stock_disponible(cursor, items, venta['ubicacion_despacho'])
        
        if not hay_stock:
            # No hay stock suficiente - mostrar errores
            mensaje_error = f'❌ No hay stock suficiente para procesar la venta {venta["numero_venta"]}:<br><br>'
            for error in errores:
                mensaje_error += f'• {error}<br>'
            mensaje_error += '<br>Por favor, carga más stock antes de procesar esta venta.'
            flash(mensaje_error, 'error')
            return redirect(url_for('ventas_activas'))
        
        # ========================================
        # HAY STOCK - PROCEDER CON DESCUENTO
        # ========================================
        for item in items:
            descontar_stock_item(cursor, item, venta['ubicacion_despacho'])
        
        # Actualizar estado
        cursor.execute('''
            UPDATE ventas 
            SET estado_entrega = 'en_proceso',
                fecha_modificacion = NOW()
            WHERE id = %s
        ''', (venta_id,))
        
        conn.commit()
        flash(f'✅ Venta {venta["numero_venta"]} pasada a Proceso de Envío. Stock descontado.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error al pasar a proceso: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('ventas_activas'))


# ==================================================
# RUTA 2: Marcar Entregada (Ventas Activas)
# ==================================================

@app.route('/ventas/activas/<int:venta_id>/entregada', methods=['POST'])
def marcar_entregada(venta_id):
    """Marcar venta como entregada (descuenta stock si no se descontó, con verificación)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener venta
        cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('Venta no encontrada', 'error')
            return redirect(url_for('ventas_activas'))
        
        # Si está pendiente, necesita descontar stock
        if venta['estado_entrega'] == 'pendiente':
            cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
            items = cursor.fetchall()
            
            # ========================================
            # VERIFICAR STOCK ANTES DE DESCONTAR
            # ========================================
            hay_stock, errores = verificar_stock_disponible(cursor, items, venta['ubicacion_despacho'])
            
            if not hay_stock:
                # No hay stock suficiente
                mensaje_error = f'❌ No hay stock suficiente para entregar la venta {venta["numero_venta"]}:<br><br>'
                for error in errores:
                    mensaje_error += f'• {error}<br>'
                mensaje_error += '<br>Por favor, carga más stock antes de marcar como entregada.'
                flash(mensaje_error, 'error')
                return redirect(url_for('ventas_activas'))
            
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
        
        conn.commit()
        flash(f'✅ Venta {venta["numero_venta"]} marcada como Entregada.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error al marcar como entregada: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('ventas_activas'))


# ==================================================
# RUTA 3: Marcar Entregada (Proceso de Envío)
# ==================================================

@app.route('/ventas/proceso/<int:venta_id>/entregada', methods=['POST'])
def proceso_marcar_entregada(venta_id):
    """Marcar venta en proceso como entregada (stock ya descontado, pero verificar por si acaso)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener venta
        cursor.execute('SELECT numero_venta, estado_entrega FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('Venta no encontrada', 'error')
            return redirect(url_for('ventas_proceso'))
        
        if venta['estado_entrega'] != 'en_proceso':
            flash('La venta no está en proceso', 'warning')
            return redirect(url_for('ventas_proceso'))
        
        # Actualizar estado Y FECHA DE ENTREGA (NO descuenta stock, ya se descontó)
        cursor.execute('''
            UPDATE ventas 
            SET estado_entrega = 'entregada',
                fecha_entrega = NOW(),
                fecha_modificacion = NOW()
            WHERE id = %s
        ''', (venta_id,))
        
        conn.commit()
        flash(f'✅ Venta {venta["numero_venta"]} marcada como Entregada.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('ventas_proceso'))


# ============================================================================
# RESUMEN:
# ============================================================================
# Estas 3 funciones reemplazan las existentes en app.py
# Ahora VERIFICAN stock ANTES de descontar
# Si no hay stock → Muestran error detallado y NO permiten la acción
# ============================================================================
