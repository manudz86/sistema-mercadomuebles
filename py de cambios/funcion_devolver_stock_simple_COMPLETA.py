def devolver_stock_simple(cursor, sku, cantidad, tipo, ubicacion_despacho):
    """
    Devuelve stock de un producto simple según ubicación (SUMA en lugar de RESTAR)
    """
    # COMPAC: tiene _DEP y _FULL
    if '_DEP' in sku or '_FULL' in sku:
        if ubicacion_despacho == 'FULL':
            # Devolver a _FULL
            sku_real = sku.replace('_DEP', '_FULL')
        else:
            # Devolver a _DEP
            sku_real = sku.replace('_FULL', '_DEP')
        
        cursor.execute('''
            UPDATE productos_base 
            SET stock_actual = stock_actual + %s 
            WHERE sku = %s
        ''', (cantidad, sku_real))
    
    # ALMOHADAS: tienen stock_actual (DEP) y stock_full (FULL)
    elif tipo == 'almohada':
        if ubicacion_despacho == 'FULL':
            cursor.execute('''
                UPDATE productos_base 
                SET stock_full = stock_full + %s 
                WHERE sku = %s
            ''', (cantidad, sku))
        else:
            cursor.execute('''
                UPDATE productos_base 
                SET stock_actual = stock_actual + %s 
                WHERE sku = %s
            ''', (cantidad, sku))
    
    # BASES CHICAS (80200, 90200, 100200): devolver directamente
    elif tipo == 'base' and any(x in sku for x in ['80200', '90200', '100200']):
        cursor.execute('''
            UPDATE productos_base 
            SET stock_actual = stock_actual + %s 
            WHERE sku = %s
        ''', (cantidad, sku))
    
    # BASES GRANDES (160, 180, 200): devuelven 2 bases chicas
    elif tipo == 'base' and any(x in sku for x in ['160', '180', '200']):
        # Determinar SKU de bases chicas
        if '160' in sku:
            sku_chica = sku.replace('160', '80200')
            cant_bases = cantidad * 2
        elif '180' in sku:
            sku_chica = sku.replace('180', '90200')
            cant_bases = cantidad * 2
        elif '200' in sku:
            sku_chica = sku.replace('200', '100200')
            cant_bases = cantidad * 2
        else:
            return
        
        cursor.execute('''
            UPDATE productos_base 
            SET stock_actual = stock_actual + %s 
            WHERE sku = %s
        ''', (cant_bases, sku_chica))
    
    # OTROS: devolver a stock_actual
    else:
        cursor.execute('''
            UPDATE productos_base 
            SET stock_actual = stock_actual + %s 
            WHERE sku = %s
        ''', (cantidad, sku))
