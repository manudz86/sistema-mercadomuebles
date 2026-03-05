# ============================================================================
# TEST: GESTIÓN DE MANUFACTURING_TIME EN PUBLICACIONES ML
# Ruta segura y aislada - no toca nada del sistema existente
# ============================================================================

@app.route('/test/manufacturing-time', methods=['GET'])
def test_manufacturing_time():
    """
    Página de prueba para ver y modificar el MANUFACTURING_TIME
    de publicaciones ML con sufijo Z
    """
    return render_template('test_manufacturing_time.html')


@app.route('/test/manufacturing-time/ver', methods=['POST'])
def ver_manufacturing_time():
    """
    Consulta el estado actual de una publicación:
    - Muestra el MANUFACTURING_TIME actual
    - Muestra available_quantity
    - Solo lectura, no modifica nada
    """
    import requests as req

    item_id = request.form.get('item_id', '').strip().upper()
    if not item_id:
        return {'error': 'Falta item_id'}, 400

    access_token = cargar_ml_token()
    if not access_token:
        return {'error': 'No hay token ML activo'}, 400

    headers = {'Authorization': f'Bearer {access_token}'}

    try:
        r = req.get(f'https://api.mercadolibre.com/items/{item_id}', headers=headers)
        if r.status_code != 200:
            return {'error': f'ML devolvió {r.status_code}: {r.text}'}, 400

        data = r.json()

        # Extraer MANUFACTURING_TIME de sale_terms
        manufacturing_time = None
        for term in data.get('sale_terms', []):
            if term.get('id') == 'MANUFACTURING_TIME':
                manufacturing_time = term.get('value_name')
                break

        return {
            'ok': True,
            'item_id': item_id,
            'title': data.get('title'),
            'status': data.get('status'),
            'available_quantity': data.get('available_quantity'),
            'manufacturing_time': manufacturing_time,  # None = sin demora
            'permalink': data.get('permalink'),
        }

    except Exception as e:
        return {'error': str(e)}, 500


@app.route('/test/manufacturing-time/quitar', methods=['POST'])
def quitar_manufacturing_time():
    """
    Elimina el MANUFACTURING_TIME de una publicación enviando null.
    Según la API de ML:
    PUT /items/{item_id}
    { "sale_terms": [{ "id": "MANUFACTURING_TIME", "value_id": null, "value_name": null }] }
    """
    import requests as req

    item_id = request.form.get('item_id', '').strip().upper()
    if not item_id:
        return {'error': 'Falta item_id'}, 400

    access_token = cargar_ml_token()
    if not access_token:
        return {'error': 'No hay token ML activo'}, 400

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
            f'https://api.mercadolibre.com/items/{item_id}',
            headers=headers,
            json=payload
        )

        if r.status_code == 200:
            data = r.json()
            # Verificar que quedó en None
            manufacturing_time_nuevo = None
            for term in data.get('sale_terms', []):
                if term.get('id') == 'MANUFACTURING_TIME':
                    manufacturing_time_nuevo = term.get('value_name')
                    break

            return {
                'ok': True,
                'item_id': item_id,
                'title': data.get('title'),
                'manufacturing_time_anterior': request.form.get('mt_anterior'),
                'manufacturing_time_nuevo': manufacturing_time_nuevo,
                'mensaje': '✅ Demora eliminada correctamente' if not manufacturing_time_nuevo else '⚠️ No se pudo eliminar'
            }
        else:
            return {
                'ok': False,
                'error': f'ML devolvió {r.status_code}',
                'detalle': r.json()
            }, 400

    except Exception as e:
        return {'error': str(e)}, 500


@app.route('/test/manufacturing-time/poner', methods=['POST'])
def poner_manufacturing_time():
    """
    Pone o restaura el MANUFACTURING_TIME a un valor específico.
    Útil para revertir si algo sale mal.
    """
    import requests as req

    item_id = request.form.get('item_id', '').strip().upper()
    dias = request.form.get('dias', '').strip()

    if not item_id or not dias:
        return {'error': 'Faltan datos'}, 400

    access_token = cargar_ml_token()
    if not access_token:
        return {'error': 'No hay token ML activo'}, 400

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "sale_terms": [
            {
                "id": "MANUFACTURING_TIME",
                "value_name": f"{dias} días"
            }
        ]
    }

    try:
        r = req.put(
            f'https://api.mercadolibre.com/items/{item_id}',
            headers=headers,
            json=payload
        )

        if r.status_code == 200:
            data = r.json()
            manufacturing_time_nuevo = None
            for term in data.get('sale_terms', []):
                if term.get('id') == 'MANUFACTURING_TIME':
                    manufacturing_time_nuevo = term.get('value_name')
                    break

            return {
                'ok': True,
                'item_id': item_id,
                'manufacturing_time_nuevo': manufacturing_time_nuevo,
                'mensaje': f'✅ Demora restaurada a {dias} días'
            }
        else:
            return {
                'ok': False,
                'error': f'ML devolvió {r.status_code}',
                'detalle': r.json()
            }, 400

    except Exception as e:
        return {'error': str(e)}, 500
