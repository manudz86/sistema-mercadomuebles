# ============================================================================
# SOLUCIÓN: Construir items_vendidos desde el formulario
# Reemplazar la sección de DETECTAR ALERTAS en guardar_venta
# ============================================================================

# ... (todo el código anterior de guardar_venta hasta justo antes de detectar alertas)

        # ========================================
        # DETECTAR ALERTAS ANTES DEL COMMIT
        # ========================================
        productos_sin_stock = []
        try:
            # Construir lista de items vendidos desde el formulario
            items_vendidos_lista = []
            
            # Recorrer todos los campos del formulario
            for key in request.form.keys():
                # Buscar campos que empiecen con 'agregar_'
                if key.startswith('agregar_'):
                    sku = key.replace('agregar_', '')
                    cantidad_str = request.form.get(key)
                    
                    if cantidad_str and int(cantidad_str) > 0:
                        items_vendidos_lista.append({
                            'sku': sku,
                            'cantidad': int(cantidad_str)
                        })
            
            print(f"\n🔍 Items a verificar: {items_vendidos_lista}")
            
            # Llamar a la función de detección
            productos_sin_stock = detectar_alertas_stock_bajo(cursor, items_vendidos_lista)
            
        except Exception as e_alertas:
            # Si falla detección de alertas, solo logear pero continuar
            print(f"⚠️ Error al detectar alertas (no crítico): {str(e_alertas)}")
            import traceback
            traceback.print_exc()
        
        # ========================================
        # COMMIT DE LA VENTA
        # ========================================
        conn.commit()
        cursor.close()
        conn.close()
        
        # ... (resto del código igual - mensajes y redirección)
