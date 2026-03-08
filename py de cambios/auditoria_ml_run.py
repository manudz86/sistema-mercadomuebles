@app.route('/auditoria-ml/run/<tipo>', methods=['GET'])
@login_required
def auditoria_ml_run(tipo):
    """
    Ejecuta un tipo específico de auditoría y devuelve JSON con los resultados.
    Usa batch de ML (20 MLAs por request) en lugar de llamadas individuales.
    """
    if tipo not in ['pausadas_sin_stock', 'pausadas_con_stock', 'demoras', 'stock_en_ml']:
        return jsonify({'error': 'Tipo de auditoría inválido'}), 400

    access_token = cargar_ml_token()
    if not access_token:
        return jsonify({'error': 'No hay token de ML configurado'}), 401

    try:
        stock_por_sku = calcular_stock_por_sku()

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

        # PASO 1: filtrar por stock local primero (sin tocar la API de ML)
        pubs_a_consultar = []
        for pub in publicaciones_db:
            sku = pub['sku']
            stock_info = stock_por_sku.get(sku)
            if not stock_info and sku.endswith('Z'):
                stock_info = stock_por_sku.get(sku[:-1])
            if not stock_info:
                continue
            stock_disponible = stock_info['stock_disponible']

            if tipo == 'stock_en_ml':
                # Para esta auditoría queremos los que NO tienen stock disponible
                if stock_disponible > 0:
                    continue
            else:
                if stock_disponible <= 0:
                    continue

            pubs_a_consultar.append((pub, stock_disponible))

        # PASO 2: batch a ML — 20 MLAs por request en lugar de 1 x 1
        mla_ids = [pub['mla_id'] for pub, _ in pubs_a_consultar]
        datos_batch = obtener_datos_ml_batch(mla_ids, access_token)

        # PASO 3: clasificar resultados
        import re
        resultados = []
        for pub, stock_disponible in pubs_a_consultar:
            mla_id    = pub['mla_id']
            sku       = pub['sku']
            datos_ml  = datos_batch.get(mla_id, {})
            status_ml = datos_ml.get('status', 'unknown')
            stock_ml  = datos_ml.get('stock', 0)
            demora_ml = datos_ml.get('demora')

            item_base = {
                'mla':              mla_id,
                'sku':              sku,
                'titulo':           datos_ml.get('titulo', pub.get('titulo_ml', '')),
                'stock_disponible': stock_disponible,
                'stock_ml':         stock_ml,
                'status':           status_ml
            }

            if tipo == 'pausadas_sin_stock':
                if status_ml == 'paused' and stock_ml == 0:
                    resultados.append(item_base)

            elif tipo == 'pausadas_con_stock':
                if status_ml == 'paused' and stock_ml > 0:
                    resultados.append(item_base)

            elif tipo == 'demoras':
                if demora_ml and demora_ml != 'Sin especificar':
                    try:
                        numeros = re.findall(r'\d+', str(demora_ml))
                        if numeros and int(numeros[0]) > 0:
                            item_base['demora'] = demora_ml
                            resultados.append(item_base)
                    except Exception as e:
                        print(f"Error parseando demora '{demora_ml}': {e}")

            elif tipo == 'stock_en_ml':
                # Publicaciones con stock en ML pero sin stock local disponible
                if stock_ml > 0:
                    resultados.append(item_base)

        print(f"✅ Auditoría '{tipo}': {len(resultados)} resultados (consultados {len(mla_ids)} MLAs en {-(-len(mla_ids)//20)} requests)")
        return jsonify({'tipo': tipo, 'resultados': resultados, 'total': len(resultados)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
