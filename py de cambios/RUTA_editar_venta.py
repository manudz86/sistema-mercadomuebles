# ============================================================================
# RUTA: EDITAR VENTA ACTIVA
# Agregar a app.py después de las rutas existentes de ventas
# ============================================================================

@app.route('/ventas/editar/<int:venta_id>', methods=['GET', 'POST'])
def editar_venta(venta_id):
    """Editar una venta activa"""
    
    if request.method == 'GET':
        # Obtener datos de la venta
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Venta principal
        cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('Venta no encontrada', 'error')
            return redirect(url_for('ventas_activas'))
        
        # Items de la venta
        cursor.execute('''
            SELECT iv.*, 
                   COALESCE(pb.nombre, pc.nombre) as nombre_producto
            FROM items_venta iv
            LEFT JOIN productos_base pb ON iv.sku = pb.sku
            LEFT JOIN productos_compuestos pc ON iv.sku = pc.sku
            WHERE iv.venta_id = %s
        ''', (venta_id,))
        items = cursor.fetchall()
        
        # Productos disponibles para agregar
        cursor.execute('''
            SELECT sku, nombre, tipo FROM productos_base
            UNION
            SELECT sku, nombre, 'sommier' as tipo FROM productos_compuestos WHERE activo = 1
            ORDER BY nombre
        ''')
        productos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('editar_venta.html', 
                             venta=venta, 
                             items=items,
                             productos=productos)
    
    # POST - Guardar cambios
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener items ANTES del cambio (para comparar)
        cursor.execute('SELECT sku, cantidad FROM items_venta WHERE venta_id = %s', (venta_id,))
        items_anteriores = {item['sku']: item['cantidad'] for item in cursor.fetchall()}
        
        # ========================================
        # 1. ACTUALIZAR DATOS GENERALES
        # ========================================
        numero_venta = request.form.get('numero_venta')
        fecha_venta = request.form.get('fecha_venta')
        canal = request.form.get('canal')
        mla_code = request.form.get('mla_code', '').strip()
        nombre_cliente = request.form.get('nombre_cliente', '').strip()
        telefono_cliente = request.form.get('telefono_cliente', '')
        
        # Entrega
        tipo_entrega = request.form.get('tipo_entrega')
        direccion_entrega = request.form.get('direccion_entrega', '')
        metodo_envio = request.form.get('metodo_envio', '')
        zona_envio = request.form.get('zona_envio', '')
        
        # Calcular ubicación de despacho
        if metodo_envio == 'Full':
            ubicacion_despacho = 'FULL'
        else:
            ubicacion_despacho = 'DEP'
        
        responsable_entrega = request.form.get('responsable_entrega', '')
        costo_flete = float(request.form.get('costo_flete', 0))
        
        # Pago
        metodo_pago = request.form.get('metodo_pago')
        importe_total = float(request.form.get('importe_total', 0))
        pago_mercadopago = float(request.form.get('pago_mercadopago', 0))
        pago_efectivo = float(request.form.get('pago_efectivo', 0))
        importe_abonado = pago_mercadopago + pago_efectivo
        
        # Estado pago
        estado_pago = 'pago_pendiente' if importe_abonado < importe_total else 'pagado'
        
        # Notas
        notas = request.form.get('notas', '')
        
        # Actualizar venta
        cursor.execute('''
            UPDATE ventas SET
                numero_venta = %s,
                fecha_venta = %s,
                canal = %s,
                mla_code = %s,
                nombre_cliente = %s,
                telefono_cliente = %s,
                tipo_entrega = %s,
                metodo_envio = %s,
                ubicacion_despacho = %s,
                zona_envio = %s,
                direccion_entrega = %s,
                responsable_entrega = %s,
                costo_flete = %s,
                metodo_pago = %s,
                importe_total = %s,
                importe_abonado = %s,
                pago_mercadopago = %s,
                pago_efectivo = %s,
                estado_pago = %s,
                notas = %s
            WHERE id = %s
        ''', (
            numero_venta, fecha_venta, canal, mla_code,
            nombre_cliente, telefono_cliente,
            tipo_entrega, metodo_envio, ubicacion_despacho,
            zona_envio, direccion_entrega, responsable_entrega,
            costo_flete, metodo_pago, importe_total, importe_abonado,
            pago_mercadopago, pago_efectivo,
            estado_pago, notas,
            venta_id
        ))
        
        # ========================================
        # 2. ACTUALIZAR ITEMS (Si cambiaron)
        # ========================================
        # Borrar items existentes
        cursor.execute('DELETE FROM items_venta WHERE venta_id = %s', (venta_id,))
        
        # Insertar items nuevos
        productos = request.form.to_dict(flat=False)
        items_nuevos = {}
        
        for key in productos.keys():
            if key.startswith('productos[') and key.endswith('[sku]'):
                index = key.split('[')[1].split(']')[0]
                sku = productos.get(f'productos[{index}][sku]', [None])[0]
                cantidad = int(productos.get(f'productos[{index}][cantidad]', [0])[0])
                precio = float(productos.get(f'productos[{index}][precio]', [0])[0])
                
                if sku and cantidad > 0:
                    # Insertar item
                    cursor.execute('''
                        INSERT INTO items_venta (venta_id, sku, cantidad, precio_unitario)
                        VALUES (%s, %s, %s, %s)
                    ''', (venta_id, sku, cantidad, precio))
                    
                    items_nuevos[sku] = cantidad
        
        # ========================================
        # 3. DETECTAR ALERTAS (Solo si cambiaron items)
        # ========================================
        items_cambiaron = items_anteriores != items_nuevos
        
        if items_cambiaron:
            try:
                items_vendidos_lista = [{'sku': sku, 'cantidad': cant} for sku, cant in items_nuevos.items()]
                if items_vendidos_lista:
                    productos_sin_stock = detectar_alertas_stock_bajo(cursor, items_vendidos_lista, venta_id)
                    
                    if productos_sin_stock:
                        # Mostrar alerta (simplificado)
                        productos_base = [p for p in productos_sin_stock if p.get('tipo_producto') == 'base']
                        if productos_base:
                            nombres = ', '.join([p['nombre'] for p in productos_base[:3]])
                            flash(f'⚠️ Productos sin stock: {nombres}', 'warning')
            except Exception as e:
                print(f"Error al detectar alertas: {str(e)}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash(f'✅ Venta {numero_venta} actualizada correctamente', 'success')
        return redirect(url_for('ventas_activas'))
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        import traceback
        traceback.print_exc()
        flash(f'❌ Error al actualizar venta: {str(e)}', 'error')
        return redirect(url_for('ventas_activas'))
