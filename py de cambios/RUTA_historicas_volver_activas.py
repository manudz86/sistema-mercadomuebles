# ============================================================================
# VENTAS HISTÓRICAS - VOLVER A ACTIVAS
# Agregar en app.py después de la ruta de ventas_historicas()
# ============================================================================

@app.route('/ventas/historicas/<int:venta_id>/volver_activas', methods=['POST'])
def historicas_volver_activas(venta_id):
    """Volver venta histórica (entregada o cancelada) a ventas activas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener venta
        cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('Venta no encontrada', 'error')
            return redirect(url_for('ventas_historicas'))
        
        estado_anterior = venta['estado_entrega']
        numero_venta = venta['numero_venta']
        
        # Verificar que sea histórica (entregada o cancelada)
        if estado_anterior not in ['entregada', 'cancelada']:
            flash(f'La venta {numero_venta} no es histórica', 'warning')
            return redirect(url_for('ventas_historicas'))
        
        # ========================================
        # LÓGICA SEGÚN ESTADO ANTERIOR
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
            
            mensaje = f'✅ Venta {numero_venta} devuelta a Ventas Activas (sin cambios en stock)'
        
        elif estado_anterior == 'entregada':
            # ENTREGADA → ACTIVA
            # SÍ devolver stock (porque se descontó cuando se entregó)
            cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
            items = cursor.fetchall()
            
            # Devolver stock de cada item
            for item in items:
                devolver_stock_item(cursor, item, venta['ubicacion_despacho'])
            
            # Cambiar estado a pendiente
            cursor.execute('''
                UPDATE ventas 
                SET estado_entrega = 'pendiente',
                    fecha_modificacion = NOW()
                WHERE id = %s
            ''', (venta_id,))
            
            mensaje = f'✅ Venta {numero_venta} devuelta a Ventas Activas. Stock restaurado.'
        
        conn.commit()
        flash(mensaje, 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error al volver a activas: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('ventas_historicas'))
