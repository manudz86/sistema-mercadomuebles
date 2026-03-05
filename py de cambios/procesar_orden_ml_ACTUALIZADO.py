# ============================================================================
# REEMPLAZAR EN app.py - Función procesar_orden_ml
# ACTUALIZADA: captura fecha_venta y costo_envio
# ============================================================================

def procesar_orden_ml(orden):
    """
    Procesar orden de ML SIN obtener detalles de shipping
    Usar al LISTAR órdenes (más rápido)
    CAPTURA FECHA REAL DE VENTA y COSTO DE ENVÍO
    """
    # Fecha REAL de la venta en ML
    fecha = datetime.fromisoformat(orden['date_created'].replace('Z', '+00:00'))
    
    # Items/Productos
    items = []
    for item in orden['order_items']:
        items.append({
            'sku': item['item'].get('seller_sku', ''),
            'titulo': item['item']['title'],
            'cantidad': item['quantity'],
            'precio': item['unit_price']
        })
    
    # Comprador
    buyer = orden.get('buyer', {})
    comprador_nombre = f"{buyer.get('first_name', '')} {buyer.get('last_name', '')}".strip()
    comprador_nickname = buyer.get('nickname', '')
    
    # Total
    total = orden['total_amount']
    
    # Estado
    estado = orden['status']
    
    # Shipping (solo ID, sin detalles) + COSTO DE ENVÍO
    shipping = orden.get('shipping', {})
    shipping_id = shipping.get('id', '')
    costo_envio = shipping.get('shipping_cost', 0)  # ✅ NUEVO: Capturar costo de envío
    
    shipping_data = {
        'tiene_envio': bool(shipping_id),
        'shipping_id': shipping_id,
        'costo_envio': costo_envio,  # ✅ NUEVO
        'metodo_envio': '',
        'direccion': '',
        'ciudad': '',
        'provincia': '',
        'codigo_postal': '',
        'zona': ''
    }
    
    return {
        'id': orden['id'],
        'fecha': fecha,  # ✅ Fecha real de ML
        'comprador_nombre': comprador_nombre,
        'comprador_nickname': comprador_nickname,
        'items': items,
        'total': total,
        'estado': estado,
        'shipping': shipping_data
    }
