# ============================================================================
# RUTAS ALERTAS ML - ACTUALIZACIÓN COMPLETA
# Reemplazar las rutas de alertas en app.py
# ============================================================================

@app.route('/alertas')
def alertas_ml():
    """Ver alertas de stock pendientes"""
    alertas = []
    try:
        alertas = query_db('''
            SELECT * FROM alertas_stock 
            WHERE estado = 'pendiente'
            ORDER BY stock_disponible ASC, fecha_creacion DESC
        ''')
    except Exception as e:
        flash(f'Error al cargar alertas: {str(e)}', 'error')
    
    return render_template('alertas.html', alertas=alertas)


@app.route('/alertas/<int:alerta_id>/procesar', methods=['POST'])
def marcar_alerta_procesada(alerta_id):
    """Marcar una alerta como procesada"""
    try:
        execute_db(
            "UPDATE alertas_stock SET estado = 'procesada', fecha_procesada = NOW() WHERE id = %s",
            (alerta_id,)
        )
        flash('✅ Alerta marcada como procesada', 'success')
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'error')
    
    return redirect(url_for('alertas_ml'))


@app.route('/alertas/marcar-todas-procesadas', methods=['POST'])
def marcar_todas_procesadas():
    """Marcar TODAS las alertas pendientes como procesadas"""
    try:
        result = execute_db(
            "UPDATE alertas_stock SET estado = 'procesada', fecha_procesada = NOW() WHERE estado = 'pendiente'"
        )
        flash('✅ Todas las alertas fueron marcadas como procesadas', 'success')
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'error')
    
    return redirect(url_for('alertas_ml'))
