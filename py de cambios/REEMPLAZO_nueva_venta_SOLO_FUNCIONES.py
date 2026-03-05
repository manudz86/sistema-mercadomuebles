# ============================================================================
# HELPER PARA JSON (agregar después de las funciones de BD)
# ============================================================================

def decimal_to_float(obj):
    """Convertir Decimals a float para JSON serialization"""
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


# ============================================================================
# NUEVA VENTA CORREGIDO - Reemplazar desde línea 266 hasta antes de dashboard_visual
# ============================================================================

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
        # 3. OBTENER VENTAS ACTIVAS (para calcular disponible)
        # ========================================
        ventas_activas = query_db('''
            SELECT iv.sku, SUM(iv.cantidad) as vendido
            FROM items_venta iv
            JOIN ventas v ON iv.venta_id = v.id
            WHERE v.estado_entrega = 'pendiente'
            GROUP BY iv.sku
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
            
            # Convertir Decimals a tipos nativos y agregar a la lista
            if productos_combos:
                for combo in productos_combos:
                    productos_procesados.append({
                        'sku': combo['sku'],
                        'nombre': combo['nombre'],
                        'tipo': combo['tipo'],
                        'stock': int(combo.get('stock', 0)),
                        'stock_disponible': int(combo.get('stock_disponible', 0)),
                        'tiene_ubicaciones': False,
                        'precio': float(combo.get('precio', 0))
                    })
            
        except Exception as e:
            print(f"Nota: No se pudieron cargar combos - {str(e)}")
            # Continuar sin combos si la tabla no existe
        
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


@app.route('/nueva-venta/guardar', methods=['POST'])
def guardar_venta():
    """Guardar venta SIN descontar stock (solo registra la venta)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # ========================================
        # 1. DATOS GENERALES
        # ========================================
        numero_venta = request.form.get('numero_venta')
        fecha_venta = request.form.get('fecha_venta')
        canal = request.form.get('canal', 'Mercado Libre')
        mla_code = request.form.get('mla_code', '').strip()
        nombre_cliente = request.form.get('nombre_cliente', '').strip()
        
        # Si no hay nombre, usar apodo ML o valor por defecto
        if not nombre_cliente:
            nombre_cliente = mla_code if mla_code else 'Cliente sin especificar'
        
        telefono_cliente = request.form.get('telefono_cliente', '')
        
        # ========================================
        # 2. ENTREGA
        # ========================================
        tipo_entrega = request.form.get('tipo_entrega')
        direccion_entrega = request.form.get('direccion_entrega', '')
        metodo_envio = request.form.get('metodo_envio', '')
        zona_envio = request.form.get('zona_envio', '')
        
        # CALCULAR UBICACIÓN DE DESPACHO
        if metodo_envio == 'Full':
            ubicacion_despacho = 'FULL'
        else:
            ubicacion_despacho = 'DEP'
        
        responsable_entrega = request.form.get('responsable_entrega', '')
        costo_flete = float(request.form.get('costo_flete', 0))
        
        # ========================================
        # 3. PAGO
        # ========================================
        metodo_pago = request.form.get('metodo_pago')
        importe_total = float(request.form.get('importe_total', 0))
        pago_mercadopago = float(request.form.get('pago_mercadopago', 0))
        pago_efectivo = float(request.form.get('pago_efectivo', 0))
        importe_abonado = pago_mercadopago + pago_efectivo
        
        # ========================================
        # 4. OBSERVACIONES
        # ========================================
        notas = request.form.get('notas', '')
        
        # ========================================
        # 5. ESTADO INICIAL
        # ========================================
        estado_entrega = 'pendiente'
        estado_pago = 'pago_pendiente' if importe_abonado < importe_total else 'pagado'
        
        # ========================================
        # 6. INSERTAR VENTA (CON ubicacion_despacho)
        # ========================================
        cursor.execute('''
            INSERT INTO ventas (
                numero_venta, fecha_venta, canal, mla_code,
                nombre_cliente, telefono_cliente,
                tipo_entrega, metodo_envio, ubicacion_despacho,
                zona_envio, direccion_entrega, responsable_entrega,
                costo_flete, metodo_pago, importe_total, importe_abonado,
                pago_mercadopago, pago_efectivo,
                estado_entrega, estado_pago, notas
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        ''', (
            numero_venta, fecha_venta, canal, mla_code,
            nombre_cliente, telefono_cliente,
            tipo_entrega, metodo_envio, ubicacion_despacho,
            zona_envio, direccion_entrega, responsable_entrega,
            costo_flete, metodo_pago, importe_total, importe_abonado,
            pago_mercadopago, pago_efectivo,
            estado_entrega, estado_pago, notas
        ))
        
        venta_id = cursor.lastrowid
        
        # ========================================
        # 7. GUARDAR PRODUCTOS
        # ========================================
        productos = request.form.to_dict(flat=False)
        items_agregados = 0
        
        for key in productos.keys():
            if key.startswith('productos[') and key.endswith('[sku]'):
                index = key.split('[')[1].split(']')[0]
                sku = productos.get(f'productos[{index}][sku]', [None])[0]
                cantidad = int(productos.get(f'productos[{index}][cantidad]', [0])[0])
                precio = float(productos.get(f'productos[{index}][precio]', [0])[0])
                
                if sku and cantidad > 0:
                    # Insertar item de venta
                    cursor.execute('''
                        INSERT INTO items_venta (venta_id, sku, cantidad, precio_unitario)
                        VALUES (%s, %s, %s, %s)
                    ''', (venta_id, sku, cantidad, precio))
                    
                    # ⚠️ NO DESCONTAMOS STOCK AQUÍ
                    # El stock se descuenta cuando la venta pasa a "en_proceso" o "entregada"
                    
                    items_agregados += 1
        
        conn.commit()
        
        mensaje = f'✅ Venta {numero_venta} registrada ({items_agregados} productos)'
        if ubicacion_despacho == 'FULL':
            mensaje += ' - Se despachará desde FULL ML'
        else:
            mensaje += ' - Se despachará desde Depósito'
            
        flash(mensaje, 'success')
        return redirect(url_for('ventas_activas'))
        
    except Exception as e:
        conn.rollback()
        import traceback
        error_completo = traceback.format_exc()
        print(f"ERROR al guardar venta:\n{error_completo}")
        flash(f'❌ Error al guardar venta: {str(e)}', 'error')
        return redirect(url_for('nueva_venta'))
    finally:
        cursor.close()
        conn.close()
