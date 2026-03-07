@app.route('/cambiar-precios-individuales', methods=['POST'])
@login_required
def cambiar_precios_individuales():
    """Actualizar precios individuales de múltiples MLAs de una vez"""
    import requests as req
    import json

    sku = request.form.get('sku')
    precios_json = request.form.get('precios_json', '[]')

    try:
        precios = json.loads(precios_json)
    except:
        flash('❌ Error al procesar los precios', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    if not precios:
        flash('❌ No se recibieron precios', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    access_token = cargar_ml_token()
    if not access_token:
        flash('❌ No hay token de ML configurado', 'danger')
        return redirect(url_for('cargar_stock_ml'))

    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}

    exitos, errores = 0, []
    for item in precios:
        mla = item.get('mla')
        precio = item.get('precio')
        try:
            precio_float = float(precio)
            if precio_float <= 0:
                raise ValueError()
        except:
            errores.append(f'{mla}: precio inválido')
            continue

        r = req.put(
            f'https://api.mercadolibre.com/items/{mla}',
            headers=headers,
            json={'price': precio_float}
        )
        if r.status_code == 200:
            exitos += 1
        else:
            errores.append(f'{mla}: error {r.status_code}')

    if exitos:
        flash(f'✅ {exitos} precio{"s" if exitos > 1 else ""} actualizado{"s" if exitos > 1 else ""} correctamente', 'success')
    for msg in errores[:3]:
        flash(f'❌ {msg}', 'danger')

    return render_template('cargar_stock_ml.html',
                           sku_buscado=sku,
                           publicaciones=_recargar_publicaciones(sku, access_token),
                           es_sku_con_z=sku.endswith('Z') if sku else False)
