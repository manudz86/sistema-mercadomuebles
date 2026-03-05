# ============================================================================
# FUNCIÓN CORRECTA PARA QUITAR DEMORA
# Basada en el descubrimiento: SIN demora = NO existe MANUFACTURING_TIME
# ============================================================================

def quitar_handling_time_ml(mla_id, access_token):
    """
    Quitar el tiempo de disponibilidad (handling_time) en ML
    
    ESTRATEGIA: Eliminar el objeto MANUFACTURING_TIME de sale_terms
    
    Args:
        mla_id: ID de la publicación
        access_token: Token de ML
    
    Returns:
        (success: bool, message: str)
    """
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # 1. Obtener publicación actual
        response_get = requests.get(
            f'https://api.mercadolibre.com/items/{mla_id}',
            headers=headers
        )
        
        if response_get.status_code != 200:
            return False, f"Error obteniendo publicación: {response_get.status_code}"
        
        item_data = response_get.json()
        
        # 2. Obtener sale_terms actuales
        sale_terms_actuales = item_data.get('sale_terms', [])
        
        # DEBUG (opcional - comentar después)
        print(f"\n=== QUITAR DEMORA {mla_id} ===")
        print(f"sale_terms ANTES (cantidad): {len(sale_terms_actuales)}")
        
        # 3. FILTRAR: Eliminar MANUFACTURING_TIME
        sale_terms_sin_demora = [
            term for term in sale_terms_actuales
            if term.get('id') != 'MANUFACTURING_TIME'
        ]
        
        print(f"sale_terms DESPUÉS (cantidad): {len(sale_terms_sin_demora)}")
        
        # Verificar si se eliminó algo
        if len(sale_terms_actuales) == len(sale_terms_sin_demora):
            print("⚠️ MANUFACTURING_TIME no encontrado (ya sin demora)")
            return True, f"Publicación {mla_id} ya estaba sin demora"
        
        # 4. Actualizar con sale_terms sin MANUFACTURING_TIME
        data = {
            "sale_terms": sale_terms_sin_demora
        }
        
        print(f"Enviando {len(sale_terms_sin_demora)} términos (sin MANUFACTURING_TIME)")
        
        response = requests.put(
            f'https://api.mercadolibre.com/items/{mla_id}',
            headers=headers,
            json=data
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            # Verificar que efectivamente se quitó
            response_verify = requests.get(
                f'https://api.mercadolibre.com/items/{mla_id}',
                headers=headers
            )
            
            if response_verify.status_code == 200:
                verify_data = response_verify.json()
                verify_terms = verify_data.get('sale_terms', [])
                
                tiene_demora_aun = any(
                    term.get('id') == 'MANUFACTURING_TIME' 
                    for term in verify_terms
                )
                
                if tiene_demora_aun:
                    print("⚠️ ML restauró MANUFACTURING_TIME")
                    return False, f"ML restauró la demora automáticamente en {mla_id}"
                else:
                    print("✅ Demora eliminada correctamente")
                    return True, f"Demora quitada de {mla_id}"
            else:
                return True, f"Demora quitada de {mla_id} (no se pudo verificar)"
        else:
            error_data = response.json()
            error_msg = error_data.get('message', 'Error desconocido')
            print(f"❌ Error: {error_msg}")
            return False, f"Error ML: {error_msg}"
    
    except Exception as e:
        print(f"❌ Excepción: {str(e)}")
        return False, f"Error: {str(e)}"
