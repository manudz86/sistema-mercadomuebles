# ============================================================================
# MAPEO CORREGIDO DE TIPOS DE ENVÍO + FILTRO ARREGLADO
# ============================================================================

# ===== FUNCIÓN: obtener_shipping_completo (MAPEO CORREGIDO) =====
def obtener_shipping_completo(shipping_id, access_token):
    """
    Obtener detalles completos de shipping desde ML
    MAPEO CORREGIDO según tipos reales de ML
    """
    shipping_data = {
        'tiene_envio': True,
        'shipping_id': shipping_id,
        'metodo_envio': '',
        'metodo_envio_ml': '',
        'logistic_type_ml': '',
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
        
        # Método de envío
        shipping_option = shipment.get('shipping_option', {})
        shipping_mode = shipping_option.get('shipping_method_id', '')
        logistic_type = shipment.get('logistic_type', '')
        
        # 🔍 DEBUGGING
        print(f"\n🚚 SHIPPING ID: {shipping_id}")
        print(f"📦 shipping_method_id: {shipping_mode}")
        print(f"📦 logistic_type: {logistic_type}")
        
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


# ===== FUNCIÓN: ml_importar_ordenes (FILTRO ARREGLADO) =====
@app.route('/ventas/ml/importar')
def ml_importar_ordenes():
    """
    Traer órdenes de ML - FILTRO ARREGLADO
    """
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('❌ No hay ACCESS_TOKEN configurado. Configuralo primero.', 'error')
        return redirect(url_for('ml_configurar_token'))
    
    # Obtener órdenes de ML
    success, result = obtener_ordenes_ml(access_token, limit=50)
    
    if not success:
        flash(f'❌ Error al obtener órdenes de ML: {result}', 'error')
        return redirect(url_for('ventas_activas'))
    
    # 🔧 FILTRO ARREGLADO
    ordenes_importadas = set()
    try:
        # Buscar en TODAS las ventas (no solo las que empiezan con ML-)
        # porque el numero_venta puede estar en cualquier formato
        todas_ventas = query_db('''
            SELECT id, numero_venta, fecha_venta, canal, mla_code 
            FROM ventas 
            ORDER BY fecha_venta DESC 
            LIMIT 200
        ''')
        
        print(f"\n📊 DEBUG FILTRO DE DUPLICADOS:")
        print(f"Total ventas en BD (últimas 200): {len(todas_ventas)}")
        
        # Revisar cada venta y ver si el numero_venta contiene un ID de ML
        for venta in todas_ventas:
            numero = venta['numero_venta']
            
            # Extraer números del numero_venta
            # Puede ser: "ML-2000015174126338", "2000015174126338", etc.
            import re
            numeros = re.findall(r'\d+', numero)
            
            for num in numeros:
                # Los IDs de ML tienen 16 dígitos y empiezan con 2000
                if len(num) == 16 and num.startswith('2000'):
                    ordenes_importadas.add(num)
                    print(f"   ✅ Encontrado: {numero} → ID ML: {num}")
        
        print(f"\n✅ Total IDs de ML ya importados: {len(ordenes_importadas)}\n")
        
    except Exception as e:
        print(f"⚠️ Error al obtener órdenes importadas: {e}")
        import traceback
        traceback.print_exc()
    
    # Procesar órdenes
    ordenes_procesadas = []
    ordenes_filtradas = 0
    
    for orden in result:
        orden_id = str(orden['id'])
        
        print(f"🔍 Orden ML: {orden_id}")
        
        if orden_id in ordenes_importadas:
            print(f"   ⏭️ YA IMPORTADA - Saltando")
            ordenes_filtradas += 1
            continue
        else:
            print(f"   ✅ NUEVA - Agregando")
        
        # Solo mostrar órdenes pagadas
        if orden['status'] in ['paid']:
            orden_data = procesar_orden_ml(orden)
            
            # Verificar SKU
            for item in orden_data['items']:
                sku = item['sku']
                if sku:
                    existe, tipo, nombre = verificar_sku_en_bd(sku)
                    item['existe_en_bd'] = existe
                    item['tipo_producto'] = tipo
                    item['nombre_bd'] = nombre
                else:
                    item['existe_en_bd'] = False
                    item['tipo_producto'] = None
                    item['nombre_bd'] = None
            
            ordenes_procesadas.append(orden_data)
    
    print(f"\n📊 RESUMEN:")
    print(f"   Órdenes en ML: {len(result)}")
    print(f"   Órdenes filtradas: {ordenes_filtradas}")
    print(f"   Órdenes a mostrar: {len(ordenes_procesadas)}\n")
    
    return render_template('ml_importar_ordenes.html', ordenes=ordenes_procesadas)
