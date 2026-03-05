# ============================================================================
# REEMPLAZAR la función procesar_orden_ml en app.py
# VERSIÓN CORREGIDA - Obtiene datos de shipping completos
# ============================================================================

def procesar_orden_ml(orden, access_token=None):
    """
    Procesar una orden de ML y extraer datos relevantes
    Si tiene shipping, hace request adicional para obtener dirección
    """
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
    
    # Datos de envío (inicializar)
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
    
    # Si tiene shipping_id, obtener detalles completos
    if shipping_id and access_token:
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(f'https://api.mercadolibre.com/shipments/{shipping_id}', headers=headers)
            
            if response.status_code == 200:
                shipment = response.json()
                
                # Determinar método de envío
                shipping_mode = shipment.get('shipping_option', {}).get('shipping_method_id', '')
                logistic_type = shipment.get('logistic_type', '')
                
                if logistic_type == 'fulfillment':
                    shipping_data['metodo_envio'] = 'Full'
                elif logistic_type == 'cross_docking':
                    shipping_data['metodo_envio'] = 'Flex'
                elif 'mercadoenvios' in shipping_mode.lower():
                    shipping_data['metodo_envio'] = 'Mercadoenvios'
                else:
                    shipping_data['metodo_envio'] = 'Mercadoenvios'  # Default
                
                # Dirección del receiver
                receiver_address = shipment.get('receiver_address', {})
                
                if receiver_address:
                    # Dirección completa
                    address_line = receiver_address.get('address_line', '')
                    street_name = receiver_address.get('street_name', '')
                    street_number = receiver_address.get('street_number', '')
                    floor = receiver_address.get('floor', '')
                    apartment = receiver_address.get('apartment', '')
                    
                    # Construir dirección
                    if address_line:
                        shipping_data['direccion'] = address_line
                    elif street_name and street_number:
                        direccion = f"{street_name} {street_number}"
                        if floor:
                            direccion += f" Piso {floor}"
                        if apartment:
                            direccion += f" Depto {apartment}"
                        shipping_data['direccion'] = direccion
                    
                    # Ciudad y provincia
                    city = receiver_address.get('city', {})
                    state = receiver_address.get('state', {})
                    
                    shipping_data['ciudad'] = city.get('name', '') if isinstance(city, dict) else str(city)
                    shipping_data['provincia'] = state.get('name', '') if isinstance(state, dict) else str(state)
                    shipping_data['codigo_postal'] = receiver_address.get('zip_code', '')
                    
                    # Inferir zona (Buenos Aires)
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
        
        except Exception as e:
            print(f"⚠️ Error al obtener detalles de shipping: {e}")
            # Continuar sin datos de shipping detallados
    
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
