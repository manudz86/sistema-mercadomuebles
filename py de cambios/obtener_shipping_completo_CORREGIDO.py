def obtener_shipping_completo(shipping_id, access_token):
    """
    Obtener detalles completos de shipping desde ML
    MAPEO CORREGIDO según tipos reales de ML
    ✅ NUEVO: Captura COSTO DE ENVÍO del shipment
    """
    shipping_data = {
        'tiene_envio': True,
        'shipping_id': shipping_id,
        'metodo_envio': '',
        'metodo_envio_ml': '',
        'logistic_type_ml': '',
        'costo_envio': 0,  # ✅ NUEVO: Inicializar
        'direccion': '',
        'ciudad': '',
        'provincia': '',
        'codigo_postal': '',
        'zona': ''
    }
    
    if not shipping_id or not access_token:
        return shipping_data
    
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f'https://api.mercadolibre.com/shipments/{shipping_id}', headers=headers)
        
        if response.status_code != 200:
            print(f"⚠️ Error al obtener shipment {shipping_id}: {response.status_code}")
            return shipping_data
        
        shipment = response.json()
        
        # ✅ NUEVO: Capturar COSTO DE ENVÍO
        # Puede estar en varios lugares según el tipo de envío
        costo_envio = 0
        
        # Opción 1: base_cost
        if 'base_cost' in shipment:
            costo_envio = shipment.get('base_cost', 0)
            print(f"💰 Costo envío (base_cost): ${costo_envio}")
        
        # Opción 2: shipping_cost
        elif 'shipping_cost' in shipment:
            costo_envio = shipment.get('shipping_cost', 0)
            print(f"💰 Costo envío (shipping_cost): ${costo_envio}")
        
        # Opción 3: cost
        elif 'cost' in shipment:
            costo_envio = shipment.get('cost', 0)
            print(f"💰 Costo envío (cost): ${costo_envio}")
        
        # Opción 4: shipping_option -> cost
        elif 'shipping_option' in shipment:
            shipping_option = shipment.get('shipping_option', {})
            if 'cost' in shipping_option:
                costo_envio = shipping_option.get('cost', 0)
                print(f"💰 Costo envío (shipping_option.cost): ${costo_envio}")
        
        shipping_data['costo_envio'] = costo_envio
        
        # Método de envío
        shipping_option = shipment.get('shipping_option', {})
        shipping_mode = shipping_option.get('shipping_method_id', '')
        logistic_type = shipment.get('logistic_type', '')
        
        # 🔍 DEBUGGING
        print(f"\n🚚 SHIPPING ID: {shipping_id}")
        print(f"📦 shipping_method_id: {shipping_mode}")
        print(f"📦 logistic_type: {logistic_type}")
        print(f"💰 COSTO TOTAL: ${costo_envio}")
        
        # Guardar valores originales
        shipping_data['metodo_envio_ml'] = shipping_mode
        shipping_data['logistic_type_ml'] = logistic_type
        
        # 🔧 MAPEO CORREGIDO según logs reales
        if logistic_type == 'fulfillment':
            shipping_data['metodo_envio'] = 'Full'
            print(f"✅ MAPEADO A: Full")
        
        elif logistic_type == 'self_service':
            shipping_data['metodo_envio'] = 'Flex'
            print(f"✅ MAPEADO A: Flex")
        
        elif logistic_type == 'xd_drop_off':
            shipping_data['metodo_envio'] = 'Mercadoenvios'
            print(f"✅ MAPEADO A: Mercadoenvios")
        
        elif logistic_type == 'cross_docking':
            shipping_data['metodo_envio'] = 'Flex'
            print(f"✅ MAPEADO A: Flex")
        
        elif logistic_type == 'default':
            # Default depende de la zona (Flete propio o Zippin)
            # Por ahora dejamos como Flete Propio y luego se puede ajustar manualmente
            shipping_data['metodo_envio'] = 'Flete Propio'
            print(f"⚠️ MAPEADO A: Flete Propio (default - ajustar según zona)")
        
        elif 'mercadoenvios' in str(shipping_mode).lower():
            shipping_data['metodo_envio'] = 'Mercadoenvios'
            print(f"✅ MAPEADO A: Mercadoenvios")
        
        else:
            shipping_data['metodo_envio'] = 'Mercadoenvios'
            print(f"⚠️ MAPEADO A: Mercadoenvios (default)")
        
        # Dirección
        receiver_address = shipment.get('receiver_address', {})
        
        if receiver_address:
            address_line = receiver_address.get('address_line', '')
            street_name = receiver_address.get('street_name', '')
            street_number = receiver_address.get('street_number', '')
            floor = receiver_address.get('floor', '')
            apartment = receiver_address.get('apartment', '')
            
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
            
            if isinstance(city, dict):
                shipping_data['ciudad'] = str(city.get('name', ''))
            else:
                shipping_data['ciudad'] = str(city) if city else ''
            
            if isinstance(state, dict):
                shipping_data['provincia'] = str(state.get('name', ''))
            else:
                shipping_data['provincia'] = str(state) if state else ''
            
            shipping_data['codigo_postal'] = str(receiver_address.get('zip_code', ''))
            
            # Inferir zona
            if shipping_data['ciudad']:
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
    
    except Exception as e:
        print(f"⚠️ Error al procesar shipping {shipping_id}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return shipping_data
