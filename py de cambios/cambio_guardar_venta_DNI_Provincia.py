# ============================================================================
# CAMBIOS EN LA FUNCIÓN guardar_venta()
# Buscar en app.py la función @app.route('/nueva-venta/guardar', methods=['POST'])
# ============================================================================

# ========================================
# CAMBIO 1: Agregar captura de DNI y Provincia
# BUSCAR la sección "1. DATOS GENERALES" (después de telefono_cliente)
# ========================================

# AGREGAR estas 2 líneas DESPUÉS de:
# telefono_cliente = request.form.get('telefono_cliente', '')

# ✅ NUEVO: Capturar DNI y Provincia
dni_cliente = request.form.get('dni_cliente', '').strip()
provincia_cliente = request.form.get('provincia_cliente', 'Capital Federal')


# ========================================
# CAMBIO 2: Actualizar el INSERT
# BUSCAR la sección "6. ✅ INSERTAR VENTA"
# ========================================

# ANTES:
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


# DESPUÉS (con dni_cliente y provincia_cliente):
cursor.execute('''
    INSERT INTO ventas (
        numero_venta, fecha_venta, canal, mla_code,
        nombre_cliente, telefono_cliente, dni_cliente, provincia_cliente,
        tipo_entrega, metodo_envio, ubicacion_despacho,
        zona_envio, direccion_entrega, responsable_entrega,
        costo_flete, metodo_pago, importe_total, importe_abonado,
        pago_mercadopago, pago_efectivo,
        estado_entrega, estado_pago, notas,
        factura_business_name, factura_doc_type, factura_doc_number,
        factura_taxpayer_type, factura_city, factura_street,
        factura_state, factura_zip_code
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s
    )
''', (
    numero_venta, fecha_venta, canal, mla_code,
    nombre_cliente, telefono_cliente, dni_cliente, provincia_cliente,  # ✅ NUEVOS
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


# ============================================================================
# RESUMEN DE CAMBIOS:
# ============================================================================
# 
# 1. Capturar dni_cliente y provincia_cliente del form
# 2. Agregar dni_cliente, provincia_cliente al INSERT
# 3. Agregar 2 valores más en la tupla de VALUES
# 4. Cambiar el placeholder count de %s (de 29 a 31)
#
# ============================================================================
