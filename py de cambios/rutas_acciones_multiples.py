# ============================================================================
# RUTAS: ACCIONES MÚLTIPLES EN VENTAS HISTÓRICAS
# Agregar en app.py después de la ruta ventas_historicas()
# ============================================================================

@app.route('/ventas/historicas/volver-activas-multiple', methods=['POST'])
def historicas_volver_activas_multiple():
    """
    Volver múltiples ventas históricas a ventas activas
    Mantiene filtros después de la acción
    """
    try:
        venta_ids = request.form.getlist('venta_ids')
        
        if not venta_ids:
            flash('❌ No se seleccionaron ventas', 'error')
            return redirect(url_for('ventas_historicas'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ventas_devueltas = 0
        ventas_con_stock_devuelto = 0
        
        for venta_id in venta_ids:
            # Obtener venta
            cursor.execute('SELECT estado_entrega FROM ventas WHERE id = %s', (venta_id,))
            venta = cursor.fetchone()
            
            if not venta:
                continue
            
            estado_original = venta['estado_entrega']
            
            # Volver a activas
            cursor.execute('''
                UPDATE ventas 
                SET estado_entrega = 'pendiente',
                    fecha_modificacion = NOW()
                WHERE id = %s
            ''', (venta_id,))
            
            ventas_devueltas += 1
            
            # Si era entregada → devolver stock
            if estado_original == 'entregada':
                # Obtener items
                cursor.execute('''
                    SELECT sku, cantidad 
                    FROM items_venta 
                    WHERE venta_id = %s
                ''', (venta_id,))
                items = cursor.fetchall()
                
                for item in items:
                    sku = item['sku']
                    cantidad = item['cantidad']
                    
                    # Verificar si es producto base o combo
                    cursor.execute('SELECT sku FROM productos_base WHERE sku = %s', (sku,))
                    es_producto_base = cursor.fetchone()
                    
                    if es_producto_base:
                        # Devolver stock directo
                        cursor.execute('''
                            UPDATE productos_base 
                            SET stock_fisico = stock_fisico + %s 
                            WHERE sku = %s
                        ''', (cantidad, sku))
                    else:
                        # Es combo → devolver componentes
                        cursor.execute('''
                            SELECT sku_componente, cantidad as cantidad_componente
                            FROM componentes_producto
                            WHERE sku_producto = %s
                        ''', (sku,))
                        componentes = cursor.fetchall()
                        
                        for comp in componentes:
                            cantidad_a_devolver = comp['cantidad_componente'] * cantidad
                            cursor.execute('''
                                UPDATE productos_base 
                                SET stock_fisico = stock_fisico + %s 
                                WHERE sku = %s
                            ''', (cantidad_a_devolver, comp['sku_componente']))
                
                ventas_con_stock_devuelto += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Mensaje de éxito
        if ventas_con_stock_devuelto > 0:
            flash(f'✅ {ventas_devueltas} venta(s) devueltas a Ventas Activas. Stock restaurado en {ventas_con_stock_devuelto} venta(s).', 'success')
        else:
            flash(f'✅ {ventas_devueltas} venta(s) devueltas a Ventas Activas.', 'success')
        
        # ✅ MANTENER FILTROS
        filtros = {}
        if request.form.get('buscar'):
            filtros['buscar'] = request.form.get('buscar')
        if request.form.get('estado'):
            filtros['estado'] = request.form.get('estado')
        if request.form.get('periodo'):
            filtros['periodo'] = request.form.get('periodo')
        if request.form.get('metodo_envio'):
            filtros['metodo_envio'] = request.form.get('metodo_envio')
        if request.form.get('zona'):
            filtros['zona'] = request.form.get('zona')
        if request.form.get('canal'):
            filtros['canal'] = request.form.get('canal')
        
        return redirect(url_for('ventas_historicas', **filtros))
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ventas_historicas'))


@app.route('/ventas/historicas/facturar-multiple')
def facturar_multiple():
    """
    Generar UN SOLO archivo .txt con TODAS las ventas seleccionadas
    """
    from flask import make_response
    from datetime import datetime
    
    try:
        # Obtener IDs
        ids_str = request.args.get('ids', '')
        if not ids_str:
            flash('❌ No se seleccionaron ventas', 'error')
            return redirect(url_for('ventas_historicas'))
        
        venta_ids = [int(id) for id in ids_str.split(',') if id.strip()]
        
        if not venta_ids:
            flash('❌ No se seleccionaron ventas válidas', 'error')
            return redirect(url_for('ventas_historicas'))
        
        # ============================================
        # OBTENER TODAS LAS VENTAS
        # ============================================
        placeholders = ', '.join(['%s'] * len(venta_ids))
        query = f'''
            SELECT * FROM ventas 
            WHERE id IN ({placeholders})
            ORDER BY fecha_venta DESC
        '''
        ventas = query_db(query, tuple(venta_ids))
        
        if not ventas:
            flash('❌ No se encontraron ventas', 'error')
            return redirect(url_for('ventas_historicas'))
        
        # ============================================
        # GENERAR CONTENIDO DEL ARCHIVO TXT
        # ============================================
        
        lineas = []
        lineas.append("="*80)
        lineas.append("FACTURACIÓN MÚLTIPLE - DATOS PARA FACTURAR")
        lineas.append("="*80)
        lineas.append(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas.append(f"Total de ventas: {len(ventas)}")
        lineas.append("="*80)
        lineas.append("")
        
        total_general = 0
        
        # Procesar cada venta
        for idx, venta in enumerate(ventas, 1):
            lineas.append("")
            lineas.append("="*80)
            lineas.append(f"VENTA #{idx} - {venta['numero_venta']}")
            lineas.append("="*80)
            lineas.append("")
            
            # DATOS DE LA VENTA
            lineas.append(f"  Fecha: {venta['fecha_venta'].strftime('%d/%m/%Y')}")
            if venta.get('mla_code'):
                lineas.append(f"  ML Code: {venta['mla_code']}")
            lineas.append("")
            
            # DATOS DEL COMPRADOR
            lineas.append("-"*80)
            lineas.append("DATOS DEL COMPRADOR:")
            lineas.append("-"*80)
            
            if venta.get('factura_business_name'):
                # Tiene datos de facturación
                lineas.append(f"  Razón Social: {venta['factura_business_name']}")
                lineas.append(f"  {venta.get('factura_doc_type', 'Documento')}: {venta.get('factura_doc_number', 'N/A')}")
                lineas.append(f"  Condición IVA: {venta.get('factura_taxpayer_type', 'N/A')}")
                lineas.append("")
                lineas.append("  DOMICILIO FISCAL:")
                lineas.append(f"    Calle: {venta.get('factura_street', 'N/A')}")
                lineas.append(f"    Ciudad: {venta.get('factura_city', 'N/A')}")
                lineas.append(f"    Provincia: {venta.get('factura_state', 'N/A')}")
                lineas.append(f"    CP: {venta.get('factura_zip_code', 'N/A')}")
            else:
                # Consumidor Final
                lineas.append(f"  Nombre: {venta['nombre_cliente']}")
                if venta.get('telefono_cliente'):
                    lineas.append(f"  Teléfono: {venta['telefono_cliente']}")
                lineas.append(f"  Condición IVA: Consumidor Final")
                
                if venta.get('direccion_entrega'):
                    lineas.append("")
                    lineas.append("  DIRECCIÓN DE ENTREGA:")
                    lineas.append(f"    {venta['direccion_entrega']}")
                    if venta.get('zona_envio'):
                        lineas.append(f"    Zona: {venta['zona_envio']}")
            
            lineas.append("")
            
            # PRODUCTOS
            items = query_db('''
                SELECT iv.*, COALESCE(pb.nombre, pc.nombre, iv.sku) as nombre_producto
                FROM items_venta iv
                LEFT JOIN productos_base pb ON iv.sku = pb.sku
                LEFT JOIN productos_compuestos pc ON iv.sku = pc.sku
                WHERE iv.venta_id = %s
            ''', (venta['id'],))
            
            lineas.append("-"*80)
            lineas.append("PRODUCTOS:")
            lineas.append("-"*80)
            lineas.append("")
            lineas.append(f"{'Cant':<6} {'SKU':<15} {'Descripción':<35} {'P.Unit':<12} {'Subtotal':<12}")
            lineas.append("-"*80)
            
            total_items = 0
            for item in items:
                cant = item['cantidad']
                sku = item['sku']
                nombre = item['nombre_producto']
                precio = item['precio_unitario']
                subtotal = cant * precio
                
                lineas.append(f"{cant:<6} {sku:<15} {nombre:<35} ${precio:<11,.2f} ${subtotal:<11,.2f}")
                total_items += subtotal
            
            lineas.append("-"*80)
            lineas.append("")
            
            # TOTALES
            lineas.append("TOTALES:")
            lineas.append(f"  Subtotal Productos: ${total_items:,.2f}")
            
            if venta.get('costo_flete') and venta['costo_flete'] > 0:
                lineas.append(f"  Costo de Envío: ${venta['costo_flete']:,.2f}")
                lineas.append(f"  TOTAL: ${venta['importe_total']:,.2f}")
            else:
                lineas.append(f"  TOTAL: ${venta['importe_total']:,.2f}")
            
            lineas.append("")
            lineas.append("-"*80)
            
            # MÉTODO DE PAGO
            lineas.append("MÉTODO DE PAGO:")
            lineas.append(f"  {venta.get('metodo_pago', 'N/A')}")
            if venta.get('pago_mercadopago') and venta['pago_mercadopago'] > 0:
                lineas.append(f"    Mercadopago: ${venta['pago_mercadopago']:,.2f}")
            if venta.get('pago_efectivo') and venta['pago_efectivo'] > 0:
                lineas.append(f"    Efectivo: ${venta['pago_efectivo']:,.2f}")
            
            lineas.append("")
            
            total_general += venta['importe_total']
        
        # RESUMEN FINAL
        lineas.append("")
        lineas.append("="*80)
        lineas.append("RESUMEN GENERAL")
        lineas.append("="*80)
        lineas.append(f"Total de ventas facturadas: {len(ventas)}")
        lineas.append(f"TOTAL GENERAL: ${total_general:,.2f}")
        lineas.append("="*80)
        
        # ============================================
        # CREAR RESPUESTA CON ARCHIVO
        # ============================================
        
        contenido = "\n".join(lineas)
        
        response = make_response(contenido)
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        
        # Nombre del archivo
        fecha_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f"facturas_multiple_{fecha_str}.txt"
        response.headers['Content-Disposition'] = f'attachment; filename={nombre_archivo}'
        
        # ============================================
        # MARCAR TODAS COMO GENERADAS
        # ============================================
        
        placeholders = ', '.join(['%s'] * len(venta_ids))
        execute_db(f'''
            UPDATE ventas 
            SET factura_generada = TRUE,
                factura_fecha_generacion = NOW()
            WHERE id IN ({placeholders})
        ''', tuple(venta_ids))
        
        return response
        
    except Exception as e:
        flash(f'❌ Error al generar facturas: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ventas_historicas'))
