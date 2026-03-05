# ============================================================================
# ACTUALIZACIÓN: Agregar fecha_entrega al marcar entregada
# Buscar estas 2 funciones en app.py y actualizarlas
# ============================================================================

# ==================================================
# FUNCIÓN 1: marcar_entregada (Ventas Activas)
# Ubicación: Después de @app.route('/ventas/activas/<int:venta_id>/entregada')
# ==================================================

@app.route('/ventas/activas/<int:venta_id>/entregada', methods=['POST'])
def marcar_entregada(venta_id):
    """Marcar venta como entregada (descuenta stock si no se descontó)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener venta
        cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('Venta no encontrada', 'error')
            return redirect(url_for('ventas_activas'))
        
        # Si está pendiente, descontar stock
        if venta['estado_entrega'] == 'pendiente':
            cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
            items = cursor.fetchall()
            
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
# FUNCIÓN 2: proceso_marcar_entregada (Proceso de Envío)
# Ubicación: Después de @app.route('/ventas/proceso/<int:venta_id>/entregada')
# ==================================================

@app.route('/ventas/proceso/<int:venta_id>/entregada', methods=['POST'])
def proceso_marcar_entregada(venta_id):
    """Marcar venta en proceso como entregada (stock ya descontado)"""
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
# RESUMEN DE CAMBIOS:
# ============================================================================
# 
# En ambas funciones, cambiar:
# 
# ANTES:
#     UPDATE ventas 
#     SET estado_entrega = 'entregada',
#         fecha_modificacion = NOW()
#     WHERE id = %s
# 
# DESPUÉS:
#     UPDATE ventas 
#     SET estado_entrega = 'entregada',
#         fecha_entrega = NOW(),          <-- AGREGAR ESTA LÍNEA
#         fecha_modificacion = NOW()
#     WHERE id = %s
# 
# ============================================================================
