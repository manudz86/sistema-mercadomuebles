# ============================================================================
# RUTAS ACTUALIZADAS CON MODAL DE ERROR DE STOCK
# Reemplazar estas 2 funciones en app.py
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
            # No hay stock suficiente - mostrar modal de error
            mensaje_html = f'''
                <p><strong>No se puede procesar la venta {venta["numero_venta"]}</strong></p>
                <p>Los siguientes productos no tienen stock suficiente:</p>
                <ul class="list-unstyled">
            '''
            for error in errores:
                mensaje_html += f'<li class="text-danger mb-2"><i class="bi bi-x-circle-fill"></i> {error}</li>'
            
            mensaje_html += '''
                </ul>
                <div class="alert alert-info mt-3">
                    <i class="bi bi-info-circle"></i> 
                    Por favor, <strong>carga más stock</strong> antes de procesar esta venta.
                </div>
            '''
            flash(mensaje_html, 'error_stock')
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
                # No hay stock suficiente - mostrar modal de error
                mensaje_html = f'''
                    <p><strong>No se puede marcar como entregada la venta {venta["numero_venta"]}</strong></p>
                    <p>Los siguientes productos no tienen stock suficiente:</p>
                    <ul class="list-unstyled">
                '''
                for error in errores:
                    mensaje_html += f'<li class="text-danger mb-2"><i class="bi bi-x-circle-fill"></i> {error}</li>'
                
                mensaje_html += '''
                    </ul>
                    <div class="alert alert-info mt-3">
                        <i class="bi bi-info-circle"></i> 
                        Por favor, <strong>carga más stock</strong> antes de marcar como entregada.
                    </div>
                '''
                flash(mensaje_html, 'error_stock')
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


# ============================================================================
# CAMBIOS CLAVE:
# ============================================================================
# 
# 1. Categoría flash cambiada: 'error' → 'error_stock'
# 2. Mensaje HTML estructurado con lista <ul> y clases de Bootstrap
# 3. El template detecta category='error_stock' y muestra modal automáticamente
# 4. Modal tiene botón "Ir a Cargar Stock" para facilitar solución
# 
# ============================================================================
