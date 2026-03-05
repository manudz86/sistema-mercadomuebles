# ============================================================================
# FUNCIÓN TEMPORAL: detectar_alertas_stock_bajo CON PROTECCIÓN
# Usar esta versión TEMPORALMENTE mientras arreglás la tabla
# ============================================================================

def detectar_alertas_stock_bajo(cursor):
    """
    Detecta productos con stock disponible <= 0 y crea alertas.
    INCLUYE combos que usan componentes sin stock.
    
    Versión con try-catch para no romper si la tabla no está lista.
    """
    productos_sin_stock = []
    combos_afectados = []
    
    try:
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
        skus_sin_stock = []
        
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
                skus_sin_stock.append(sku)
                
                productos_sin_stock.append({
                    'sku': sku,
                    'nombre': nombre,
                    'stock_fisico': stock_fisico,
                    'vendido': vendido,
                    'stock_disponible': stock_disponible,
                    'tipo_producto': 'base'
                })
                
                # Intentar crear alerta en BD (puede fallar si tabla no existe)
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
                    # Si falla, solo loguear pero no romper
                    print(f"⚠️ No se pudo guardar alerta en BD para {sku}: {str(e)}")
                    pass
        
        # ============================================
        # 4. DETECTAR COMBOS QUE USAN ESOS COMPONENTES
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
                        
                        # Intentar crear alerta en BD
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
                            print(f"⚠️ No se pudo guardar alerta en BD para combo {combo_sku}: {str(e)}")
                            pass
                            
                except Exception as e:
                    print(f"⚠️ Error al buscar combos para {sku_sin_stock}: {str(e)}")
                    pass
        
        # Combinar productos base y combos afectados
        todos_sin_stock = productos_sin_stock + combos_afectados
        
        return todos_sin_stock
        
    except Exception as e:
        # Si falla todo, retornar lista vacía para no romper la venta
        print(f"⚠️ Error en detectar_alertas_stock_bajo: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
