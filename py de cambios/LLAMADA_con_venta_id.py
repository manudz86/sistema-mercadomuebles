        # ========================================
        # DETECTAR ALERTAS ANTES DEL COMMIT
        # Pasar venta_id para excluirla del cálculo
        # ========================================
        productos_sin_stock = []
        try:
            # Construir lista de items vendidos desde los productos guardados
            items_vendidos_lista = []
            
            for key in productos.keys():
                if key.startswith('productos[') and key.endswith('[sku]'):
                    index = key.split('[')[1].split(']')[0]
                    sku = productos.get(f'productos[{index}][sku]', [None])[0]
                    cantidad = int(productos.get(f'productos[{index}][cantidad]', [0])[0])
                    
                    if sku and cantidad > 0:
                        items_vendidos_lista.append({
                            'sku': sku,
                            'cantidad': cantidad
                        })
            
            print(f"\n🔍 Items a verificar: {items_vendidos_lista}")
            
            # Llamar a la función de detección PASANDO venta_id
            if items_vendidos_lista:
                productos_sin_stock = detectar_alertas_stock_bajo(cursor, items_vendidos_lista, venta_id)
            
        except Exception as e_alertas:
            print(f"⚠️ Error al detectar alertas (no crítico): {str(e_alertas)}")
            import traceback
            traceback.print_exc()
