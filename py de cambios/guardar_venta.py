@app.route('/nueva-venta/guardar', methods=['POST'])
def guardar_venta():
    """Guardar venta SIN descontar stock (solo registra la venta)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        from flask import session
        from datetime import datetime
        
        # ========================================
        # FECHA DE VENTA
        # ========================================
        fecha_venta_iso = session.get('ml_fecha_venta')
        if fecha_venta_iso:
            fecha_venta = datetime.fromisoformat(fecha_venta_iso)
            print(f"✅ Usando fecha de ML: {fecha_venta}")
        else:
            fecha_venta_form = request.form.get('fecha_venta')
            fecha_venta = datetime.strptime(fecha_venta_form, '%Y-%m-%d') if fecha_venta_form else datetime.now()
            print(f"✅ Usando fecha del formulario: {fecha_venta}")
        
        # ========================================
        # 1. DATOS GENERALES
        # ========================================
        numero_venta = request.form.get('numero_venta')
        canal = request.form.get('canal', 'Mercado Libre')
        mla_code = request.form.get('mla_code', '').strip()
        nombre_cliente = request.form.get('nombre_cliente', '').strip()
        
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
        
        if metodo_envio == 'Full':
            ubicacion_despacho = 'FULL'
        else:
            ubicacion_despacho = 'DEP'
        
        responsable_entrega = request.form.get('responsable_entrega', '')
        costo_flete = float(request.form.get('costo_flete', 0))
        
        # ========================================
        # 3. PRODUCTOS - calcular importe_total desde items reales
        # ========================================
        productos_form = request.form.to_dict(flat=False)
        importe_total = 0.0
        
        for key in productos_form.keys():
            if key.startswith('productos[') and key.endswith('[sku]'):
                index = key.split('[')[1].split(']')[0]
                sku = productos_form.get(f'productos[{index}][sku]', [None])[0]
                cantidad = int(productos_form.get(f'productos[{index}][cantidad]', [0])[0])
                precio = float(productos_form.get(f'productos[{index}][precio]', [0])[0])
                if sku and cantidad > 0:
                    importe_total += cantidad * precio
        
        print(f"✅ importe_total calculado desde items: ${importe_total}")
        
        # ========================================
        # 4. PAGO
        # ========================================
        metodo_pago = request.form.get('metodo_pago')
        pago_mercadopago = float(request.form.get('pago_mercadopago', 0))
        pago_efectivo = float(request.form.get('pago_efectivo', 0))
        
        # Para Flete Propio y Zippin de ML, el cliente paga productos + flete por MP
        if canal == 'Mercado Libre' and metodo_envio in ['Flete Propio', 'Zippin'] and costo_flete > 0:
            pago_mercadopago += costo_flete
            print(f"✅ Sumando flete a pago_mercadopago: +${costo_flete} → total ${pago_mercadopago}")
        
        importe_abonado = pago_mercadopago + pago_efectivo
        
        print(f"✅ pago_mercadopago: ${pago_mercadopago}")
        print(f"✅ pago_efectivo: ${pago_efectivo}")
        print(f"✅ importe_abonado: ${importe_abonado}")
        
        # ========================================
        # 5. DATOS DE FACTURACIÓN
        # ========================================
        ml_billing_data = session.get('ml_billing_data')
        billing_info = {
            'business_name': None,
            'doc_type': None,
            'doc_number': None,
            'taxpayer_type': None,
            'city': None,
            'street': None,
            'state': None,
            'zip_code': None
        }
        
        if ml_billing_data:
            billing_info = extraer_billing_info_ml(ml_billing_data)
        
        # ========================================
        # 6. OBSERVACIONES Y ESTADO
        # ========================================
        notas = request.form.get('notas', '')
        estado_entrega = 'pendiente'
        estado_pago = 'pago_pendiente' if importe_abonado < importe_total else 'pagado'
        
        # ========================================
        # 7. INSERTAR VENTA
        # ========================================
        cursor.execute('''
            INSERT INTO ventas (
                numero_venta, fecha_venta, canal, mla_code,
                nombre_cliente, telefono_cliente,
                tipo_entrega, metodo_envio, ubicacion_despacho,
                zona_envio, direccion_entrega, responsable_entrega,
                costo_flete, metodo_pago, importe_total, importe_abonado,
                pago_mercadopago, pago_efectivo,
                estado_entrega, estado_pago, notas,
                factura_business_name, factura_doc_type, factura_doc_number,
                factura_taxpayer_type, factura_city, factura_street,
                factura_state, factura_zip_code
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        ''', (
            numero_venta, fecha_venta, canal, mla_code,
            nombre_cliente, telefono_cliente,
            tipo_entrega, metodo_envio, ubicacion_despacho,
            zona_envio, direccion_entrega, responsable_entrega,
            costo_flete, metodo_pago, importe_total, importe_abonado,
            pago_mercadopago, pago_efectivo,
            estado_entrega, estado_pago, notas,
            billing_info['business_name'],
            billing_info['doc_type'],
            billing_info['doc_number'],
            billing_info['taxpayer_type'],
            billing_info['city'],
            billing_info['street'],
            billing_info['state'],
            billing_info['zip_code']
        ))
        
        venta_id = cursor.lastrowid
        
        # ========================================
        # 8. GUARDAR PRODUCTOS
        # ========================================
        items_agregados = 0
        
        for key in productos_form.keys():
            if key.startswith('productos[') and key.endswith('[sku]'):
                index = key.split('[')[1].split(']')[0]
                sku = productos_form.get(f'productos[{index}][sku]', [None])[0]
                cantidad = int(productos_form.get(f'productos[{index}][cantidad]', [0])[0])
                precio = float(productos_form.get(f'productos[{index}][precio]', [0])[0])
                
                if sku and cantidad > 0:
                    cursor.execute('''
                        INSERT INTO items_venta (venta_id, sku, cantidad, precio_unitario)
                        VALUES (%s, %s, %s, %s)
                    ''', (venta_id, sku, cantidad, precio))
                    items_agregados += 1
        
        conn.commit()
        
        # ========================================
        # 9. DETECTAR ALERTAS DE STOCK
        # ========================================
        productos_sin_stock = []
        try:
            items_vendidos_lista = []
            for key in productos_form.keys():
                if key.startswith('productos[') and key.endswith('[sku]'):
                    index = key.split('[')[1].split(']')[0]
                    sku = productos_form.get(f'productos[{index}][sku]', [None])[0]
                    cantidad = int(productos_form.get(f'productos[{index}][cantidad]', [0])[0])
                    if sku and cantidad > 0:
                        items_vendidos_lista.append({'sku': sku, 'cantidad': cantidad})
            
            if items_vendidos_lista:
                productos_sin_stock = detectar_alertas_stock_bajo(cursor, items_vendidos_lista, venta_id)
        except Exception as e_alertas:
            print(f"⚠️ Error al detectar alertas: {str(e_alertas)}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # ========================================
        # 10. LIMPIAR SESIÓN DE ML
        # ========================================
        session.pop('ml_orden_id', None)
        session.pop('ml_items', None)
        session.pop('ml_comprador_nombre', None)
        session.pop('ml_comprador_nickname', None)
        session.pop('ml_shipping', None)
        session.pop('ml_fecha_venta', None)
        session.pop('ml_billing_data', None)
        
        # ========================================
        # 11. MENSAJE Y REDIRECCIÓN
        # ========================================
        if productos_sin_stock:
            productos_base = [p for p in productos_sin_stock if p.get('tipo_producto') == 'base']
            combos_afectados = [p for p in productos_sin_stock if p.get('tipo_producto') == 'combo']
            
            mensaje_html = f'''
                <div class="alert alert-success mb-3">
                    <strong>✅ Venta {numero_venta} registrada correctamente</strong>
                </div>
                <div class="alert alert-warning">
                    <h5><i class="bi bi-exclamation-triangle-fill"></i> ⚠️ Alerta de Stock ML</h5>
            '''
            
            if productos_base:
                mensaje_html += '<p class="mb-2"><strong>Productos base sin stock disponible:</strong></p><ul class="mb-3">'
                for prod in productos_base:
                    mensaje_html += f'''
                        <li><strong>{prod['nombre']}</strong> (SKU: {prod['sku']})<br>
                            <small>Stock físico: {prod['stock_fisico']} | Vendido: {prod['vendido']} | Disponible: <span class="text-danger">{prod['stock_disponible']}</span></small>
                        </li>
                    '''
                mensaje_html += '</ul>'
            
            if combos_afectados:
                mensaje_html += '<p class="mb-2"><strong>Combos/Sommiers que NO se pueden armar:</strong></p><ul class="mb-3">'
                for combo in combos_afectados:
                    mensaje_html += f'''
                        <li><strong>{combo['nombre']}</strong> (SKU: {combo['sku']})<br>
                            <small class="text-muted">Falta componente: {combo.get('componente_faltante', 'N/A')}</small>
                        </li>
                    '''
                mensaje_html += '</ul>'
            
            mensaje_html += '<p class="mb-0"><strong>Recordá:</strong> Pausá las publicaciones en ML o cargá más stock.</p></div>'
            flash(mensaje_html, 'alerta_stock')
        else:
            mensaje = f'✅ Venta {numero_venta} registrada'
            if ubicacion_despacho == 'FULL':
                mensaje += ' - Se despachará desde FULL ML'
            else:
                mensaje += ' - Se despachará desde Depósito'
            flash(mensaje, 'success')
        
        return redirect(url_for('ventas_activas'))
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        import traceback
        error_completo = traceback.format_exc()
        print(f"ERROR al guardar venta:\n{error_completo}")
        flash(f'❌ Error al guardar venta: {str(e)}', 'error')
        return redirect(url_for('nueva_venta'))
