# ============================================================================
# AGREGAR ESTE ENDPOINT EN app.py (en cualquier lugar con las otras rutas)
# ============================================================================

@app.route('/api/productos')
def api_productos():
    """API para el buscador de productos en templates"""
    from flask import jsonify
    
    # Productos base
    productos_base = query_db('SELECT sku, nombre, tipo, stock_actual FROM productos_base ORDER BY nombre')
    
    # Combos
    combos = query_db('SELECT sku, nombre FROM productos_compuestos ORDER BY nombre')
    
    todos = []
    
    for p in productos_base:
        todos.append({
            'sku': p['sku'],
            'nombre': p['nombre'],
            'tipo': p['tipo'],
            'stock_actual': p['stock_actual']
        })
    
    for c in combos:
        todos.append({
            'sku': c['sku'],
            'nombre': c['nombre'],
            'tipo': 'combo',
            'stock_actual': 0
        })
    
    return jsonify(todos)
