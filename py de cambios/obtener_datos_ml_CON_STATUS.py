# ============================================================================
# FUNCIÓN OBTENER DATOS ML - CON STATUS REAL
# ============================================================================

def obtener_datos_ml(mla_id, access_token):
    """
    Obtener título, stock, demora y ESTADO actual de una publicación de ML
    
    Returns:
        dict con 'titulo', 'stock', 'demora' y 'status'
    """
    try:
        url = f'https://api.mercadolibre.com/items/{mla_id}'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extraer demora si existe
            demora = None
            sale_terms = data.get('sale_terms', [])
            for term in sale_terms:
                if term.get('id') == 'MANUFACTURING_TIME':
                    demora = term.get('value_name', 'Sin especificar')
                    break
            
            # Extraer status real de ML
            status = data.get('status', 'unknown')  # active, paused, closed, etc.
            
            return {
                'titulo': data.get('title', 'Sin título'),
                'stock': data.get('available_quantity', 0),
                'demora': demora,
                'status': status  # ← NUEVO: Estado real de ML
            }
        else:
            return {'titulo': 'Error', 'stock': 0, 'demora': None, 'status': 'error'}
    
    except Exception as e:
        return {'titulo': 'Error', 'stock': 0, 'demora': None, 'status': 'error'}
