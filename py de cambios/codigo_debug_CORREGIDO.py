# ============================================================================
# CÓDIGO CORREGIDO - COPIAR AL FINAL DE app.py (ANTES del if __name__)
# ============================================================================

@app.route('/debug/ml/<orden_id>')
def debug_ml_orden(orden_id):
    """Ver qué datos trae ML de una orden"""
    access_token = cargar_ml_token()
    
    if not access_token:
        flash('No hay token de ML', 'error')
        return redirect(url_for('ventas_activas'))
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        # Obtener orden
        response = requests.get(f'https://api.mercadolibre.com/orders/{orden_id}', headers=headers)
        
        if response.status_code != 200:
            return f"<h2>Error {response.status_code}</h2>"
        
        orden = response.json()
        buyer = orden.get('buyer', {})
        
        # Intentar obtener billing
        billing_html = ""
        try:
            billing_response = requests.get(
                f'https://api.mercadolibre.com/orders/{orden_id}/billing_info',
                headers=headers
            )
            
            if billing_response.status_code == 200:
                billing = billing_response.json()
                import json
                billing_json = json.dumps(billing, indent=2, ensure_ascii=False)
                billing_html = f"<h3>TIENE DATOS DE FACTURACION:</h3><pre>{billing_json}</pre>"
            else:
                billing_html = "<h3>NO TIENE DATOS DE FACTURACION (Consumidor Final)</h3>"
        except:
            billing_html = "<h3>Error al obtener billing</h3>"
        
        # Construir HTML de respuesta
        html_response = """
        <html>
        <head>
            <title>Debug ML Orden</title>
            <style>
                body {{ font-family: monospace; padding: 20px; background: #1e1e1e; color: #d4d4d4; }}
                pre {{ background: #2d2d2d; padding: 15px; border-radius: 5px; overflow-x: auto; }}
                h2 {{ color: #4fc3f7; }}
                h3 {{ color: #ce9178; }}
            </style>
        </head>
        <body>
            <h2>DEBUG ORDEN ML: {orden_id}</h2>
            
            <h3>COMPRADOR:</h3>
            <p>Nombre: {nombre}</p>
            <p>Nickname: {nickname}</p>
            <p>Email: {email}</p>
            
            {billing_info}
            
            <br><br>
            <a href="/ventas/activas" style="color: #4fc3f7;">Volver a Ventas Activas</a>
        </body>
        </html>
        """.format(
            orden_id=orden_id,
            nombre=f"{buyer.get('first_name', '')} {buyer.get('last_name', '')}",
            nickname=buyer.get('nickname', ''),
            email=buyer.get('email', 'No disponible'),
            billing_info=billing_html
        )
        
        return html_response
        
    except Exception as e:
        import traceback
        error_completo = traceback.format_exc()
        return f"<pre>Error: {error_completo}</pre>"
