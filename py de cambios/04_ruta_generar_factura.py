# ============================================================================
# RUTA: GENERAR ARCHIVO .TXT DE FACTURACIÓN
# Agregar en app.py después de las rutas de ventas históricas
# ============================================================================

@app.route('/ventas/historicas/<int:venta_id>/generar-factura')
def generar_factura_txt(venta_id):
    """
    Generar archivo .txt con datos de facturación
    """
    from flask import make_response
    from datetime import datetime
    
    try:
        # Obtener venta con items
        venta = query_one('SELECT * FROM ventas WHERE id = %s', (venta_id,))
        
        if not venta:
            flash('❌ Venta no encontrada', 'error')
            return redirect(url_for('ventas_historicas'))
        
        # Obtener items
        items = query_db('''
            SELECT iv.*, COALESCE(pb.nombre, pc.nombre, iv.sku) as nombre_producto
            FROM items_venta iv
            LEFT JOIN productos_base pb ON iv.sku = pb.sku
            LEFT JOIN productos_compuestos pc ON iv.sku = pc.sku
            WHERE iv.venta_id = %s
        ''', (venta_id,))
        
        # ============================================
        # GENERAR CONTENIDO DEL ARCHIVO TXT
        # ============================================
        
        lineas = []
        lineas.append("="*80)
        lineas.append("DATOS PARA FACTURACIÓN")
        lineas.append("="*80)
        lineas.append("")
        
        # DATOS DE LA VENTA
        lineas.append("VENTA:")
        lineas.append(f"  Número: {venta['numero_venta']}")
        lineas.append(f"  Fecha: {venta['fecha_venta'].strftime('%d/%m/%Y')}")
        if venta.get('mla_code'):
            lineas.append(f"  ML Code: {venta['mla_code']}")
        lineas.append("")
        
        # DATOS DEL COMPRADOR / FACTURACIÓN
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
            # Consumidor Final - usar datos básicos
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
        lineas.append("-"*80)
        lineas.append("PRODUCTOS A FACTURAR:")
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
        lineas.append("="*80)
        lineas.append(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas.append("="*80)
        
        # ============================================
        # CREAR RESPUESTA CON ARCHIVO
        # ============================================
        
        contenido = "\n".join(lineas)
        
        # Crear respuesta
        response = make_response(contenido)
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        
        # Nombre del archivo
        nombre_archivo = f"factura_{venta['numero_venta'].replace('/', '-')}.txt"
        response.headers['Content-Disposition'] = f'attachment; filename={nombre_archivo}'
        
        # ============================================
        # MARCAR COMO GENERADA
        # ============================================
        
        execute_db('''
            UPDATE ventas 
            SET factura_generada = TRUE,
                factura_fecha_generacion = NOW()
            WHERE id = %s
        ''', (venta_id,))
        
        return response
        
    except Exception as e:
        flash(f'❌ Error al generar factura: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ventas_historicas'))
