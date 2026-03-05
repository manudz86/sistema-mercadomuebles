# ============================================================================
# 1. ACTUALIZAR obtener_datos_ml PARA INCLUIR PRECIO Y LISTING TYPE
# Buscá la función obtener_datos_ml en tu app.py y agregá estos campos
# ============================================================================

# Mapeo de listing_type_id a nombre legible (Argentina)
LISTING_TYPE_NOMBRES = {
    'gold_pro':      'Clásica',
    'gold_special':  'Destacada',
    'gold_premium':  'Premium',
    'gold':          'Oro',
    'silver':        'Plata',
    'bronze':        'Bronce',
    'free':          'Gratuita',
}

def obtener_datos_ml(mla_id, access_token):
    """
    Consulta datos actuales de una publicación ML.
    Devuelve: titulo, stock, status, demora, precio, listing_type
    """
    import requests as req

    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        r = req.get(f'https://api.mercadolibre.com/items/{mla_id}', headers=headers)
        if r.status_code != 200:
            return {
                'titulo': mla_id, 'stock': 0, 'status': 'unknown',
                'demora': None, 'precio': None, 'listing_type': None
            }

        data = r.json()

        # Demora
        demora = None
        for term in data.get('sale_terms', []):
            if term.get('id') == 'MANUFACTURING_TIME':
                demora = term.get('value_name')
                break

        # Tipo de publicación
        listing_type_id = data.get('listing_type_id', '')
        listing_type = LISTING_TYPE_NOMBRES.get(listing_type_id, listing_type_id)

        return {
            'titulo':       data.get('title', mla_id),
            'stock':        data.get('available_quantity', 0),
            'status':       data.get('status', 'unknown'),
            'demora':       demora,
            'precio':       data.get('price'),          # ← NUEVO
            'listing_type': listing_type,               # ← NUEVO
        }

    except Exception as e:
        print(f"Error obteniendo datos ML de {mla_id}: {e}")
        return {
            'titulo': mla_id, 'stock': 0, 'status': 'unknown',
            'demora': None, 'precio': None, 'listing_type': None
        }


# ============================================================================
# 2. TAMBIÉN ACTUALIZAR _recargar_publicaciones para pasar precio y listing_type
# (ya llama a obtener_datos_ml, solo agregar los campos al dict)
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
                'mla':          row['mla_id'],
                'titulo':       datos_ml['titulo'],
                'stock_actual': datos_ml['stock'],
                'demora':       datos_ml.get('demora'),
                'precio':       datos_ml.get('precio'),        # ← NUEVO
                'listing_type': datos_ml.get('listing_type'),  # ← NUEVO
                'estado':       estado_map.get(status_ml, status_ml.capitalize()),
                'status_raw':   status_ml
            })
        else:
            pubs_lista.append({
                'mla':          row['mla_id'],
                'titulo':       row['titulo_ml'] or 'Sin título',
                'stock_actual': '-', 'demora': None,
                'precio':       None, 'listing_type': None,
                'estado':       'Activa' if row['activo'] else 'Pausada',
                'status_raw':   'active' if row['activo'] else 'paused'
            })
    return pubs_lista


# ============================================================================
# 3. TAMBIÉN ACTUALIZAR buscar_sku_ml para pasar precio y listing_type
# En el loop donde se arma el dict de cada publicación, agregar:
# ============================================================================

# DENTRO DEL LOOP en buscar_sku_ml, donde hacés publicaciones.append({...}):
# Agregar estos dos campos:
#
#     'precio':       datos_ml.get('precio'),
#     'listing_type': datos_ml.get('listing_type'),
#
# Y en el fallback sin token:
#     'precio':       None,
#     'listing_type': None,


# ============================================================================
# 4. RUTA: Cambiar precio — INDIVIDUAL
# ============================================================================

@app.route('/cambiar-precio-mla', methods=['POST'])
def cambiar_precio_mla():
    """Cambiar el precio de una publicación específica"""
    mla    = request.form.get('mla')
    sku    = request.form.get('sku')
    precio = request.form.get('precio', '').strip()

    if not mla or not sku or not precio:
        flash('Faltan datos', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    try:
        precio_float = float(precio)
        if precio_float <= 0:
            raise ValueError()
    except ValueError:
        flash('❌ Precio inválido', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    access_token = cargar_ml_token()
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    import requests as req
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    payload = {'price': precio_float}

    r = req.put(f'https://api.mercadolibre.com/items/{mla}', headers=headers, json=payload)

    if r.status_code == 200:
        flash(f'✅ Precio actualizado a ${precio_float:,.0f} en {mla}', 'success')
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


# ============================================================================
# 5. RUTA: Cambiar precio — MASIVO
# ============================================================================

@app.route('/cambiar-precio-masivo', methods=['POST'])
def cambiar_precio_masivo():
    """Cambiar el precio de todas las publicaciones de un SKU"""
    sku    = request.form.get('sku')
    precio = request.form.get('precio', '').strip()

    if not sku or not precio:
        flash('Faltan datos', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    try:
        precio_float = float(precio)
        if precio_float <= 0:
            raise ValueError()
    except ValueError:
        flash('❌ Precio inválido', 'danger')
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
    payload = {'price': precio_float}

    exitos, errores = 0, []
    for row in mlas:
        r = req.put(f'https://api.mercadolibre.com/items/{row["mla_id"]}', headers=headers, json=payload)
        if r.status_code == 200:
            exitos += 1
        else:
            errores.append(f'{row["mla_id"]}: {r.status_code}')

    if exitos:
        flash(f'✅ Precio actualizado a ${precio_float:,.0f} en {exitos} publicación{"es" if exitos > 1 else ""}', 'success')
    for msg in errores[:3]:
        flash(f'❌ {msg}', 'danger')

    return render_template('cargar_stock_ml.html',
                           sku_buscado=sku,
                           publicaciones=_recargar_publicaciones(sku, access_token),
                           es_sku_con_z=sku.endswith('Z'))
