# ============================================================================
# RUTAS Y FUNCIONES PARA CARGAR STOCK EN ML
# Agregar esto a app.py
# ============================================================================

import requests
from flask import render_template, request, redirect, url_for, flash


# ============================================================================
# RUTA PRINCIPAL - Mostrar página de carga de stock
# ============================================================================

@app.route('/cargar-stock-ml', methods=['GET'])
def cargar_stock_ml():
    """Mostrar página para cargar stock en ML"""
    return render_template('cargar_stock_ml.html',
                         sku_buscado=None,
                         publicaciones=[],
                         es_sku_con_z=False)


# ============================================================================
# BUSCAR PUBLICACIONES POR SKU
# ============================================================================

@app.route('/buscar-sku-ml', methods=['POST'])
def buscar_sku_ml():
    """Buscar publicaciones de ML por SKU"""
    
    sku_buscado = request.form.get('sku_buscar', '').strip().upper()
    
    if not sku_buscado:
        flash('Debes ingresar un SKU', 'warning')
        return redirect(url_for('cargar_stock_ml'))
    
    # Detectar si el SKU termina en Z
    es_sku_con_z = sku_buscado.endswith('Z')
    
    # Buscar publicaciones en la tabla sku_mla_mapeo
    cursor = mysql.connection.cursor()
    
    query = """
        SELECT mla, titulo, stock_actual, estado
        FROM sku_mla_mapeo
        WHERE sku = %s
        ORDER BY mla
    """
    
    cursor.execute(query, (sku_buscado,))
    resultados = cursor.fetchall()
    cursor.close()
    
    publicaciones = []
    for row in resultados:
        publicaciones.append({
            'mla': row[0],
            'titulo': row[1],
            'stock_actual': row[2],
            'estado': row[3]
        })
    
    return render_template('cargar_stock_ml.html',
                         sku_buscado=sku_buscado,
                         publicaciones=publicaciones,
                         es_sku_con_z=es_sku_con_z)


# ============================================================================
# QUITAR DEMORA - INDIVIDUAL
# ============================================================================

@app.route('/quitar-demora-mla', methods=['POST'])
def quitar_demora_mla():
    """Quitar demora de una publicación específica"""
    
    mla = request.form.get('mla')
    sku = request.form.get('sku')
    
    if not mla or not sku:
        flash('Faltan datos', 'danger')
        return redirect(url_for('cargar_stock_ml'))
    
    try:
        # Actualizar handling_time en ML (20 días por defecto)
        url = f'https://api.mercadolibre.com/items/{mla}'
        headers = {'Authorization': f'Bearer {ML_ACCESS_TOKEN}'}
        
        data = {
            'shipping': {
                'local_pick_up': False,
                'free_shipping': False,
                'mode': 'not_specified',
                'methods': [],
                'dimensions': None,
                'tags': ['self_service_in'],
                'logistic_type': 'default'
            },
            'sale_terms': [
                {'id': 'MANUFACTURING_TIME', 'value_name': '20 días'}
            ]
        }
        
        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code == 200:
            flash(f'✅ Demora quitada de {mla}', 'success')
        else:
            flash(f'❌ Error al quitar demora de {mla}: {response.text}', 'danger')
    
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    
    # Volver a buscar el SKU
    return redirect(url_for('buscar_sku_ml') + f'?sku_buscar={sku}')


# ============================================================================
# QUITAR DEMORA - MASIVO
# ============================================================================

