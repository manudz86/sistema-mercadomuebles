# ============================================================================
# PROCESO DE ENVÍO - RUTAS ACTUALIZADAS
# Incluye: Volver a Activas + Motivo de Cancelación
# Reemplazar las rutas de /ventas/proceso en app.py
# ============================================================================

@app.route('/ventas/proceso')
def ventas_proceso():
    """Lista de ventas en proceso de envío con filtros"""
    try:
        # ========================================
        # OBTENER FILTROS
        # ========================================
        filtro_buscar = request.args.get('buscar', '').strip()
        filtro_tipo_entrega = request.args.get('tipo_entrega', '')
        filtro_metodo_envio = request.args.get('metodo_envio', '')
        filtro_zona = request.args.get('zona', '')
        filtro_canal = request.args.get('canal', '')
        filtro_estado_pago = request.args.get('estado_pago', '')
        
        # ========================================
        # CONSTRUIR QUERY CON FILTROS
        # ========================================
        query = '''
            SELECT 
                id, numero_venta, fecha_venta, canal, mla_code,
                nombre_cliente, telefono_cliente,
                tipo_entrega, metodo_envio, ubicacion_despacho,
                zona_envio, direccion_entrega,
                metodo_pago, importe_total, importe_abonado,
                pago_mercadopago, pago_efectivo,
                estado_entrega, estado_pago, notas
            FROM ventas
            WHERE estado_entrega = 'en_proceso'
        '''
        params = []
        
        # Filtro: Búsqueda de texto
        if filtro_buscar:
            query += '''
                AND (
                    mla_code LIKE %s 
                    OR nombre_cliente LIKE %s
                    OR id IN (
                        SELECT venta_id FROM items_venta WHERE sku LIKE %s
                    )
                )
            '''
            busqueda = f'%{filtro_buscar}%'
            params.extend([busqueda, busqueda, busqueda])
        
        # Filtro: Tipo de entrega
        if filtro_tipo_entrega:
            query += ' AND tipo_entrega = %s'
            params.append(filtro_tipo_entrega)
        
        # Filtro: Método de envío
        if filtro_metodo_envio:
            query += ' AND metodo_envio = %s'
            params.append(filtro_metodo_envio)
        
        # Filtro: Zona
        if filtro_zona:
            query += ' AND zona_envio = %s'
            params.append(filtro_zona)
        
        # Filtro: Canal
        if filtro_canal:
            query += ' AND canal = %s'
            params.append(filtro_canal)
        
        # Filtro: Estado de pago
        if filtro_estado_pago:
            if filtro_estado_pago == 'pagado':
                query += ' AND importe_abonado >= importe_total'
            elif filtro_estado_pago == 'pendiente':
                query += ' AND importe_abonado = 0'
            elif filtro_estado_pago == 'parcial':
                query += ' AND importe_abonado > 0 AND importe_abonado < importe_total'
        
        # Ordenar: más antiguas arriba
        query += ' ORDER BY fecha_venta ASC, id ASC'
        
        # Ejecutar query
        ventas = query_db(query, tuple(params) if params else None)
        
        # ========================================
        # OBTENER ITEMS DE CADA VENTA
        # ========================================
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
        
        return render_template('proceso_envio.html', 
                             ventas=ventas,
                             filtro_buscar=filtro_buscar,
                             filtro_tipo_entrega=filtro_tipo_entrega,
                             filtro_metodo_envio=filtro_metodo_envio,
                             filtro_zona=filtro_zona,
                             filtro_canal=filtro_canal,
                             filtro_estado_pago=filtro_estado_pago)
        
    except Exception as e:
        flash(f'Error al cargar proceso de envío: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('index'))


@app.route('/ventas/proceso/<int:venta_id>/volver_activas', methods=['POST'])
def proceso_volver_activas(venta_id):
    """Volver venta de proceso a activas (devuelve stock)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener venta
        cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('Venta no encontrada', 'error')
            return redirect(url_for('ventas_proceso'))
        
        if venta['estado_entrega'] != 'en_proceso':
            flash('La venta no está en proceso', 'warning')
            return redirect(url_for('ventas_proceso'))
        
        # Obtener items de la venta
        cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
        items = cursor.fetchall()
        
        # DEVOLVER STOCK (porque ya se había descontado)
        for item in items:
            devolver_stock_item(cursor, item, venta['ubicacion_despacho'])
        
        # Actualizar estado a 'pendiente' (volver a activas)
        cursor.execute('''
            UPDATE ventas 
            SET estado_entrega = 'pendiente',
                fecha_modificacion = NOW()
            WHERE id = %s
        ''', (venta_id,))
        
        conn.commit()
        flash(f'✅ Venta {venta["numero_venta"]} devuelta a Ventas Activas. Stock restaurado.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error al volver a activas: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('ventas_proceso'))


@app.route('/ventas/proceso/<int:venta_id>/entregada', methods=['POST'])
def proceso_marcar_entregada(venta_id):
    """Marcar venta en proceso como entregada (stock ya descontado)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener venta
        cursor.execute('SELECT numero_venta, estado_entrega FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('Venta no encontrada', 'error')
            return redirect(url_for('ventas_proceso'))
        
        if venta['estado_entrega'] != 'en_proceso':
            flash('La venta no está en proceso', 'warning')
            return redirect(url_for('ventas_proceso'))
        
        # Actualizar estado (NO descuenta stock, ya se descontó)
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
        flash(f'❌ Error: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('ventas_proceso'))


@app.route('/ventas/proceso/<int:venta_id>/cancelar', methods=['POST'])
def proceso_cancelar_devolver(venta_id):
    """Cancelar venta en proceso y DEVOLVER stock descontado (con motivo opcional)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener venta
        cursor.execute('SELECT * FROM ventas WHERE id = %s', (venta_id,))
        venta = cursor.fetchone()
        
        if not venta:
            flash('Venta no encontrada', 'error')
            return redirect(url_for('ventas_proceso'))
        
        if venta['estado_entrega'] != 'en_proceso':
            flash('La venta no está en proceso', 'warning')
            return redirect(url_for('ventas_proceso'))
        
        # Obtener motivo de cancelación (opcional)
        motivo_cancelacion = request.form.get('motivo_cancelacion', '').strip()
        
        # Obtener items de la venta
        cursor.execute('SELECT * FROM items_venta WHERE venta_id = %s', (venta_id,))
        items = cursor.fetchall()
        
        # DEVOLVER STOCK (lo opuesto a descontar)
        for item in items:
            devolver_stock_item(cursor, item, venta['ubicacion_despacho'])
        
        # Actualizar estado y agregar motivo si existe
        if motivo_cancelacion:
            # Agregar motivo a las notas existentes
            notas_actuales = venta.get('notas', '') or ''
            notas_nuevas = f"{notas_actuales}\n[CANCELACIÓN] {motivo_cancelacion}".strip()
            
            cursor.execute('''
                UPDATE ventas 
                SET estado_entrega = 'cancelada',
                    notas = %s,
                    fecha_modificacion = NOW()
                WHERE id = %s
            ''', (notas_nuevas, venta_id))
        else:
            cursor.execute('''
                UPDATE ventas 
                SET estado_entrega = 'cancelada',
                    fecha_modificacion = NOW()
                WHERE id = %s
            ''', (venta_id,))
        
        conn.commit()
        
        mensaje = f'✅ Venta {venta["numero_venta"]} cancelada. Stock devuelto correctamente.'
        if motivo_cancelacion:
            mensaje += f' Motivo: {motivo_cancelacion}'
        
        flash(mensaje, 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error al cancelar y devolver stock: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('ventas_proceso'))


# ============================================================================
# FUNCIÓN AUXILIAR: DEVOLVER STOCK (OPUESTO A DESCONTAR)
# ============================================================================

def devolver_stock_item(cursor, item, ubicacion_despacho):
    """
    Devuelve stock de un item (lo opuesto a descontar_stock_item)
    Considera:
    - Ubicación de despacho (DEP o FULL)
    - Descomposición de combos
    - Bases grandes (160, 180, 200) devuelven 2 bases chicas
    """
    sku = item['sku']
    cantidad = item['cantidad']
    
    # Verificar si es un combo
    cursor.execute('SELECT id FROM productos_compuestos WHERE sku = %s', (sku,))
    combo = cursor.fetchone()
    
    if combo:
        # Es combo: descomponer y devolver componentes
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
            
            # Devolver componente según ubicación
            devolver_stock_simple(cursor, sku_comp, cant_comp, tipo_comp, ubicacion_despacho)
    
    else:
        # Es producto simple
        cursor.execute('SELECT tipo FROM productos_base WHERE sku = %s', (sku,))
        prod = cursor.fetchone()
        tipo = prod['tipo'] if prod else 'colchon'
        
        devolver_stock_simple(cursor, sku, cantidad, tipo, ubicacion_despacho)


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
    
    # BASES GRANDES: 160, 180, 200 devuelven 2 bases chicas
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
