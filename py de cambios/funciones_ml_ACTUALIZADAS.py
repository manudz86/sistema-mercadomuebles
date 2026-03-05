# ============================================================================
# FUNCIONES ACTUALIZADAS PARA app.py - IMPORTAR DATOS DE ENVÍO
# ============================================================================

# REEMPLAZAR la función obtener_shipping_details (NUEVA FUNCIÓN)
def obtener_shipping_details(access_token, shipping_id):
    """
    Obtener detalles del envío desde ML
    Retorna: (success, data_o_error)
    """
    if not shipping_id:
        return False, "No hay shipping_id"
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        response = requests.get(f'https://api.mercadolibre.com/shipments/{shipping_id}', headers=headers)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"Error {response.status_code}"
    except Exception as e:
        return False, str(e)


# REEMPLAZAR la función procesar_orden_ml completa
def procesar_orden_ml(orden):
    """
    Procesar una orden de ML y extraer datos relevantes
    Retorna diccionario con datos formateados
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
        # Determinar método de envío
        shipping_mode = shipping.get('shipping_mode', '')
        logistic_type = shipping.get('logistic_type', '')
        
        if logistic_type == 'fulfillment':
            shipping_data['metodo_envio'] = 'Full'
        elif logistic_type == 'cross_docking':
            shipping_data['metodo_envio'] = 'Flex'
        elif shipping_mode == 'me2':
            shipping_data['metodo_envio'] = 'Mercadoenvios'
        else:
            shipping_data['metodo_envio'] = 'Mercadoenvios'  # Por defecto
        
        # Dirección
        receiver_address = shipping.get('receiver_address', {})
        if receiver_address:
            # Dirección completa
            address_line = receiver_address.get('address_line', '')
            street_name = receiver_address.get('street_name', '')
            street_number = receiver_address.get('street_number', '')
            
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
            
            # Inferir zona (Buenos Aires específicamente)
            ciudad_lower = shipping_data['ciudad'].lower()
            provincia_lower = shipping_data['provincia'].lower()
            
            # Capital Federal
            if 'capital federal' in ciudad_lower or 'ciudad' in ciudad_lower or 'caba' in ciudad_lower or 'autonoma' in provincia_lower:
                shipping_data['zona'] = 'Capital'
            # Sur (La Plata, Quilmes, Avellaneda, etc.)
            elif any(x in ciudad_lower for x in ['plata', 'quilmes', 'avellaneda', 'berazategui', 'florencio varela', 'lanus']):
                shipping_data['zona'] = 'Sur'
            # Norte-Noroeste (San Isidro, Tigre, Pilar, etc.)
            elif any(x in ciudad_lower for x in ['san isidro', 'tigre', 'pilar', 'escobar', 'san fernando']):
                shipping_data['zona'] = 'Norte-Noroeste'
            # Oeste (Morón, Merlo, etc.)
            elif any(x in ciudad_lower for x in ['moron', 'merlo', 'ituzaingo', 'hurlingham', 'moreno']):
                shipping_data['zona'] = 'Oeste'
            else:
                shipping_data['zona'] = ''  # No se pudo inferir
    
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


# REEMPLAZAR la función ml_importar_ordenes completa
@app.route('/ventas/ml/importar')
def ml_importar_ordenes():
    """
    Traer órdenes de Mercado Libre y mostrarlas para seleccionar
    NO muestra órdenes ya importadas
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
    
    # Obtener IDs de órdenes ya importadas
    ordenes_importadas = set()
    try:
        # Buscar en BD ventas que empiecen con "ML-"
        ventas_ml = query_db("SELECT numero_venta FROM ventas WHERE numero_venta LIKE 'ML-%'")
        for venta in ventas_ml:
            # Extraer el ID de orden (después de "ML-")
            orden_id = venta['numero_venta'].replace('ML-', '')
            ordenes_importadas.add(orden_id)
    except Exception as e:
        print(f"Error al obtener órdenes importadas: {e}")
    
    # Procesar órdenes
    ordenes_procesadas = []
    for orden in result:
        # Verificar si ya fue importada
        orden_id = str(orden['id'])
        if orden_id in ordenes_importadas:
            continue  # Saltar esta orden
        
        # Solo mostrar órdenes pagadas y no canceladas
        if orden['status'] in ['paid']:
            orden_data = procesar_orden_ml(orden)
            
            # Verificar SKU en BD
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
    
    return render_template('ml_importar_ordenes.html', ordenes=ordenes_procesadas)
