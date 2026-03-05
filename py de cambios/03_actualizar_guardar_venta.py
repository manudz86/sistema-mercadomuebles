# ============================================================================
# ACTUALIZAR FUNCIÓN: guardar_venta
# REEMPLAZAR LA SECCIÓN DE INSERT en app.py
# ============================================================================

# Buscar en tu función guardar_venta() la parte donde hace el INSERT
# Y agregar los campos de facturación

# ============================================
# AGREGAR DESPUÉS DE: ml_shipping = session.get('ml_shipping', {})
# ============================================

# ✅ NUEVO: Obtener y extraer datos de billing
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

# ============================================
# REEMPLAZAR EL INSERT COMPLETO
# ============================================

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
    # ✅ NUEVOS: Datos de facturación
    billing_info['business_name'],
    billing_info['doc_type'],
    billing_info['doc_number'],
    billing_info['taxpayer_type'],
    billing_info['city'],
    billing_info['street'],
    billing_info['state'],
    billing_info['zip_code']
))

# ============================================
# AGREGAR AL FINAL (donde se limpia la sesión)
# ============================================

# Limpiar sesión de ML (agregar billing_data)
session.pop('ml_orden_id', None)
session.pop('ml_items', None)
session.pop('ml_comprador_nombre', None)
session.pop('ml_comprador_nickname', None)
session.pop('ml_shipping', None)
session.pop('ml_fecha_venta', None)
session.pop('ml_billing_data', None)  # ✅ NUEVO
