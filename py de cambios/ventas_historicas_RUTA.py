# ============================================================================
# VENTAS HISTÓRICAS - RUTA COMPLETA
# Agregar después de las rutas de /ventas/proceso
# ============================================================================

@app.route('/ventas/historicas')
def ventas_historicas():
    """Lista de ventas históricas (entregadas y canceladas) con filtros"""
    try:
        # ========================================
        # OBTENER FILTROS
        # ========================================
        filtro_buscar = request.args.get('buscar', '').strip()
        filtro_estado = request.args.get('estado', '')  # '' = Todos, 'entregada', 'cancelada'
        filtro_periodo = request.args.get('periodo', 'todo')  # 'hoy', 'semana', 'mes', 'trimestre', 'todo'
        filtro_metodo_envio = request.args.get('metodo_envio', '')
        filtro_zona = request.args.get('zona', '')
        filtro_canal = request.args.get('canal', '')
        
        # ========================================
        # CONSTRUIR QUERY CON FILTROS
        # ========================================
        query = '''
            SELECT 
                id, numero_venta, fecha_venta, fecha_entrega, canal, mla_code,
                nombre_cliente, telefono_cliente,
                tipo_entrega, metodo_envio, ubicacion_despacho,
                zona_envio, direccion_entrega,
                metodo_pago, importe_total, importe_abonado,
                pago_mercadopago, pago_efectivo,
                estado_entrega, estado_pago, notas
            FROM ventas
            WHERE estado_entrega IN ('entregada', 'cancelada')
        '''
        params = []
        
        # Filtro: Estado (entregada, cancelada, o ambas)
        if filtro_estado:
            query += ' AND estado_entrega = %s'
            params.append(filtro_estado)
        
        # Filtro: Período (por fecha de entrega)
        if filtro_periodo == 'hoy':
            query += ' AND DATE(COALESCE(fecha_entrega, fecha_modificacion)) = CURDATE()'
        elif filtro_periodo == 'semana':
            query += ' AND COALESCE(fecha_entrega, fecha_modificacion) >= DATE_SUB(NOW(), INTERVAL 7 DAY)'
        elif filtro_periodo == 'mes':
            query += ' AND COALESCE(fecha_entrega, fecha_modificacion) >= DATE_SUB(NOW(), INTERVAL 30 DAY)'
        elif filtro_periodo == 'trimestre':
            query += ' AND COALESCE(fecha_entrega, fecha_modificacion) >= DATE_SUB(NOW(), INTERVAL 90 DAY)'
        
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
        
        # Ordenar: Más recientes arriba (por fecha de entrega, o fecha_modificacion si no hay fecha_entrega)
        query += ' ORDER BY COALESCE(fecha_entrega, fecha_modificacion) DESC, id DESC LIMIT 100'
        
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
        
        # ========================================
        # CONTAR ENTREGADAS Y CANCELADAS
        # ========================================
        stats_query = '''
            SELECT 
                estado_entrega,
                COUNT(*) as total
            FROM ventas
            WHERE estado_entrega IN ('entregada', 'cancelada')
        '''
        if filtro_periodo != 'todo':
            if filtro_periodo == 'hoy':
                stats_query += ' AND DATE(COALESCE(fecha_entrega, fecha_modificacion)) = CURDATE()'
            elif filtro_periodo == 'semana':
                stats_query += ' AND COALESCE(fecha_entrega, fecha_modificacion) >= DATE_SUB(NOW(), INTERVAL 7 DAY)'
            elif filtro_periodo == 'mes':
                stats_query += ' AND COALESCE(fecha_entrega, fecha_modificacion) >= DATE_SUB(NOW(), INTERVAL 30 DAY)'
            elif filtro_periodo == 'trimestre':
                stats_query += ' AND COALESCE(fecha_entrega, fecha_modificacion) >= DATE_SUB(NOW(), INTERVAL 90 DAY)'
        
        stats_query += ' GROUP BY estado_entrega'
        stats = query_db(stats_query)
        
        entregadas = 0
        canceladas = 0
        for stat in stats:
            if stat['estado_entrega'] == 'entregada':
                entregadas = stat['total']
            elif stat['estado_entrega'] == 'cancelada':
                canceladas = stat['total']
        
        return render_template('ventas_historicas.html', 
                             ventas=ventas,
                             entregadas=entregadas,
                             canceladas=canceladas,
                             filtro_buscar=filtro_buscar,
                             filtro_estado=filtro_estado,
                             filtro_periodo=filtro_periodo,
                             filtro_metodo_envio=filtro_metodo_envio,
                             filtro_zona=filtro_zona,
                             filtro_canal=filtro_canal)
        
    except Exception as e:
        flash(f'Error al cargar ventas históricas: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('index'))
