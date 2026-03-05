# ============================================================================
# FUNCIÓN CON DEBUG - OBTENER DATOS DE ML
# ============================================================================

def obtener_datos_ml(mla_id, access_token):
    """
    Obtener título, stock y demora actual de una publicación de ML
    CON DEBUG para ver sale_terms completos
    """
    try:
        url = f'https://api.mercadolibre.com/items/{mla_id}'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # ========== DEBUG ==========
            print(f"\n{'='*80}")
            print(f"DEBUG MLA: {mla_id}")
            print(f"{'='*80}")
            
            # Mostrar sale_terms completo
            sale_terms = data.get('sale_terms', [])
            print(f"sale_terms COMPLETO:")
            import json
            print(json.dumps(sale_terms, indent=2, ensure_ascii=False))
            
            # Extraer demora si existe
            demora = None
            for term in sale_terms:
                if term.get('id') == 'MANUFACTURING_TIME':
                    demora = term.get('value_name', 'Sin especificar')
                    print(f"\n✅ MANUFACTURING_TIME encontrado:")
                    print(f"   value_name: {demora}")
                    print(f"   Objeto completo: {json.dumps(term, indent=2, ensure_ascii=False)}")
                    break
            
            if demora is None:
                print(f"\n❌ MANUFACTURING_TIME NO encontrado")
                print(f"   Esto significa: SIN DEMORA")
            
            print(f"{'='*80}\n")
            # ========== FIN DEBUG ==========
            
            return {
                'titulo': data.get('title', 'Sin título'),
                'stock': data.get('available_quantity', 0),
                'demora': demora
            }
        else:
            print(f"❌ Error HTTP {response.status_code} para {mla_id}")
            return {'titulo': 'Error', 'stock': 0, 'demora': None}
    
    except Exception as e:
        print(f"❌ Excepción en obtener_datos_ml: {str(e)}")
        return {'titulo': 'Error', 'stock': 0, 'demora': None}
