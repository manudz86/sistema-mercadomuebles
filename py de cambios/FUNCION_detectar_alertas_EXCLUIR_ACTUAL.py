# ============================================================================
# FUNCIÓN CORREGIDA: EXCLUIR VENTA ACTUAL
# Reemplazar detectar_alertas_stock_bajo() en app.py
# ============================================================================

def detectar_alertas_stock_bajo(cursor, items_vendidos, venta_id_actual=None):
    """
    Detecta productos con stock disponible <= 0.
    
    Args:
        cursor: Cursor de BD
        items_vendidos: Lista de items de la venta actual
        venta_id_actual: ID de la venta actual para excluirla del cálculo
    
    Returns:
        Lista de productos sin stock
    """
    productos_sin_stock = []
    
    try:
        print("\n" + "="*60)
        print("🔍 DEBUG - DETECTAR ALERTAS")
        print("="*60)
        print(f"Items vendidos: {items_vendidos}")
        print(f"Venta ID actual (excluir): {venta_id_actual}")
        
        # ============================================
        # 1. SKUs A VERIFICAR
        # ============================================
        skus_a_verificar = set()
        cantidades_venta_actual = {}
        
        for item in items_vendidos:
            sku = item['sku']
            cantidad = item['cantidad']
            
            print(f"\n📦 Procesando item: {sku} x{cantidad}")
            
            cursor.execute('SELECT id FROM productos_compuestos WHERE sku = %s', (sku,))
            es_combo = cursor.fetchone()
            
            if es_combo:
                print(f"  → Es COMBO")
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
                print(f"  → Es PRODUCTO BASE")
                skus_a_verificar.add(sku)
                cantidades_venta_actual[sku] = cantidades_venta_actual.get(sku, 0) + cantidad
        
        print(f"\n📋 SKUs a verificar: {skus_a_verificar}")
        print(f"📋 Cantidades venta actual: {cantidades_venta_actual}")
        
        # ============================================
        # 2. VENTAS ACTIVAS (EXCLUYENDO LA ACTUAL)
        # ============================================
        if venta_id_actual:
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
                AND v.id != %s
                GROUP BY sku
            ''', (venta_id_actual,))
        else:
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
        
        print(f"\n📊 Ventas activas en BD (sin venta actual): {ventas_dict}")
        
        # ============================================
        # 3. VERIFICAR CADA SKU
        # ============================================
        skus_sin_stock = []
        
        for sku in skus_a_verificar:
            print(f"\n🔎 Verificando: {sku}")
            
            cursor.execute('''
                SELECT sku, nombre, stock_actual, COALESCE(stock_full, 0) as stock_full, tipo
                FROM productos_base
                WHERE sku = %s
            ''', (sku,))
            
            prod = cursor.fetchone()
            
            if not prod:
                print(f"  ❌ NO EXISTE")
                continue
            
            print(f"  ✅ Encontrado: {prod['nombre']}")
            
            stock_fisico = prod['stock_actual'] + prod['stock_full']
            vendido_anterior = ventas_dict.get(sku, 0)
            vendido_actual = cantidades_venta_actual.get(sku, 0)
            vendido_total = vendido_anterior + vendido_actual
            stock_disponible = stock_fisico - vendido_total
            
            print(f"  📊 Stock físico: {stock_fisico}")
            print(f"  📊 Vendido anterior: {vendido_anterior}")
            print(f"  📊 Vendido actual: {vendido_actual}")
            print(f"  📊 Vendido TOTAL: {vendido_total}")
            print(f"  📊 Disponible: {stock_disponible}")
            
            if stock_disponible <= 0:
                print(f"  ⚠️ SIN STOCK - DEBE ALERTAR")
                
                skus_sin_stock.append(sku)
                
                productos_sin_stock.append({
                    'sku': sku,
                    'nombre': prod['nombre'],
                    'stock_fisico': stock_fisico,
                    'vendido': vendido_total,
                    'stock_disponible': stock_disponible,
                    'tipo_producto': 'base'
                })
                
                # Guardar alerta
                try:
                    cursor.execute('SELECT id FROM alertas_stock WHERE sku = %s AND estado = "pendiente"', (sku,))
                    
                    if not cursor.fetchone():
                        print(f"  💾 Guardando alerta...")
                        cursor.execute('''
                            INSERT INTO alertas_stock 
                            (sku, nombre_producto, stock_fisico, stock_vendido, stock_disponible, tipo_alerta, estado)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ''', (sku, prod['nombre'], stock_fisico, vendido_total, stock_disponible, 'SIN_STOCK', 'pendiente'))
                        print(f"  ✅ Alerta guardada")
                    else:
                        print(f"  ℹ️ Alerta ya existe")
                except Exception as e:
                    print(f"  ❌ Error al guardar alerta: {str(e)}")
            else:
                print(f"  ✅ Stock OK")
        
        # ============================================
        # 4. BUSCAR COMBOS AFECTADOS
        # ============================================
        combos_afectados = []
        
        if skus_sin_stock:
            for sku_sin_stock in skus_sin_stock:
                try:
                    cursor.execute('''
                        SELECT DISTINCT pc.sku as combo_sku, pc.nombre as combo_nombre
                        FROM productos_compuestos pc
                        JOIN componentes c ON pc.id = c.producto_compuesto_id
                        JOIN productos_base pb ON c.producto_base_id = pb.id
                        WHERE pb.sku = %s AND pc.activo = 1
                    ''', (sku_sin_stock,))
                    
                    combos_que_usan = cursor.fetchall()
                    
                    for combo in combos_que_usan:
                        combo_sku = combo['combo_sku']
                        combo_nombre = combo['combo_nombre']
                        
                        if not any(p['sku'] == combo_sku for p in productos_sin_stock):
                            combos_afectados.append({
                                'sku': combo_sku,
                                'nombre': combo_nombre,
                                'componente_faltante': sku_sin_stock,
                                'tipo_producto': 'combo'
                            })
                            
                            try:
                                cursor.execute('SELECT id FROM alertas_stock WHERE sku = %s AND estado = "pendiente"', (combo_sku,))
                                
                                if not cursor.fetchone():
                                    cursor.execute('''
                                        INSERT INTO alertas_stock 
                                        (sku, nombre_producto, stock_fisico, stock_vendido, stock_disponible, tipo_alerta, estado, mlas_afectados)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    ''', (combo_sku, combo_nombre, 0, 0, 0, 'COMBO_SIN_COMPONENTE', 'pendiente', sku_sin_stock))
                            except Exception as e:
                                print(f"  ❌ Error al guardar alerta combo: {str(e)}")
                                
                except Exception as e:
                    print(f"⚠️ Error al buscar combos: {str(e)}")
        
        print(f"\n📋 Total productos sin stock: {len(productos_sin_stock) + len(combos_afectados)}")
        print("="*60 + "\n")
        
        return productos_sin_stock + combos_afectados
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
