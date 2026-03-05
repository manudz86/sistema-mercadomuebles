# ============================================================================
# FUNCIONES AUXILIARES: VERIFICACIÓN DE STOCK
# Agregar ANTES de las rutas de /ventas/activas en app.py
# ============================================================================

def verificar_stock_disponible(cursor, items, ubicacion_despacho):
    """
    Verifica si hay stock suficiente para todos los items de una venta.
    Retorna (True, []) si hay stock suficiente
    Retorna (False, [lista de errores]) si falta stock
    """
    errores = []
    
    for item in items:
        sku = item['sku']
        cantidad = item['cantidad']
        
        # Verificar si es un combo
        cursor.execute('SELECT id FROM productos_compuestos WHERE sku = %s', (sku,))
        combo = cursor.fetchone()
        
        if combo:
            # Es combo: verificar componentes
            cursor.execute('''
                SELECT pb.sku, pb.nombre, pb.tipo, c.cantidad_necesaria
                FROM componentes c
                JOIN productos_base pb ON c.producto_base_id = pb.id
                WHERE c.producto_compuesto_id = %s
            ''', (combo['id'],))
            componentes = cursor.fetchall()
            
            for comp in componentes:
                sku_comp = comp['sku']
                nombre_comp = comp['nombre']
                cant_necesaria = comp['cantidad_necesaria'] * cantidad
                tipo_comp = comp['tipo']
                
                # Verificar stock del componente
                stock_disponible = obtener_stock_disponible(cursor, sku_comp, tipo_comp, ubicacion_despacho)
                
                if stock_disponible < cant_necesaria:
                    errores.append(f"{nombre_comp} (SKU: {sku_comp}): Necesitas {cant_necesaria}, disponible {stock_disponible}")
        
        else:
            # Es producto simple
            cursor.execute('SELECT nombre, tipo FROM productos_base WHERE sku = %s', (sku,))
            prod = cursor.fetchone()
            
            if not prod:
                errores.append(f"Producto {sku} no encontrado en base de datos")
                continue
            
            nombre = prod['nombre']
            tipo = prod['tipo']
            
            # Verificar stock
            stock_disponible = obtener_stock_disponible(cursor, sku, tipo, ubicacion_despacho)
            
            if stock_disponible < cantidad:
                errores.append(f"{nombre} (SKU: {sku}): Necesitas {cantidad}, disponible {stock_disponible}")
    
    if errores:
        return False, errores
    else:
        return True, []


def obtener_stock_disponible(cursor, sku, tipo, ubicacion_despacho):
    """
    Obtiene el stock disponible de un producto según su tipo y ubicación.
    Considera:
    - COMPAC: _DEP o _FULL según ubicacion
    - Almohadas: stock_actual (DEP) o stock_full (FULL)
    - Bases grandes: divide stock de bases chicas entre 2
    - Otros: stock_actual
    """
    # COMPAC: tiene _DEP y _FULL
    if '_DEP' in sku or '_FULL' in sku:
        if ubicacion_despacho == 'FULL':
            sku_real = sku.replace('_DEP', '_FULL')
        else:
            sku_real = sku.replace('_FULL', '_DEP')
        
        cursor.execute('SELECT stock_actual FROM productos_base WHERE sku = %s', (sku_real,))
        prod = cursor.fetchone()
        return prod['stock_actual'] if prod else 0
    
    # ALMOHADAS: tienen stock_actual (DEP) y stock_full (FULL)
    elif tipo == 'almohada':
        cursor.execute('SELECT stock_actual, stock_full FROM productos_base WHERE sku = %s', (sku,))
        prod = cursor.fetchone()
        
        if not prod:
            return 0
        
        if ubicacion_despacho == 'FULL':
            return prod['stock_full']
        else:
            return prod['stock_actual']
    
    # BASES GRANDES: 160, 180, 200 necesitan 2 bases chicas
    elif tipo == 'base' and any(x in sku for x in ['160', '180', '200']):
        # Determinar SKU de bases chicas
        if '160' in sku:
            sku_chica = sku.replace('160', '80200')
        elif '180' in sku:
            sku_chica = sku.replace('180', '90200')
        elif '200' in sku:
            sku_chica = sku.replace('200', '100200')
        else:
            return 0
        
        cursor.execute('SELECT stock_actual FROM productos_base WHERE sku = %s', (sku_chica,))
        prod = cursor.fetchone()
        
        if not prod:
            return 0
        
        # Una base grande = 2 bases chicas
        # Stock disponible de bases grandes = stock_chicas / 2
        return prod['stock_actual'] // 2
    
    # OTROS: stock_actual normal
    else:
        cursor.execute('SELECT stock_actual FROM productos_base WHERE sku = %s', (sku,))
        prod = cursor.fetchone()
        return prod['stock_actual'] if prod else 0


# ============================================================================
# NOTA: Estas funciones deben agregarse ANTES de las rutas de ventas
# Luego se usan en pasar_a_proceso(), marcar_entregada(), etc.
# ============================================================================
