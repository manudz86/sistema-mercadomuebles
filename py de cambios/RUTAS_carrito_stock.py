# ============================================================================
# RUTAS PARA CARRITO DE CARGA DE STOCK
# Agregar estas rutas en app.py
# ============================================================================

# ==================================================
# API: Obtener lista de productos
# ==================================================

@app.route('/api/productos')
def api_productos():
    """Retorna lista de todos los productos para el buscador"""
    try:
        productos = query_db('''
            SELECT sku, nombre, stock_actual, stock_full, tipo
            FROM productos_base
            ORDER BY nombre
        ''')
        
        return jsonify(productos)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================================================
# POST: Cargar stock desde carrito
# ==================================================

@app.route('/cargar-stock', methods=['POST'])
def cargar_stock_carrito():
    """Procesa la carga de stock desde el carrito"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        data = request.get_json()
        items = data.get('items', [])
        
        if not items:
            return jsonify({'success': False, 'error': 'No hay items para cargar'}), 400
        
        # Procesar cada item del carrito
        for item in items:
            sku = item['sku']
            cantidad = item['cantidad']
            ubicacion = item['ubicacion']  # 'stock_actual' o 'stock_full'
            motivo = item['motivo']
            
            # Actualizar stock
            if ubicacion == 'stock_actual':
                cursor.execute('''
                    UPDATE productos_base 
                    SET stock_actual = stock_actual + %s,
                        fecha_actualizacion = NOW()
                    WHERE sku = %s
                ''', (cantidad, sku))
            else:  # stock_full
                cursor.execute('''
                    UPDATE productos_base 
                    SET stock_full = stock_full + %s,
                        fecha_actualizacion = NOW()
                    WHERE sku = %s
                ''', (cantidad, sku))
            
            # Registrar en historial
            cursor.execute('''
                INSERT INTO historial_movimientos 
                (sku, tipo_movimiento, cantidad, ubicacion, motivo, usuario, fecha)
                VALUES (%s, 'carga', %s, %s, %s, 'Sistema', NOW())
            ''', (sku, cantidad, ubicacion, motivo))
        
        conn.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Stock cargado: {len(items)} productos, {sum(i["cantidad"] for i in items)} unidades'
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# RUTA ORIGINAL: cargar_stock (GET)
# Actualizar para que renderice el nuevo template
# ============================================================================

@app.route('/cargar-stock')
def cargar_stock_page():
    """Página de cargar stock con carrito"""
    return render_template('cargar_stock.html')


# ============================================================================
# NOTA:
# ============================================================================
# Si ya existe una ruta /cargar-stock con POST, renombrar esta a:
# @app.route('/cargar-stock-carrito', methods=['POST'])
# 
# Y en el JavaScript del template, cambiar la URL a '/cargar-stock-carrito'
# ============================================================================
