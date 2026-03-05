# ============================================================================
# FUNCIÓN MEJORADA: DETECTAR ALERTAS INCLUYENDO COMBOS AFECTADOS
# Reemplazar la función detectar_alertas_stock_bajo() en app.py
# ============================================================================

def detectar_alertas_stock_bajo(cursor):
    """
    Detecta productos con stock disponible <= 0 y crea alertas.
    INCLUYE combos que usan componentes sin stock.
    
    Stock disponible = Stock físico - Ventas activas
    """
    productos_sin_stock = []
    combos_afectados = []
    
    # ============================================
    # 1. OBTENER STOCK FÍSICO DE PRODUCTOS BASE
    # ============================================
    cursor.execute('''
        SELECT sku, nombre, stock_actual, COALESCE(stock_full, 0) as stock_full, tipo
        FROM productos_base
        WHERE tipo IN ('colchon', 'base', 'almohada')
    ''')
    productos = cursor.fetchall()
    
    # ============================================
    # 2. OBTENER VENTAS ACTIVAS (descomponer combos)
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
    # 3. DETECTAR PRODUCTOS BASE SIN STOCK
    # ============================================
    skus_sin_stock = []  # Lista de SKUs sin stock para buscar combos después
    
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
            skus_sin_stock.append(sku)  # Guardar para buscar combos
            
            productos_sin_stock.append({
                'sku': sku,
                'nombre': nombre,
                'stock_fisico': stock_fisico,
                'vendido': vendido,
                'stock_disponible': stock_disponible,
                'tipo_producto': 'base'
            })
            
            # Verificar si ya existe alerta pendiente
            cursor.execute('''
                SELECT id FROM alertas_stock 
                WHERE sku = %s AND estado = 'pendiente'
            ''', (sku,))
            
            alerta_existente = cursor.fetchone()
            
            if not alerta_existente:
                # Crear alerta para producto base
                cursor.execute('''
                    INSERT INTO alertas_stock 
                    (sku, nombre_producto, stock_fisico, stock_vendido, stock_disponible, tipo_alerta, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (sku, nombre, stock_fisico, vendido, stock_disponible, 'SIN_STOCK', 'pendiente'))
    
    # ============================================
    # 4. DETECTAR COMBOS QUE USAN ESOS COMPONENTES
    # ============================================
    if skus_sin_stock:
        # Para cada SKU sin stock, buscar combos que lo usan
        for sku_sin_stock in skus_sin_stock:
            cursor.execute('''
                SELECT DISTINCT
                    pc.sku as combo_sku,
                    pc.nombre as combo_nombre
                FROM productos_compuestos pc
                JOIN componentes c ON pc.id = c.producto_compuesto_id
                JOIN productos_base pb ON c.producto_base_id = pb.id
                WHERE pb.sku = %s
                AND pc.activo = 1
            ''', (sku_sin_stock,))
            
            combos_que_usan = cursor.fetchall()
            
            for combo in combos_que_usan:
                combo_sku = combo['combo_sku']
                combo_nombre = combo['combo_nombre']
                
                # Agregar a lista de combos afectados
                combos_afectados.append({
                    'sku': combo_sku,
                    'nombre': combo_nombre,
                    'componente_faltante': sku_sin_stock,
                    'tipo_producto': 'combo'
                })
                
                # Verificar si ya existe alerta pendiente para este combo
                cursor.execute('''
                    SELECT id FROM alertas_stock 
                    WHERE sku = %s AND estado = 'pendiente'
                ''', (combo_sku,))
                
                alerta_combo_existente = cursor.fetchone()
                
                if not alerta_combo_existente:
                    # Crear alerta para el combo
                    cursor.execute('''
                        INSERT INTO alertas_stock 
                        (sku, nombre_producto, stock_fisico, stock_vendido, stock_disponible, tipo_alerta, estado, mlas_afectados)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (combo_sku, combo_nombre, 0, 0, 0, 'COMBO_SIN_COMPONENTE', 'pendiente', sku_sin_stock))
    
    # ============================================
    # 5. RETORNAR AMBAS LISTAS
    # ============================================
    # Combinar productos base y combos afectados
    todos_sin_stock = productos_sin_stock + combos_afectados
    
    return todos_sin_stock