@app.route('/quitar-demora-masivo', methods=['POST'])
def quitar_demora_masivo():
    """Quitar demora de todas las publicaciones de un SKU"""
    
    sku = request.form.get('sku')
    
    if not sku:
        flash('Falta el SKU', 'danger')
        return redirect(url_for('cargar_stock_ml'))
    
    # Obtener todas las publicaciones del SKU
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT mla FROM sku_mla_mapeo WHERE sku = %s", (sku,))
    mlas = [row[0] for row in cursor.fetchall()]
    cursor.close()
    
    exitos = 0
    errores = 0
    
    for mla in mlas:
        try:
            url = f'https://api.mercadolibre.com/items/{mla}'
            headers = {'Authorization': f'Bearer {ML_ACCESS_TOKEN}'}
            
            data = {
                'shipping': {
                    'local_pick_up': False,
                    'free_shipping': False,
                    'mode': 'not_specified',
                    'methods': [],
                    'dimensions': None,
                    'tags': ['self_service_in'],
                    'logistic_type': 'default'
                },
                'sale_terms': [
                    {'id': 'MANUFACTURING_TIME', 'value_name': '20 días'}
                ]
            }
            
            response = requests.put(url, headers=headers, json=data)
            
            if response.status_code == 200:
                exitos += 1
            else:
                errores += 1
        
        except Exception as e:
            errores += 1
    
    if exitos > 0:
        flash(f'✅ Demora quitada de {exitos} publicaciones', 'success')
    if errores > 0:
        flash(f'⚠️ {errores} publicaciones con errores', 'warning')
    
    # Volver a buscar el SKU
    return redirect(url_for('buscar_sku_ml') + f'?sku_buscar={sku}')


# ============================================================================
# CARGAR STOCK - INDIVIDUAL
# ============================================================================

@app.route('/cargar-stock-mla', methods=['POST'])
def cargar_stock_mla():
    """Cargar stock en una publicación específica"""
    
    mla = request.form.get('mla')
    sku = request.form.get('sku')
    stock_nuevo = request.form.get('stock_nuevo')
    
    if not mla or not sku or not stock_nuevo:
        flash('Faltan datos', 'danger')
        return redirect(url_for('cargar_stock_ml'))
    
    try:
        stock_nuevo = int(stock_nuevo)
        
        # Actualizar stock en ML
        url = f'https://api.mercadolibre.com/items/{mla}'
        headers = {'Authorization': f'Bearer {ML_ACCESS_TOKEN}'}
        
        data = {
            'available_quantity': stock_nuevo
        }
        
        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code == 200:
            # Actualizar en BD
            cursor = mysql.connection.cursor()
            cursor.execute("""
                UPDATE sku_mla_mapeo 
                SET stock_actual = %s
                WHERE mla = %s
            """, (stock_nuevo, mla))
            mysql.connection.commit()
            cursor.close()
            
            flash(f'✅ Stock cargado en {mla}: {stock_nuevo} unidades', 'success')
        else:
            flash(f'❌ Error al cargar stock en {mla}: {response.text}', 'danger')
    
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    
    # Volver a buscar el SKU
    return redirect(url_for('buscar_sku_ml') + f'?sku_buscar={sku}')


# ============================================================================
# CARGAR STOCK - MASIVO
# ============================================================================

@app.route('/cargar-stock-masivo', methods=['POST'])
def cargar_stock_masivo():
    """Cargar el mismo stock en todas las publicaciones de un SKU"""
    
    sku = request.form.get('sku')
    stock_nuevo = request.form.get('stock_nuevo')
    
    if not sku or not stock_nuevo:
        flash('Faltan datos', 'danger')
        return redirect(url_for('cargar_stock_ml'))
    
    try:
        stock_nuevo = int(stock_nuevo)
        
        # Obtener todas las publicaciones del SKU
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT mla FROM sku_mla_mapeo WHERE sku = %s", (sku,))
        mlas = [row[0] for row in cursor.fetchall()]
        
        exitos = 0
        errores = 0
        
        for mla in mlas:
            try:
                url = f'https://api.mercadolibre.com/items/{mla}'
                headers = {'Authorization': f'Bearer {ML_ACCESS_TOKEN}'}
                
                data = {
                    'available_quantity': stock_nuevo
                }
                
                response = requests.put(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    # Actualizar en BD
                    cursor.execute("""
                        UPDATE sku_mla_mapeo 
                        SET stock_actual = %s
                        WHERE mla = %s
                    """, (stock_nuevo, mla))
                    exitos += 1
                else:
                    errores += 1
            
            except Exception as e:
                errores += 1
        
        mysql.connection.commit()
        cursor.close()
        
        if exitos > 0:
            flash(f'✅ Stock cargado en {exitos} publicaciones: {stock_nuevo} unidades', 'success')
        if errores > 0:
            flash(f'⚠️ {errores} publicaciones con errores', 'warning')
    
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    
    # Volver a buscar el SKU
    return redirect(url_for('buscar_sku_ml') + f'?sku_buscar={sku}')
