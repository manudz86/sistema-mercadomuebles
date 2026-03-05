# ============================================================================
# RUTAS NUEVAS: Bajar stock a 0 y Cargar demora
# Agregar en app.py junto a las rutas de cargar_stock_ml
# ============================================================================

def _recargar_publicaciones(sku, access_token):
    """Helper: recarga lista de publicaciones con datos frescos de ML"""
    publicaciones = query_db(
        "SELECT mla_id, titulo_ml, activo FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE",
        (sku,)
    )
    pubs_lista = []
    estado_map = {
        'active': 'Activa', 'paused': 'Pausada', 'closed': 'Cerrada',
        'under_review': 'En revisión', 'inactive': 'Inactiva'
    }
    for row in publicaciones:
        if access_token:
            datos_ml = obtener_datos_ml(row['mla_id'], access_token)
            status_ml = datos_ml.get('status', 'unknown')
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
                'stock_actual': '-', 'demora': None,
                'estado': 'Activa' if row['activo'] else 'Pausada',
                'status_raw': 'active' if row['activo'] else 'paused'
            })
    return pubs_lista


# ─── Bajar stock a 0 — INDIVIDUAL ────────────────────────────────────────────

@app.route('/bajar-stock-mla-cero', methods=['POST'])
def bajar_stock_mla_cero():
    """Poner stock en 0 en una publicación específica"""
    mla = request.form.get('mla')
    sku = request.form.get('sku')

    if not mla or not sku:
        flash('Faltan datos', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    access_token = cargar_ml_token()
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    success, message = actualizar_stock_ml(mla, 0, access_token)

    if success:
        flash(f'✅ Stock bajado a 0 en {mla}', 'success')
    else:
        flash(f'❌ {message}', 'danger')

    return render_template('cargar_stock_ml.html',
                           sku_buscado=sku,
                           publicaciones=_recargar_publicaciones(sku, access_token),
                           es_sku_con_z=sku.endswith('Z'))


# ─── Bajar stock a 0 — MASIVO ────────────────────────────────────────────────

@app.route('/bajar-stock-cero-masivo', methods=['POST'])
def bajar_stock_cero_masivo():
    """Poner stock en 0 en todas las publicaciones de un SKU"""
    sku = request.form.get('sku')
    if not sku:
        flash('Falta el SKU', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    access_token = cargar_ml_token()
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    mlas = query_db(
        "SELECT mla_id FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE", (sku,)
    )

    exitos, errores = 0, []
    for row in mlas:
        ok, msg = actualizar_stock_ml(row['mla_id'], 0, access_token)
        if ok:
            exitos += 1
        else:
            errores.append(msg)

    if exitos:
        flash(f'✅ Stock bajado a 0 en {exitos} publicación{"es" if exitos > 1 else ""}', 'success')
    for msg in errores[:3]:
        flash(f'❌ {msg}', 'danger')

    return render_template('cargar_stock_ml.html',
                           sku_buscado=sku,
                           publicaciones=_recargar_publicaciones(sku, access_token),
                           es_sku_con_z=sku.endswith('Z'))


# ─── Cargar demora — INDIVIDUAL ──────────────────────────────────────────────

@app.route('/cargar-demora-mla', methods=['POST'])
def cargar_demora_mla():
    """Poner X días de MANUFACTURING_TIME en una publicación"""
    mla  = request.form.get('mla')
    sku  = request.form.get('sku')
    dias = request.form.get('dias', '').strip()

    if not mla or not sku or not dias:
        flash('Faltan datos', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    access_token = cargar_ml_token()
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    import requests as req
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    payload = {"sale_terms": [{"id": "MANUFACTURING_TIME", "value_name": f"{dias} días"}]}

    r = req.put(f'https://api.mercadolibre.com/items/{mla}', headers=headers, json=payload)

    if r.status_code == 200:
        flash(f'✅ Demora de {dias} días cargada en {mla}', 'success')
    else:
        try:
            err = r.json()
        except:
            err = r.text
        flash(f'❌ Error ML {r.status_code} en {mla}: {err}', 'danger')

    return render_template('cargar_stock_ml.html',
                           sku_buscado=sku,
                           publicaciones=_recargar_publicaciones(sku, access_token),
                           es_sku_con_z=sku.endswith('Z'))


# ─── Cargar demora — MASIVO ───────────────────────────────────────────────────

@app.route('/cargar-demora-masivo', methods=['POST'])
def cargar_demora_masivo():
    """Poner X días de MANUFACTURING_TIME en todas las publicaciones de un SKU"""
    sku  = request.form.get('sku')
    dias = request.form.get('dias', '').strip()

    if not sku or not dias:
        flash('Faltan datos', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    access_token = cargar_ml_token()
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    mlas = query_db(
        "SELECT mla_id FROM sku_mla_mapeo WHERE sku = %s AND activo = TRUE", (sku,)
    )

    import requests as req
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    payload = {"sale_terms": [{"id": "MANUFACTURING_TIME", "value_name": f"{dias} días"}]}

    exitos, errores = 0, []
    for row in mlas:
        r = req.put(f'https://api.mercadolibre.com/items/{row["mla_id"]}', headers=headers, json=payload)
        if r.status_code == 200:
            exitos += 1
        else:
            errores.append(f'{row["mla_id"]}: {r.status_code}')

    if exitos:
        flash(f'✅ {dias} días de demora cargados en {exitos} publicación{"es" if exitos > 1 else ""}', 'success')
    for msg in errores[:3]:
        flash(f'❌ {msg}', 'danger')

    return render_template('cargar_stock_ml.html',
                           sku_buscado=sku,
                           publicaciones=_recargar_publicaciones(sku, access_token),
                           es_sku_con_z=sku.endswith('Z'))
