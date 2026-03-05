@app.route('/cargar-stock', methods=['GET', 'POST'])
def cargar_stock():
    """Formulario para cargar/agregar stock de productos"""
    from flask import jsonify
    
    if request.method == 'POST' and request.is_json:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            data = request.get_json()
            items = data.get('items', [])
            
            for item in items:
                sku = item['sku']
                cantidad = item['cantidad']
                ubicacion = item['ubicacion']
                motivo = item.get('motivo', 'Carga de stock')
                
                # Obtener datos actuales del producto
                cursor.execute('SELECT nombre, stock_actual, COALESCE(stock_full, 0) as stock_full FROM productos_base WHERE sku = %s', (sku,))
                prod = cursor.fetchone()
                
                if not prod:
                    continue
                
                nombre_producto = prod['nombre']
                
                # Actualizar stock y registrar movimiento
                if ubicacion == 'stock_actual':
                    stock_anterior = prod['stock_actual']
                    stock_nuevo = stock_anterior + cantidad
                    
                    cursor.execute('UPDATE productos_base SET stock_actual = stock_actual + %s WHERE sku = %s', (cantidad, sku))
                    
                    # Registrar en historial
                    cursor.execute('''
                        INSERT INTO movimientos_stock 
                        (sku, nombre_producto, tipo_movimiento, cantidad, stock_anterior, stock_nuevo, motivo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (sku, nombre_producto, 'carga', cantidad, stock_anterior, stock_nuevo, motivo))
                    
                else:  # stock_full
                    stock_anterior = prod['stock_full']
                    stock_nuevo = stock_anterior + cantidad
                    
                    cursor.execute('UPDATE productos_base SET stock_full = stock_full + %s WHERE sku = %s', (cantidad, sku))
                    
                    # Registrar en historial
                    cursor.execute('''
                        INSERT INTO movimientos_stock 
                        (sku, nombre_producto, tipo_movimiento, cantidad, stock_anterior, stock_nuevo, motivo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (sku, nombre_producto, 'carga', cantidad, stock_anterior, stock_nuevo, motivo))
            
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': f'Stock cargado: {len(items)} productos'})
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Si es GET, mostrar formulario
    productos = []
    try:
        productos = query_db('''
            SELECT * FROM productos_base 
            ORDER BY 
                CASE tipo
                    WHEN 'colchon' THEN 1
                    WHEN 'base' THEN 2
                    WHEN 'almohada' THEN 3
                END,
                nombre
        ''')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return render_template('cargar_stock.html', productos=productos)
