# ============================================================================
# CONFIGURACIÓN - RESETEO DE SISTEMA
# ============================================================================

@app.route('/configuracion/resetear')
def resetear_sistema():
    """Página para resetear el sistema (requiere contraseña)"""
    return render_template('resetear_sistema.html')


@app.route('/configuracion/resetear/ejecutar', methods=['POST'])
def ejecutar_reseteo():
    """Ejecutar reseteo completo del sistema"""
    from flask import jsonify
    
    # Verificar contraseña
    password = request.form.get('password', '')
    confirmar = request.form.get('confirmar', '')
    
    # Contraseña configurada (CAMBIAR ESTO por tu contraseña)
    PASSWORD_CORRECTA = 'CANNON2024'
    
    if password != PASSWORD_CORRECTA:
        flash('❌ Contraseña incorrecta', 'error')
        return redirect(url_for('resetear_sistema'))
    
    if confirmar != 'RESETEAR':
        flash('❌ Debes escribir "RESETEAR" para confirmar', 'error')
        return redirect(url_for('resetear_sistema'))
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # ==================================
        # 1. BORRAR TODAS LAS VENTAS
        # ==================================
        cursor.execute('DELETE FROM items_venta')
        items_borrados = cursor.rowcount
        
        cursor.execute('DELETE FROM ventas')
        ventas_borradas = cursor.rowcount
        
        # ==================================
        # 2. BORRAR MOVIMIENTOS DE STOCK
        # ==================================
        cursor.execute('DELETE FROM movimientos_stock')
        movimientos_borrados = cursor.rowcount
        
        # ==================================
        # 3. RESETEAR STOCK A 0
        # ==================================
        cursor.execute('''
            UPDATE productos_base 
            SET stock_actual = 0, 
                stock_full = 0
        ''')
        productos_reseteados = cursor.rowcount
        
        # ==================================
        # 4. BORRAR ALERTAS DE STOCK
        # ==================================
        try:
            cursor.execute('DELETE FROM alertas_stock')
            alertas_borradas = cursor.rowcount
        except:
            alertas_borradas = 0
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Mensaje de confirmación
        mensaje = f'''
        ✅ <strong>Sistema reseteado correctamente</strong><br><br>
        📊 <strong>Operaciones realizadas:</strong><br>
        • {ventas_borradas} ventas eliminadas<br>
        • {items_borrados} items de venta eliminados<br>
        • {movimientos_borrados} movimientos de stock eliminados<br>
        • {productos_reseteados} productos reseteados a stock 0<br>
        • {alertas_borradas} alertas eliminadas<br><br>
        🎯 El sistema está listo para comenzar de cero.
        '''
        
        flash(mensaje, 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        flash(f'❌ Error al resetear: {str(e)}', 'error')
        return redirect(url_for('resetear_sistema'))
