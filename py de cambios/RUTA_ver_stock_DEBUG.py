@app.route('/stock')
def ver_stock():
    """Ver stock disponible con filtros - PRODUCTOS BASE + COMBOS - VERSION DEBUG"""
    productos = []
    filtro_estado = request.args.get('estado', 'TODOS')
    filtro_tipo = request.args.get('tipo', 'TODOS')
    filtro_modelo = request.args.get('modelo', 'TODOS')
    filtro_medida = request.args.get('medida', 'TODAS')
    buscar = request.args.get('buscar', '').strip()
    
    print("\n" + "="*60)
    print("🔍 DEBUG - VER STOCK")
    print("="*60)
    print(f"Filtros: estado={filtro_estado}, tipo={filtro_tipo}, medida={filtro_medida}, modelo={filtro_modelo}")
    print(f"Buscar: '{buscar}'")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ============================================
        # 1. VENTAS ACTIVAS
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
        print(f"\n📊 Ventas activas: {len(ventas_dict)} SKUs")
        
        # ============================================
        # 2. PRODUCTOS BASE
        # ============================================
        query_productos = """
            SELECT 
                sku, nombre, tipo, medida, modelo,
                stock_actual, COALESCE(stock_full, 0) as stock_full
            FROM productos_base
            WHERE 1=1
        """
        params = []
        
        if filtro_tipo != 'TODOS' and filtro_tipo in ('colchon', 'base', 'almohada'):
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
        
        cursor.execute(query_productos, tuple(params) if params else None)
        productos_base = cursor.fetchall()
        
        print(f"\n📦 Productos base encontrados: {len(productos_base)}")
        
        productos_base_agregados = 0
        for prod in productos_base:
            sku = prod['sku']
            stock_fisico = prod['stock_actual'] + prod['stock_full']
            vendido = ventas_dict.get(sku, 0)
            stock_disponible = stock_fisico - vendido
            
            if stock_disponible <= 0:
                estado_stock = 'SIN_STOCK'
            elif stock_disponible <= 2:
                estado_stock = 'POCO_STOCK'
            else:
                estado_stock = 'DISPONIBLE'
            
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
                'estado_stock': estado_stock,
                'es_combo': False
            })
            productos_base_agregados += 1
        
        print(f"✅ Productos base agregados (después de filtros): {productos_base_agregados}")
        
        # ============================================
        # 3. COMBOS
        # ============================================
        print(f"\n🔷 Procesando combos...")
        print(f"   Filtro tipo: '{filtro_tipo}'")
        print(f"   ¿Debe mostrar combos? {filtro_tipo == 'TODOS' or filtro_tipo == 'sommier'}")
        
        if filtro_tipo == 'TODOS' or filtro_tipo == 'sommier':
            query_combos = """
                SELECT id, sku, nombre, medida, modelo
                FROM productos_compuestos
                WHERE activo = 1
            """
            params_combos = []
            
            if filtro_medida != 'TODAS':
                query_combos += " AND medida = %s"
                params_combos.append(filtro_medida)
            
            if filtro_modelo != 'TODOS':
                query_combos += " AND (nombre LIKE %s OR modelo LIKE %s)"
                params_combos.append(f'%{filtro_modelo}%')
                params_combos.append(f'%{filtro_modelo}%')
            
            if buscar:
                query_combos += " AND (sku LIKE %s OR nombre LIKE %s)"
                params_combos.append(f'%{buscar}%')
                params_combos.append(f'%{buscar}%')
            
            cursor.execute(query_combos, tuple(params_combos) if params_combos else None)
            combos = cursor.fetchall()
            
            print(f"   📋 Combos encontrados en BD: {len(combos)}")
            
            combos_agregados = 0
            for combo in combos:
                combo_id = combo['id']
                combo_sku = combo['sku']
                
                print(f"\n   🔎 Procesando combo: {combo_sku} - {combo['nombre']}")
                
                # Obtener componentes
                cursor.execute('''
                    SELECT pb.sku, pb.stock_actual, COALESCE(pb.stock_full, 0) as stock_full,
                           c.cantidad_necesaria
                    FROM componentes c
                    JOIN productos_base pb ON c.producto_base_id = pb.id
                    WHERE c.producto_compuesto_id = %s
                ''', (combo_id,))
                
                componentes = cursor.fetchall()
                
                print(f"      Componentes: {len(componentes)}")
                
                if not componentes:
                    print(f"      ⚠️ Sin componentes - SKIP")
                    continue
                
                # Calcular stock disponible
                stock_disponible_combo = float('inf')
                
                for comp in componentes:
                    comp_sku = comp['sku']
                    comp_stock_fisico = comp['stock_actual'] + comp['stock_full']
                    comp_vendido = ventas_dict.get(comp_sku, 0)
                    comp_stock_disponible = comp_stock_fisico - comp_vendido
                    combos_posibles = comp_stock_disponible // comp['cantidad_necesaria']
                    
                    print(f"      - {comp_sku}: Stock {comp_stock_disponible} / Necesita {comp['cantidad_necesaria']} = {combos_posibles} combos")
                    
                    stock_disponible_combo = min(stock_disponible_combo, combos_posibles)
                
                stock_disponible_combo = int(stock_disponible_combo) if stock_disponible_combo != float('inf') else 0
                
                print(f"      📊 Stock disponible del combo: {stock_disponible_combo}")
                
                # Estado
                if stock_disponible_combo <= 0:
                    estado_stock = 'SIN_STOCK'
                elif stock_disponible_combo <= 2:
                    estado_stock = 'POCO_STOCK'
                else:
                    estado_stock = 'DISPONIBLE'
                
                print(f"      Estado: {estado_stock}")
                
                # Filtro por estado
                if filtro_estado != 'TODOS' and estado_stock != filtro_estado:
                    print(f"      ❌ Filtrado por estado (necesita {filtro_estado}, es {estado_stock})")
                    continue
                
                print(f"      ✅ AGREGADO")
                
                productos.append({
                    'sku': combo_sku,
                    'nombre': combo['nombre'],
                    'tipo': 'sommier',
                    'medida': combo['medida'],
                    'modelo': combo['modelo'],
                    'stock_fisico': '-',
                    'stock_disponible': stock_disponible_combo,
                    'estado_stock': estado_stock,
                    'es_combo': True
                })
                combos_agregados += 1
            
            print(f"\n   ✅ Combos agregados (después de filtros): {combos_agregados}")
        
        # Ordenar
        productos.sort(key=lambda x: (x['tipo'], x['nombre'], x['medida'] or ''))
        
        print(f"\n📋 TOTAL PRODUCTOS EN LISTA: {len(productos)}")
        print("="*60 + "\n")
        
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
