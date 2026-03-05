# ============================================================================
# VENTAS ACTIVAS - RUTAS COMPLETAS
# Agregar después de la ruta /nueva-venta/guardar
# ============================================================================

@app.route('/ventas/activas')
def ventas_activas():
    """Lista de ventas activas con toda la información"""
    try:
        # Obtener ventas pendientes ordenadas por fecha (más antiguas arriba)
        ventas = query_db('''
            SELECT 
                id, numero_venta, fecha_venta, canal, mla_code,
                nombre_cliente, telefono_cliente,
                tipo_entrega, metodo_envio, ubicacion_despacho,
                zona_envio, direccion_entrega,
                metodo_pago, importe_total, importe_abonado,
                pago_mercadopago, pago_efectivo,
                estado_entrega, estado_pago, notas
            FROM ventas
            WHERE estado_entrega = 'pendiente'
            ORDER BY fecha_venta ASC, id ASC
        ''')
        
        # Para cada venta, obtener sus items
        for venta in ventas:
            items = query_db('''
                SELECT 
                    iv.sku, 
                    iv.cantidad, 
                    iv.precio_unitario,
                    COALESCE(pb.nombre, pc.nombre, iv.sku) as nombre_producto
                FROM items_venta iv
                LEFT JOIN productos_base pb ON iv.sku = pb.sku
                LEFT JOIN productos_compuestos pc ON iv.sku = pc.sku
                WHERE iv.venta_id = %s
                ORDER BY iv.id
            ''', (venta['id'],))
            venta['items'] = items
        
        return render_template('ventas_activas.html', ventas=ventas)
        
    except Exception as e:
        flash(f'Error al cargar ventas activas: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('index'))


@app.route('/ventas/activas/<int:venta_id>/proceso', methods=['POST'])
def pasar_a_proceso(venta_id):
    """Pasar venta a proceso de envío (descuenta stock)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener venta
        cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('Venta no encontrada', 'error')
            return redirect(url_for('ventas_activas'))
        
        if venta['estado_entrega'] != 'pendiente':
            flash('La venta ya no está pendiente', 'warning')
            return redirect(url_for('ventas_activas'))
        
        # Obtener items de la venta
        cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
        items = cursor.fetchall()
        
        # Descontar stock
        for item in items:
            descontar_stock_item(cursor, item, venta['ubicacion_despacho'])
        
        # Actualizar estado
        cursor.execute('''
            UPDATE ventas 
            SET estado_entrega = 'en_proceso',
                fecha_modificacion = NOW()
            WHERE id = %s
        ''', (venta_id,))
        
        conn.commit()
        flash(f'✅ Venta {venta["numero_venta"]} pasada a Proceso de Envío. Stock descontado.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error al pasar a proceso: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('ventas_activas'))


@app.route('/ventas/activas/<int:venta_id>/entregada', methods=['POST'])
def marcar_entregada(venta_id):
    """Marcar venta como entregada (descuenta stock si no se descontó)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener venta
        cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('Venta no encontrada', 'error')
            return redirect(url_for('ventas_activas'))
        
        # Si está pendiente, descontar stock
        if venta['estado_entrega'] == 'pendiente':
            cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
            items = cursor.fetchall()
            
            for item in items:
                descontar_stock_item(cursor, item, venta['ubicacion_despacho'])
        
        # Actualizar estado
        cursor.execute('''
            UPDATE ventas 
            SET estado_entrega = 'entregada',
                fecha_modificacion = NOW()
            WHERE id = %s
        ''', (venta_id,))
        
        conn.commit()
        flash(f'✅ Venta {venta["numero_venta"]} marcada como Entregada.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error al marcar como entregada: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('ventas_activas'))


@app.route('/ventas/activas/<int:venta_id>/cancelar', methods=['POST'])
def cancelar_venta(venta_id):
    """Cancelar venta (NO descuenta stock)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener venta
        cursor.execute('SELECT numero_venta FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('Venta no encontrada', 'error')
            return redirect(url_for('ventas_activas'))
        
        # Actualizar estado
        cursor.execute('''
            UPDATE ventas 
            SET estado_entrega = 'cancelada',
                fecha_modificacion = NOW()
            WHERE id = %s
        ''', (venta_id,))
        
        conn.commit()
        flash(f'✅ Venta {venta["numero_venta"]} cancelada. No se descontó stock.', 'info')
        
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error al cancelar venta: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('ventas_activas'))


# ============================================================================
# FUNCIÓN AUXILIAR: DESCONTAR STOCK
# ============================================================================

def descontar_stock_item(cursor, item, ubicacion_despacho):
    """
    Descuenta stock de un item considerando:
    - Ubicación de despacho (DEP o FULL)
    - Descomposición de combos
    - Bases grandes (160, 180, 200) descuentan 2 bases chicas
    """
    sku = item['sku']
    cantidad = item['cantidad']
    
    # Verificar si es un combo
    cursor.execute('SELECT id FROM productos_compuestos WHERE sku = %s', (sku,))
    combo = cursor.fetchone()
    
    if combo:
        # Es combo: descomponer y descontar componentes
        cursor.execute('''
            SELECT pb.sku, pb.tipo, c.cantidad_necesaria
            FROM componentes c
            JOIN productos_base pb ON c.producto_base_id = pb.id
            WHERE c.producto_compuesto_id = %s
        ''', (combo['id'],))
        componentes = cursor.fetchall()
        
        for comp in componentes:
            sku_comp = comp['sku']
            cant_comp = comp['cantidad_necesaria'] * cantidad
            tipo_comp = comp['tipo']
            
            # Descontar componente según ubicación
            descontar_stock_simple(cursor, sku_comp, cant_comp, tipo_comp, ubicacion_despacho)
    
    else:
        # Es producto simple
        cursor.execute('SELECT tipo FROM productos_base WHERE sku = %s', (sku,))
        prod = cursor.fetchone()
        tipo = prod['tipo'] if prod else 'colchon'
        
        descontar_stock_simple(cursor, sku, cantidad, tipo, ubicacion_despacho)


def descontar_stock_simple(cursor, sku, cantidad, tipo, ubicacion_despacho):
    """
    Descuenta stock de un producto simple según ubicación
    """
    # COMPAC: tiene _DEP y _FULL
    if '_DEP' in sku or '_FULL' in sku:
        if ubicacion_despacho == 'FULL':
            # Descontar de _FULL
            sku_real = sku.replace('_DEP', '_FULL')
        else:
            # Descontar de _DEP
            sku_real = sku.replace('_FULL', '_DEP')
        
        cursor.execute('''
            UPDATE productos_base 
            SET stock_actual = stock_actual - %s 
            WHERE sku = %s
        ''', (cantidad, sku_real))
    
    # ALMOHADAS: tienen stock_actual (DEP) y stock_full (FULL)
    elif tipo == 'almohada':
        if ubicacion_despacho == 'FULL':
            cursor.execute('''
                UPDATE productos_base 
                SET stock_full = stock_full - %s 
                WHERE sku = %s
            ''', (cantidad, sku))
        else:
            cursor.execute('''
                UPDATE productos_base 
                SET stock_actual = stock_actual - %s 
                WHERE sku = %s
            ''', (cantidad, sku))
    
    # BASES GRANDES: 160, 180, 200 descuentan 2 bases chicas
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
        
        cursor.execute('''
            UPDATE productos_base 
            SET stock_actual = stock_actual - %s 
            WHERE sku = %s
        ''', (cant_bases, sku_chica))
    
    # OTROS: descontar de stock_actual
    else:
        cursor.execute('''
            UPDATE productos_base 
            SET stock_actual = stock_actual - %s 
            WHERE sku = %s
        ''', (cantidad, sku))
