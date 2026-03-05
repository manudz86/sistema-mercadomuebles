def quitar_handling_time_ml(mla_id, access_token):
    """
    Quitar el tiempo de disponibilidad (handling_time) en ML
    CON LOGGING DETALLADO
    """
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # GET de la publicación
        response_get = requests.get(
            f'https://api.mercadolibre.com/items/{mla_id}',
            headers=headers
        )
        
        if response_get.status_code != 200:
            return False, f"Error obteniendo publicación: {response_get.status_code}"
        
        item_data = response_get.json()
        
        # VER QUÉ SALE_TERMS TIENE
        sale_terms_antes = item_data.get('sale_terms', [])
        print(f"\n=== DEBUG {mla_id} ===")
        print(f"sale_terms ANTES: {sale_terms_antes}")
        
        # Filtrar para quitar MANUFACTURING_TIME
        sale_terms_despues = [
            term for term in sale_terms_antes
            if term.get('id') != 'MANUFACTURING_TIME'
        ]
        
        print(f"sale_terms DESPUÉS: {sale_terms_despues}")
        
        # Enviar actualización
        data = {
            "sale_terms": sale_terms_despues
        }
        
        print(f"Enviando: {data}")
        
        response = requests.put(
            f'https://api.mercadolibre.com/items/{mla_id}',
            headers=headers,
            json=data
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500]}")  # Primeros 500 chars
        
        if response.status_code == 200:
            # VERIFICAR si realmente se quitó
            response_check = requests.get(
                f'https://api.mercadolibre.com/items/{mla_id}',
                headers=headers
            )
            
            if response_check.status_code == 200:
                item_actualizado = response_check.json()
                sale_terms_final = item_actualizado.get('sale_terms', [])
                print(f"sale_terms FINAL (después de actualizar): {sale_terms_final}")
                
                # Verificar si todavía tiene MANUFACTURING_TIME
                tiene_demora = any(
                    term.get('id') == 'MANUFACTURING_TIME' 
                    for term in sale_terms_final
                )
                
                if tiene_demora:
                    return False, f"ML aceptó el cambio pero la demora sigue ahí"
                else:
                    return True, f"Demora quitada correctamente de {mla_id}"
            
            return True, f"Actualizado (sin verificar)"
        else:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('message', 'Error desconocido')
            return False, f"Error ML: {error_msg}"
    
    except Exception as e:
        print(f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, f"Error: {str(e)}"
