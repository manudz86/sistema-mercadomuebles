# ============================================================================
# VERSIÓN CON DEBUGGING de nueva_venta_desde_ml
# REEMPLAZAR en app.py temporalmente para debuggear
# ============================================================================

@app.route('/ventas/nueva/ml')
def nueva_venta_desde_ml():
    """
    Crear nueva venta con datos precargados desde ML
    VERSIÓN CON DEBUGGING
    """
    from flask import session
    
    print("\n" + "="*70)
    print("🔍 DEBUG: Cargando nueva venta desde ML")
    print("="*70)
    
    if 'ml_items' not in session:
        flash('❌ No hay datos de ML para importar', 'error')
        return redirect(url_for('ventas_activas'))
    
    ml_items = session.get('ml_items', [])
    ml_orden_id = session.get('ml_orden_id', '')
    ml_shipping = session.get('ml_shipping', {})
    
    print(f"📦 Orden ID: {ml_orden_id}")
    print(f"🛍️ Items: {len(ml_items)} productos")
    print(f"🚚 Shipping data en sesión: {ml_shipping}")
    
    # Obtener datos necesarios para el formulario
    productos = query_db('SELECT * FROM productos_base ORDER BY nombre')
    combos = query_db('SELECT * FROM productos_compuestos ORDER BY nombre')
    
    print("="*70 + "\n")
    
    return render_template('nueva_venta_ml.html',
                         productos=productos,
                         combos=combos,
                         ml_items=ml_items,
                         ml_orden_id=ml_orden_id)
