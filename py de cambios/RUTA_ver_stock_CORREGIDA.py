@app.route('/stock')
def ver_stock():
    """Ver stock disponible con filtros - CALCULADO CORRECTAMENTE"""
    productos = []
    filtro_estado = request.args.get('estado', 'TODOS')
    filtro_tipo = request.args.get('tipo', 'TODOS')
    filtro_modelo = request.args.get('modelo', 'TODOS')
    filtro_medida = request.args.get('medida', 'TODAS')
    buscar = request.args.get('buscar', '').strip()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ============================================
        # 1. OBTENER PRODUCTOS BASE
        # ============================================
        query_productos = """
            SELECT 
                sku,
                nombre,
                tipo,
                medida,
                modelo,
                stock_actual,
                COALESCE(stock_full, 0) as stock_full,
                (stock_actual + COALESCE(stock_full, 0)) as stock_fisico
            FROM productos_base
            WHERE 1=1
        """
        params = []
        
        # Filtros
        if filtro_tipo != 'TODOS':
            query_productos += " AND tipo = %s"
            params.append(filtro_tipo)
        
        if filtro_medida != 'TODAS':
            query_productos += " AND medida = %s"
            params.append(filtro_medida)
        
        if filtro_modelo != 'TODOS':
            query_productos += " AND (nombre LIKE %s OR modelo LIKE %s)"
            params.append(f'%{filtro_modelo}%')
            params.append(f'%{filtro_modelo}%')
        
        if buscar:
            query_productos += " AND (sku LIKE %s OR nombre LIKE %s)"
            params.append(f'%{buscar}%')
            params.append(f'%{buscar}%')
        
        query_productos += " ORDER BY tipo, nombre, medida"
        
        cursor.execute(query_productos, tuple(params) if params else None)
        productos_base = cursor.fetchall()
        
        # ============================================
        # 2. OBTENER VENTAS ACTIVAS (descompuestas)
        # ============================================
        cursor.execute('''
            SELECT 
                COALESCE(pb_comp.sku, iv.sku) as sku,
                SUM(iv.cantidad * COALESCE(c.cantidad_necesaria, 1)) as vendido
            FROM items_venta iv
            JOIN ventas v ON iv.venta_id = v.id
            LEFT JOIN productos_compuestos pc ON iv.sku = pc.sku
            LEFT JOIN componentes c ON pc.id = c.producto_compuesto_id
            LEFT JOIN productos_base pb_comp ON c.producto_base_id = pb_comp.id
            WHERE v.estado_entrega = 'pendiente'
            GROUP BY sku
        ''')
        ventas_activas = cursor.fetchall()
        ventas_dict = {v['sku']: int(v['vendido']) for v in ventas_activas}
        
        # ============================================
        # 3. CALCULAR STOCK DISPONIBLE
        # ============================================
        productos = []
        
        for prod in productos_base:
            sku = prod['sku']
            stock_fisico = prod['stock_fisico']
            vendido = ventas_dict.get(sku, 0)
            stock_disponible = stock_fisico - vendido
            
            # Determinar estado
            if stock_disponible <= 0:
                estado_stock = 'SIN_STOCK'
            elif stock_disponible <= 2:
                estado_stock = 'POCO_STOCK'
            else:
                estado_stock = 'DISPONIBLE'
            
            # Filtro por estado
            if filtro_estado != 'TODOS' and estado_stock != filtro_estado:
                continue
            
            productos.append({
                'sku': sku,
                'nombre': prod['nombre'],
                'tipo': prod['tipo'],
                'medida': prod['medida'],
                'modelo': prod['modelo'],
                'stock_fisico': stock_fisico,
                'stock_disponible': stock_disponible,
                'estado_stock': estado_stock
            })
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    
    return render_template('stock.html', 
                         productos=productos, 
                         filtro_estado=filtro_estado,
                         filtro_tipo=filtro_tipo,
                         filtro_modelo=filtro_modelo,
                         filtro_medida=filtro_medida,
                         buscar=buscar)
