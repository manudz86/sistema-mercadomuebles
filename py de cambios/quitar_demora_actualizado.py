# ============================================================================
# FUNCIÓN HELPER - Quitar MANUFACTURING_TIME completamente (envía null a ML)
# Reemplaza a quitar_handling_time_ml y actualizar_handling_time_ml
# ============================================================================

def quitar_manufacturing_time_ml(mla_id, access_token):
    """
    Elimina completamente el MANUFACTURING_TIME de una publicación ML.
    Envía value_id: null y value_name: null — ambos requeridos por la API.
    Retorna (True, mensaje) o (False, error)
    """
    import requests as req

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "sale_terms": [
            {
                "id": "MANUFACTURING_TIME",
                "value_id": None,
                "value_name": None
            }
        ]
    }

    try:
        r = req.put(
            f'https://api.mercadolibre.com/items/{mla_id}',
            headers=headers,
            json=payload
        )

        if r.status_code == 200:
            data = r.json()
            # Verificar que quedó en None
            mt_nuevo = None
            for term in data.get('sale_terms', []):
                if term.get('id') == 'MANUFACTURING_TIME':
                    mt_nuevo = term.get('value_name')
                    break

            if mt_nuevo is None:
                return True, f'Demora eliminada en {mla_id}'
            else:
                return True, f'Demora actualizada a {mt_nuevo} en {mla_id}'
        else:
            try:
                err = r.json()
            except:
                err = r.text
            return False, f'Error ML {r.status_code} en {mla_id}: {err}'

    except Exception as e:
        return False, f'Excepción en {mla_id}: {str(e)}'


# ============================================================================
# RUTA: Quitar demora de UNA publicación
# ============================================================================

@app.route('/quitar-demora-mla', methods=['POST'])
def quitar_demora_mla():
    """Eliminar MANUFACTURING_TIME de una publicación específica"""

    mla = request.form.get('mla')
    sku = request.form.get('sku')

    if not mla or not sku:
        flash('Faltan datos', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    access_token = cargar_ml_token()
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    success, message = quitar_manufacturing_time_ml(mla, access_token)

    if success:
        flash(f'✅ {message}', 'success')
    else:
        flash(f'❌ {message}', 'danger')

    # Recargar publicaciones con datos actualizados de ML
    publicaciones = query_db(
        "SELECT mla_id, titulo_ml, activo FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE",
        (sku,)
    )

    pubs_lista = []
    access_token_refresh = cargar_ml_token()

    for row in publicaciones:
        if access_token_refresh:
            datos_ml = obtener_datos_ml(row['mla_id'], access_token_refresh)
            status_ml = datos_ml.get('status', 'unknown')
            estado_map = {
                'active': 'Activa', 'paused': 'Pausada', 'closed': 'Cerrada',
                'under_review': 'En revisión', 'inactive': 'Inactiva'
            }
            pubs_lista.append({
                'mla': row['mla_id'],
                'titulo': datos_ml['titulo'],
                'stock_actual': datos_ml['stock'],
                'demora': datos_ml.get('demora'),
                'estado': estado_map.get(status_ml, status_ml.capitalize()),
                'status_raw': status_ml
            })
        else:
            pubs_lista.append({
                'mla': row['mla_id'],
                'titulo': row['titulo_ml'] or 'Sin título',
                'stock_actual': '-',
                'demora': None,
                'estado': 'Activa' if row['activo'] else 'Pausada',
                'status_raw': 'active' if row['activo'] else 'paused'
            })

    return render_template('cargar_stock_ml.html',
                           sku_buscado=sku,
                           publicaciones=pubs_lista,
                           es_sku_con_z=sku.endswith('Z'))


# ============================================================================
# RUTA: Quitar demora de TODAS las publicaciones de un SKU
# ============================================================================

@app.route('/quitar-demora-masivo', methods=['POST'])
def quitar_demora_masivo():
    """Eliminar MANUFACTURING_TIME de todas las publicaciones de un SKU"""

    sku = request.form.get('sku')
    if not sku:
        flash('Falta el SKU', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    access_token = cargar_ml_token()
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    mlas = query_db(
        "SELECT mla_id FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE",
        (sku,)
    )

    exitos = 0
    errores = 0
    mensajes_error = []

    for row in mlas:
        success, message = quitar_manufacturing_time_ml(row['mla_id'], access_token)
        if success:
            exitos += 1
        else:
            errores += 1
            mensajes_error.append(message)

    if exitos > 0:
        flash(f'✅ Demora eliminada en {exitos} publicación{"es" if exitos > 1 else ""}', 'success')
    if errores > 0:
        flash(f'⚠️ {errores} publicación{"es" if errores > 1 else ""} con errores', 'warning')
        for msg in mensajes_error[:3]:
            flash(msg, 'warning')

    # Recargar publicaciones con datos actualizados de ML
    publicaciones = query_db(
        "SELECT mla_id, titulo_ml, activo FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE",
        (sku,)
    )

    pubs_lista = []
    access_token_refresh = cargar_ml_token()

    for row in publicaciones:
        if access_token_refresh:
            datos_ml = obtener_datos_ml(row['mla_id'], access_token_refresh)
            status_ml = datos_ml.get('status', 'unknown')
            estado_map = {
                'active': 'Activa', 'paused': 'Pausada', 'closed': 'Cerrada',
                'under_review': 'En revisión', 'inactive': 'Inactiva'
            }
            pubs_lista.append({
                'mla': row['mla_id'],
                'titulo': datos_ml['titulo'],
                'stock_actual': datos_ml['stock'],
                'demora': datos_ml.get('demora'),
                'estado': estado_map.get(status_ml, status_ml.capitalize()),
                'status_raw': status_ml
            })
        else:
            pubs_lista.append({
                'mla': row['mla_id'],
                'titulo': row['titulo_ml'] or 'Sin título',
                'stock_actual': '-',
                'demora': None,
                'estado': 'Activa' if row['activo'] else 'Pausada',
                'status_raw': 'active' if row['activo'] else 'paused'
            })

    return render_template('cargar_stock_ml.html',
                           sku_buscado=sku,
                           publicaciones=pubs_lista,
                           es_sku_con_z=sku.endswith('Z'))
