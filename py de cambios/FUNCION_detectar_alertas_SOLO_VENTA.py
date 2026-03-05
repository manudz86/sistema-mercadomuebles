# ============================================================================
# FUNCIÓN: DETECTAR ALERTAS SOLO DE PRODUCTOS VENDIDOS EN ESTA VENTA
# Reemplazar detectar_alertas_stock_bajo() en app.py
# ============================================================================

def detectar_alertas_stock_bajo(cursor, items_vendidos):
    """
    Detecta productos con stock disponible <= 0 SOLO entre los productos vendidos.
    INCLUYE combos que usan componentes que se quedaron sin stock.
    
    Args:
        cursor: Cursor de BD
        items_vendidos: Lista de items de la venta actual
                       [{'sku': 'SDO80', 'cantidad': 1, ...}, ...]
    
    Returns:
        Lista de productos sin stock (solo los relevantes a esta venta)
    """
    productos_sin_stock = []
    combos_afectados = []
    
    try:
        # ============================================
        # 1. EXPANDIR COMBOS A COMPONENTES
        # ============================================
        componentes_vendidos = set()  # SKUs de componentes base vendidos
        
        for item in items_vendidos:
            sku = item['sku']
            cantidad = item['cantidad']
            
            # Verificar si es un combo
            cursor.execute('''
                SELECT id FROM productos_compuestos WHERE sku = %s
            ''', (sku,))
            
            es_combo = cursor.fetchone()
            
            if es_combo:
                # Es un combo - obtener sus componentes
                cursor.execute('''
                    SELECT pb.sku, c.cantidad_necesaria
                    FROM componentes c
                    JOIN productos_base pb ON c.producto_base_id = pb.id
                    WHERE c.producto_compuesto_id = %s
                ''', (es_combo['id'],))
                
                componentes = cursor.fetchall()
                for comp in componentes:
                    componentes_vendidos.add(comp['sku'])
            else:
                # Es producto base
                componentes_vendidos.add(sku)
        
        # ============================================
        # 2. OBTENER VENTAS ACTIVAS TOTALES
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
        # 3. VERIFICAR SOLO LOS COMPONENTES VENDIDOS
        # ============================================
        skus_sin_stock = []
        
        for sku in componentes_vendidos:
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
            vendido = ventas_dict.get(sku, 0)
            stock_disponible = stock_fisico - vendido
            
            # Si quedó sin stock o negativo
            if stock_disponible <= 0:
                skus_sin_stock.append(sku)
                
                productos_sin_stock.append({
                    'sku': sku,
                    'nombre': nombre,
                    'stock_fisico': stock_fisico,
                    'vendido': vendido,
                    'stock_disponible': stock_disponible,
                    'tipo_producto': 'base'
                })
                
                # Verificar si ya existe alerta pendiente
                try:
                    cursor.execute('''
                        SELECT id FROM alertas_stock 
                        WHERE sku = %s AND estado = 'pendiente'
                    ''', (sku,))
                    
                    alerta_existente = cursor.fetchone()
                    
                    if not alerta_existente:
                        cursor.execute('''
                            INSERT INTO alertas_stock 
                            (sku, nombre_producto, stock_fisico, stock_vendido, stock_disponible, tipo_alerta, estado)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ''', (sku, nombre, stock_fisico, vendido, stock_disponible, 'SIN_STOCK', 'pendiente'))
                except Exception as e:
                    print(f"⚠️ No se pudo guardar alerta en BD para {sku}: {str(e)}")
        
        # ============================================
        # 4. BUSCAR COMBOS QUE USAN ESOS COMPONENTES
        # ============================================
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
                        
                        combos_afectados.append({
                            'sku': combo_sku,
                            'nombre': combo_nombre,
                            'componente_faltante': sku_sin_stock,
                            'tipo_producto': 'combo'
                        })
                        
                        # Crear alerta para el combo
                        try:
                            cursor.execute('''
                                SELECT id FROM alertas_stock 
                                WHERE sku = %s AND estado = 'pendiente'
                            ''', (combo_sku,))
                            
                            alerta_combo_existente = cursor.fetchone()
                            
                            if not alerta_combo_existente:
                                cursor.execute('''
                                    INSERT INTO alertas_stock 
                                    (sku, nombre_producto, stock_fisico, stock_vendido, stock_disponible, tipo_alerta, estado, mlas_afectados)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ''', (combo_sku, combo_nombre, 0, 0, 0, 'COMBO_SIN_COMPONENTE', 'pendiente', sku_sin_stock))
                        except Exception as e:
                            print(f"⚠️ No se pudo guardar alerta para combo {combo_sku}: {str(e)}")
                            
                except Exception as e:
                    print(f"⚠️ Error al buscar combos para {sku_sin_stock}: {str(e)}")
        
        # Combinar productos base y combos afectados
        todos_sin_stock = productos_sin_stock + combos_afectados
        
        return todos_sin_stock
        
    except Exception as e:
        print(f"⚠️ Error en detectar_alertas_stock_bajo: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
