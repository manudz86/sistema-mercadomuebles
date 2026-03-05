# ============================================================================
# FUNCIÓN: DETECTAR Y CREAR ALERTAS DE STOCK
# Agregar en app.py después de las funciones de verificación de stock
# ============================================================================

def detectar_alertas_stock_bajo(cursor):
    """
    Detecta productos con stock disponible <= 0 y crea alertas.
    Retorna lista de productos sin stock para mostrar al usuario.
    
    Stock disponible = Stock físico - Ventas activas
    """
    productos_sin_stock = []
    
    # Obtener stock físico de todos los productos
    cursor.execute('''
        SELECT sku, nombre, stock_actual, COALESCE(stock_full, 0) as stock_full, tipo
        FROM productos_base
        WHERE tipo IN ('colchon', 'base', 'almohada')
    ''')
    productos = cursor.fetchall()
    
    # Obtener ventas activas (descomponer combos)
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
    
    # Calcular stock disponible para cada producto
    for prod in productos:
        sku = prod['sku']
        nombre = prod['nombre']
        tipo = prod['tipo']
        
        # Stock físico total (DEP + FULL)
        stock_fisico = prod['stock_actual'] + prod['stock_full']
        
        # Ventas activas
        vendido = ventas_dict.get(sku, 0)
        
        # Stock disponible
        stock_disponible = stock_fisico - vendido
        
        # Si quedó sin stock o negativo
        if stock_disponible <= 0:
            productos_sin_stock.append({
                'sku': sku,
                'nombre': nombre,
                'stock_fisico': stock_fisico,
                'vendido': vendido,
                'stock_disponible': stock_disponible
            })
            
            # Verificar si ya existe una alerta pendiente para este producto
            cursor.execute('''
                SELECT id FROM alertas_stock 
                WHERE sku = %s AND estado = 'pendiente'
            ''', (sku,))
            
            alerta_existente = cursor.fetchone()
            
            if not alerta_existente:
                # Crear nueva alerta
                cursor.execute('''
                    INSERT INTO alertas_stock 
                    (sku, nombre_producto, stock_fisico, stock_vendido, stock_disponible, tipo_alerta, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (sku, nombre, stock_fisico, vendido, stock_disponible, 'SIN_STOCK', 'pendiente'))
    
    return productos_sin_stock
