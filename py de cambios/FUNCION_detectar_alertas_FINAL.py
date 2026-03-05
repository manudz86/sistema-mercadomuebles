# ============================================================================
# FUNCIÓN CORREGIDA: CUENTA LA VENTA ACTUAL
# Reemplazar detectar_alertas_stock_bajo() en app.py
# ============================================================================

def detectar_alertas_stock_bajo(cursor, items_vendidos):
    """
    Detecta productos con stock disponible <= 0.
    INCLUYE la venta actual en el cálculo de "vendido".
    
    Args:
        cursor: Cursor de BD
        items_vendidos: Lista de items de la venta actual
    
    Returns:
        Lista de productos sin stock
    """
    productos_sin_stock = []
    
    try:
        # ============================================
        # 1. OBTENER SKUs A VERIFICAR Y CANTIDADES DE VENTA ACTUAL
        # ============================================
        skus_a_verificar = set()
        cantidades_venta_actual = {}  # {sku: cantidad} de la venta que se está guardando
        
        for item in items_vendidos:
            sku = item['sku']
            cantidad = item['cantidad']
            
            # Verificar si es combo
            cursor.execute('''
                SELECT id FROM productos_compuestos WHERE sku = %s
            ''', (sku,))
            
            es_combo = cursor.fetchone()
            
            if es_combo:
                # Es combo - descomponer en componentes
                cursor.execute('''
                    SELECT pb.sku, c.cantidad_necesaria
                    FROM componentes c
                    JOIN productos_base pb ON c.producto_base_id = pb.id
                    WHERE c.producto_compuesto_id = %s
                ''', (es_combo['id'],))
                
                componentes = cursor.fetchall()
                for comp in componentes:
                    comp_sku = comp['sku']
                    comp_cant = comp['cantidad_necesaria'] * cantidad
                    
                    skus_a_verificar.add(comp_sku)
                    cantidades_venta_actual[comp_sku] = cantidades_venta_actual.get(comp_sku, 0) + comp_cant
            else:
                # Es producto base
                skus_a_verificar.add(sku)
                cantidades_venta_actual[sku] = cantidades_venta_actual.get(sku, 0) + cantidad
        
        # ============================================
        # 2. OBTENER VENTAS ACTIVAS (SIN LA ACTUAL)
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
        # 3. VERIFICAR CADA SKU (SUMANDO VENTA ACTUAL)
        # ============================================
        skus_sin_stock = []
        
        for sku in skus_a_verificar:
            # Obtener stock físico
            cursor.execute('''
                SELECT sku, nombre, stock_actual, COALESCE(stock_full, 0) as stock_full, tipo
                FROM productos_base
                WHERE sku = %s
            ''', (sku,))
            
            prod = cursor.fetchone()
            
            if not prod:
                continue
            
            nombre = prod['nombre']
            stock_fisico = prod['stock_actual'] + prod['stock_full']
            
            # Vendido TOTAL = ventas anteriores + venta actual
            vendido_anterior = ventas_dict.get(sku, 0)
            vendido_actual = cantidades_venta_actual.get(sku, 0)
            vendido_total = vendido_anterior + vendido_actual
            
            stock_disponible = stock_fisico - vendido_total
            
            # Si quedó sin stock o negativo
            if stock_disponible <= 0:
                skus_sin_stock.append(sku)
                
                productos_sin_stock.append({
                    'sku': sku,
                    'nombre': nombre,
                    'stock_fisico': stock_fisico,
                    'vendido': vendido_total,
                    'stock_disponible': stock_disponible,
                    'tipo_producto': 'base'
                })
                
                # Guardar alerta
                try:
                    cursor.execute('''
                        SELECT id FROM alertas_stock 
                        WHERE sku = %s AND estado = 'pendiente'
                    ''', (sku,))
                    
                    if not cursor.fetchone():
                        cursor.execute('''
                            INSERT INTO alertas_stock 
                            (sku, nombre_producto, stock_fisico, stock_vendido, stock_disponible, tipo_alerta, estado)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ''', (sku, nombre, stock_fisico, vendido_total, stock_disponible, 'SIN_STOCK', 'pendiente'))
                except Exception as e:
                    print(f"⚠️ No se pudo guardar alerta para {sku}: {str(e)}")
        
        # ============================================
        # 4. BUSCAR COMBOS AFECTADOS
        # ============================================
        combos_afectados = []
        
        if skus_sin_stock:
            for sku_sin_stock in skus_sin_stock:
                try:
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
                        
                        # Evitar duplicados
                        if not any(p['sku'] == combo_sku for p in productos_sin_stock):
                            combos_afectados.append({
                                'sku': combo_sku,
                                'nombre': combo_nombre,
                                'componente_faltante': sku_sin_stock,
                                'tipo_producto': 'combo'
                            })
                            
                            # Guardar alerta
                            try:
                                cursor.execute('''
                                    SELECT id FROM alertas_stock 
                                    WHERE sku = %s AND estado = 'pendiente'
                                ''', (combo_sku,))
                                
                                if not cursor.fetchone():
                                    cursor.execute('''
                                        INSERT INTO alertas_stock 
                                        (sku, nombre_producto, stock_fisico, stock_vendido, stock_disponible, tipo_alerta, estado, mlas_afectados)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    ''', (combo_sku, combo_nombre, 0, 0, 0, 'COMBO_SIN_COMPONENTE', 'pendiente', sku_sin_stock))
                            except Exception as e:
                                print(f"⚠️ No se pudo guardar alerta para combo {combo_sku}: {str(e)}")
                                
                except Exception as e:
                    print(f"⚠️ Error al buscar combos para {sku_sin_stock}: {str(e)}")
        
        # Combinar todo
        todos_sin_stock = productos_sin_stock + combos_afectados
        
        return todos_sin_stock
        
    except Exception as e:
        print(f"⚠️ Error en detectar_alertas_stock_bajo: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
