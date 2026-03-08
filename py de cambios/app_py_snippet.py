# ============================================================
# CAMBIO 1: en auditoria_ml_run, agregar 'stock_en_ml' a los tipos válidos
# Buscar la línea:
#   if tipo not in ['pausadas_sin_stock', 'pausadas_con_stock', 'demoras']:
# Reemplazar por:
#   if tipo not in ['pausadas_sin_stock', 'pausadas_con_stock', 'demoras', 'stock_en_ml']:
# ============================================================

# ============================================================
# CAMBIO 2: en auditoria_ml_run, dentro del if tipo == 'demoras' que filtra publicaciones,
# agregar el elif para stock_en_ml.
# Buscar el bloque:
#        if tipo == 'demoras':
#            publicaciones_db = query_db("""...""")
#        else:
#            publicaciones_db = query_db("""...""")
#
# Reemplazar por:
# ============================================================
        if tipo == 'demoras':
            publicaciones_db = query_db("""
                SELECT mla_id, sku, titulo_ml
                FROM sku_mla_mapeo
                WHERE activo = TRUE AND sku LIKE '%%Z'
                ORDER BY sku
            """)
        else:
            publicaciones_db = query_db("""
                SELECT mla_id, sku, titulo_ml
                FROM sku_mla_mapeo
                WHERE activo = TRUE
                ORDER BY sku
            """)

# ============================================================
# CAMBIO 3: en el PASO 1 del mismo método, el filtro actual
# salta SKUs con stock_disponible <= 0. Para stock_en_ml necesitamos
# EXACTAMENTE esos. Buscar:
#            if stock_disponible <= 0:
#                continue
#            pubs_a_consultar.append((pub, stock_disponible))
#
# Reemplazar por:
# ============================================================
            if tipo == 'stock_en_ml':
                # Queremos los que NO tienen stock disponible
                if stock_disponible > 0:
                    continue
            else:
                if stock_disponible <= 0:
                    continue
            pubs_a_consultar.append((pub, stock_disponible))

# ============================================================
# CAMBIO 4: en el PASO 3, agregar el elif para stock_en_ml.
# Buscar el bloque:
#            elif tipo == 'demoras':
#                if demora_ml and ...
#
# Agregar DESPUÉS del bloque demoras:
# ============================================================
            elif tipo == 'stock_en_ml':
                if stock_ml > 0:
                    resultados.append(item_base)

# ============================================================
# CAMBIO 5: agregar las dos nuevas rutas de acción
# Pegar DESPUÉS de auditoria_reducir_demora (línea ~7880 aprox)
# ============================================================

@app.route('/auditoria-ml/bajar-cero', methods=['POST'])
@login_required
def auditoria_bajar_cero():
    """Bajar stock a 0 en publicaciones seleccionadas. Para sección stock_en_ml."""
    if request.is_json:
        mlas_data = request.json.get('mla_stock', [])
    else:
        mlas_data = request.form.getlist('mla_stock')
    if not mlas_data:
        return jsonify({'error': 'No se seleccionaron publicaciones'}), 400
    access_token = cargar_ml_token()
    if not access_token:
        return jsonify({'error': 'No hay token de ML configurado'}), 401
    exitos = 0
    errores = []
    for item in mlas_data:
        try:
            mla, stock_str = item.split(':')
            stock = int(stock_str)  # siempre 0
            success, message = actualizar_stock_ml(mla, stock, access_token)
            if success:
                exitos += 1
            else:
                errores.append(f'{mla}: {message}')
            time.sleep(2)
        except Exception as e:
            errores.append(f'{item}: {str(e)}')
    return jsonify({'exitos': exitos, 'errores': errores, 'total': len(mlas_data)})


@app.route('/auditoria-ml/poner-demora', methods=['POST'])
@login_required
def auditoria_poner_demora():
    """Poner X días de demora en publicaciones Z seleccionadas. Para sección stock_en_ml."""
    if request.is_json:
        mlas_dias = request.json.get('mlas_dias', [])  # lista de "MLA123:15"
    else:
        mlas_dias = request.form.getlist('mlas_dias')
    if not mlas_dias:
        return jsonify({'error': 'No se seleccionaron publicaciones'}), 400
    access_token = cargar_ml_token()
    if not access_token:
        return jsonify({'error': 'No hay token de ML configurado'}), 401
    exitos = 0
    errores = []
    for item in mlas_dias:
        try:
            mla, dias_str = item.split(':')
            dias = int(dias_str)
            payload = {"sale_terms": [{"id": "MANUFACTURING_TIME", "value_name": f"{dias} días"}]}
            r = ml_request('put', f'https://api.mercadolibre.com/items/{mla}', access_token, json_data=payload)
            if r.status_code == 200:
                exitos += 1
            else:
                try:
                    err = r.json()
                except:
                    err = r.text
                errores.append(f'{mla}: {err}')
            time.sleep(2)
        except Exception as e:
            errores.append(f'{item}: {str(e)}')
    return jsonify({'exitos': exitos, 'errores': errores, 'total': len(mlas_dias)})
