@app.route('/nueva-venta')
def nueva_venta():
    """Formulario para registrar venta con stock disponible y ubicaciones"""
    from datetime import date
    import json
    
    try:
        # ========================================
        # 1. GENERAR SIGUIENTE NÚMERO DE VENTA
        # ========================================
        ultima_venta = query_db('SELECT numero_venta FROM ventas ORDER BY id DESC LIMIT 1')
        siguiente_numero = 'VENTA-001'
        
        if ultima_venta and len(ultima_venta) > 0:
            num_venta = ultima_venta[0].get('numero_venta')
            if num_venta and '-' in num_venta:
                try:
                    ultimo_num = int(num_venta.split('-')[1])
                    siguiente_numero = f'VENTA-{ultimo_num + 1:03d}'
                except (ValueError, IndexError):
                    siguiente_numero = 'VENTA-001'
        
        # ========================================
        # 2. OBTENER STOCK FÍSICO (con ubicaciones)
        # ========================================
        productos_base = query_db('''
            SELECT 
                sku, 
                nombre, 
                tipo, 
                stock_actual,
                COALESCE(stock_full, 0) as stock_full
            FROM productos_base 
            ORDER BY tipo, nombre
        ''')
        
        # ========================================
        # 3. OBTENER VENTAS ACTIVAS (DESCOMPONIENDO COMBOS)
        # ========================================
        ventas_activas = query_db('''
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
        
        # Convertir a diccionario
        ventas_dict = {v['sku']: int(v['vendido']) for v in ventas_activas}
        
        # ========================================
        # 4. CALCULAR STOCK DISPONIBLE
        # ========================================
        productos_procesados = []
        
        for prod in productos_base:
            sku = prod['sku']
            vendido = ventas_dict.get(sku, 0)
            
            # Para productos con ubicaciones
            if '_DEP' in sku or '_FULL' in sku:
                # Compac: tiene _DEP y _FULL separados
                stock_fisico = int(prod['stock_actual'])
                stock_disponible_dep = stock_fisico - vendido
                
                productos_procesados.append({
                    'sku': sku,
                    'nombre': prod['nombre'],
                    'tipo': prod['tipo'],
                    'stock': stock_fisico,
                    'stock_disponible': stock_disponible_dep,
                    'tiene_ubicaciones': True,
                    'ubicacion': 'DEP' if '_DEP' in sku else 'FULL',
                    'precio': 0
                })
                
            elif prod['tipo'] == 'almohada':
                # Almohadas: tienen stock_actual (DEP) y stock_full (FULL)
                stock_dep = int(prod['stock_actual'])
                stock_full = int(prod['stock_full'])
                stock_total = stock_dep + stock_full
                stock_disponible = stock_total - vendido
                
                productos_procesados.append({
                    'sku': sku,
                    'nombre': prod['nombre'],
                    'tipo': prod['tipo'],
                    'stock': stock_total,
                    'stock_dep': stock_dep,
                    'stock_full': stock_full,
                    'stock_disponible': stock_disponible,
                    'tiene_ubicaciones': True,
                    'precio': 0
                })
                
            else:
                # Otros productos: solo stock_actual
                stock_fisico = int(prod['stock_actual'])
                stock_disponible = stock_fisico - vendido
                
                productos_procesados.append({
                    'sku': sku,
                    'nombre': prod['nombre'],
                    'tipo': prod['tipo'],
                    'stock': stock_fisico,
                    'stock_disponible': stock_disponible,
                    'tiene_ubicaciones': False,
                    'precio': 0
                })
        
        # ========================================
        # 5. OBTENER COMBOS/SOMMIERS
        # ========================================
        try:
            productos_combos = query_db('''
                SELECT 
                    sku, 
                    nombre, 
                    'combo' as tipo,
                    0 as stock,
                    0 as stock_disponible,
                    0 as precio
                FROM productos_compuestos
                WHERE activo = 1
                ORDER BY nombre
            ''')
            
            # Para cada combo, calcular su disponibilidad según componentes
            if productos_combos:
                for combo in productos_combos:
                    # Obtener componentes del combo usando IDs
                    componentes = query_db('''
                        SELECT pb.sku, c.cantidad_necesaria 
                        FROM componentes c
                        JOIN productos_base pb ON c.producto_base_id = pb.id
                        JOIN productos_compuestos pc ON c.producto_compuesto_id = pc.id
                        WHERE pc.sku = %s
                    ''', (combo['sku'],))
                    
                    # Calcular cuántos combos se pueden armar con el stock disponible
                    stock_disponible_combo = 999999  # Empezar con infinito
                    
                    for comp in componentes:
                        sku_comp = comp['sku']
                        cant_necesaria = int(comp['cantidad_necesaria'])
                        
                        # Buscar el stock disponible de este componente
                        prod_comp = next((p for p in productos_procesados if p['sku'] == sku_comp), None)
                        if prod_comp:
                            stock_disp_comp = prod_comp['stock_disponible']
                            # Cuántos combos se pueden hacer con este componente
                            combos_posibles = stock_disp_comp // cant_necesaria if cant_necesaria > 0 else 0
                            # El mínimo define cuántos combos se pueden armar
                            stock_disponible_combo = min(stock_disponible_combo, combos_posibles)
                        else:
                            # Si no existe el componente, no se puede armar el combo
                            stock_disponible_combo = 0
                            break
                    
                    # Si no hay componentes o todos dan infinito, poner 0
                    if stock_disponible_combo == 999999 or stock_disponible_combo < 0:
                        stock_disponible_combo = 0
                    
                    productos_procesados.append({
                        'sku': combo['sku'],
                        'nombre': combo['nombre'],
                        'tipo': combo['tipo'],
                        'stock': 0,  # Los combos no tienen stock físico
                        'stock_disponible': stock_disponible_combo,
                        'tiene_ubicaciones': False,
                        'precio': float(combo.get('precio', 0))
                    })
            
        except Exception as e:
            print(f"Nota: No se pudieron cargar combos - {str(e)}")
            import traceback
            traceback.print_exc()
        
        # ========================================
        # 6. CONVERTIR A JSON (SIN DECIMALS)
        # ========================================
        productos_json = json.dumps(productos_procesados)
        
        return render_template('nueva_venta.html',
                             siguiente_numero=siguiente_numero,
                             fecha_hoy=date.today().strftime('%Y-%m-%d'),
                             productos_json=productos_json)
                             
    except Exception as e:
        import traceback
        error_completo = traceback.format_exc()
        flash(f'Error al cargar Nueva Venta: {str(e)}', 'error')
        print(f"ERROR en nueva_venta:\n{error_completo}")
        return redirect(url_for('index'))
