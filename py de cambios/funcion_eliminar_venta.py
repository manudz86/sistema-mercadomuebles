# ============================================================================
# AGREGAR ESTA FUNCIÓN EN app.py DESPUÉS DE LA FUNCIÓN cancelar_venta
# ============================================================================

@app.route('/ventas/activas/<int:venta_id>/eliminar', methods=['POST'])
def eliminar_venta(venta_id):
    """
    Eliminar venta completamente de la base de datos
    NO descuenta stock (igual que cancelar)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener info de la venta antes de borrar
        cursor.execute('SELECT numero_venta FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('❌ Venta no encontrada', 'error')
            return redirect(url_for('ventas_activas'))
        
        numero_venta = venta['numero_venta']
        
        # 1. Eliminar items de venta
        cursor.execute('DELETE FROM items_venta WHERE venta_id = %s', (venta_id,))
        items_eliminados = cursor.rowcount
        
        # 2. Eliminar venta
        cursor.execute('DELETE FROM ventas WHERE id = %s', (venta_id,))
        
        conn.commit()
        
        flash(f'✅ Venta {numero_venta} eliminada correctamente ({items_eliminados} items borrados). No se descontó stock.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error al eliminar venta: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('ventas_activas'))
