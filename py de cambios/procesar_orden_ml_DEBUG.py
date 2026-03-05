# ============================================================================
# VERSIÓN CON DEBUGGING de procesar_orden_ml
# REEMPLAZAR en app.py temporalmente para debuggear
# ============================================================================

def procesar_orden_ml(orden):
    """
    Procesar una orden de ML y extraer datos relevantes
    VERSIÓN CON DEBUGGING
    """
    print("\n" + "="*70)
    print("🔍 DEBUG: Procesando orden de ML")
    print("="*70)
    
    # Fecha
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
    
    # Shipping
    shipping = orden.get('shipping', {})
    shipping_id = shipping.get('id', '')
    
    print(f"📦 Orden ID: {orden['id']}")
    print(f"🚚 Shipping ID: {shipping_id}")
    print(f"🚚 Shipping completo: {shipping}")
    
    # Datos de envío (si existen)
    shipping_data = {
        'tiene_envio': bool(shipping_id),
        'shipping_id': shipping_id,
        'metodo_envio': '',
        'direccion': '',
        'ciudad': '',
        'provincia': '',
        'codigo_postal': '',
        'zona': ''
    }
    
    # Si tiene shipping, extraer datos
    if shipping:
        print(f"✅ Tiene shipping")
        
        # Determinar método de envío
        shipping_mode = shipping.get('shipping_mode', '')
        logistic_type = shipping.get('logistic_type', '')
        
        print(f"   Shipping mode: {shipping_mode}")
        print(f"   Logistic type: {logistic_type}")
        
        if logistic_type == 'fulfillment':
            shipping_data['metodo_envio'] = 'Full'
        elif logistic_type == 'cross_docking':
            shipping_data['metodo_envio'] = 'Flex'
        elif shipping_mode == 'me2':
            shipping_data['metodo_envio'] = 'Mercadoenvios'
        else:
            shipping_data['metodo_envio'] = 'Mercadoenvios'
        
        print(f"   Método inferido: {shipping_data['metodo_envio']}")
        
        # Dirección
        receiver_address = shipping.get('receiver_address', {})
        print(f"   Receiver address: {receiver_address}")
        
        if receiver_address:
            # Dirección completa
            address_line = receiver_address.get('address_line', '')
            street_name = receiver_address.get('street_name', '')
            street_number = receiver_address.get('street_number', '')
            
            print(f"   Address line: {address_line}")
            print(f"   Street name: {street_name}")
            print(f"   Street number: {street_number}")
            
            if address_line:
                shipping_data['direccion'] = address_line
            elif street_name and street_number:
                shipping_data['direccion'] = f"{street_name} {street_number}"
            
            # Ciudad y provincia
            city = receiver_address.get('city', {})
            state = receiver_address.get('state', {})
            
            shipping_data['ciudad'] = city.get('name', '') if isinstance(city, dict) else city
            shipping_data['provincia'] = state.get('name', '') if isinstance(state, dict) else state
            shipping_data['codigo_postal'] = receiver_address.get('zip_code', '')
            
            print(f"   Dirección final: {shipping_data['direccion']}")
            print(f"   Ciudad: {shipping_data['ciudad']}")
            print(f"   Provincia: {shipping_data['provincia']}")
            
            # Inferir zona
            ciudad_lower = shipping_data['ciudad'].lower()
            provincia_lower = shipping_data['provincia'].lower()
            
            if 'capital federal' in ciudad_lower or 'ciudad' in ciudad_lower or 'caba' in ciudad_lower or 'autonoma' in provincia_lower:
                shipping_data['zona'] = 'Capital'
            elif any(x in ciudad_lower for x in ['plata', 'quilmes', 'avellaneda', 'berazategui', 'florencio varela', 'lanus']):
                shipping_data['zona'] = 'Sur'
            elif any(x in ciudad_lower for x in ['san isidro', 'tigre', 'pilar', 'escobar', 'san fernando']):
                shipping_data['zona'] = 'Norte-Noroeste'
            elif any(x in ciudad_lower for x in ['moron', 'merlo', 'ituzaingo', 'hurlingham', 'moreno']):
                shipping_data['zona'] = 'Oeste'
            else:
                shipping_data['zona'] = ''
            
            print(f"   Zona inferida: {shipping_data['zona']}")
    else:
        print(f"❌ NO tiene shipping")
    
    print(f"\n📊 Shipping data final: {shipping_data}")
    print("="*70 + "\n")
    
    return {
        'id': orden['id'],
        'fecha': fecha,
        'comprador_nombre': comprador_nombre,
        'comprador_nickname': comprador_nickname,
        'items': items,
        'total': total,
        'estado': estado,
        'shipping': shipping_data
    }
