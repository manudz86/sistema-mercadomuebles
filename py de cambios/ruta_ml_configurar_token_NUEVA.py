# ============================================================================
# REEMPLAZAR la ruta ml_configurar_token en app.py con esta versión
# ============================================================================

@app.route('/ventas/ml/configurar_token', methods=['GET', 'POST'])
def ml_configurar_token():
    """
    Página para configurar/actualizar el token de ML
    Maneja 3 acciones:
    - GET: Mostrar página con URL de autorización
    - POST action=canjear_code: Canjear el code por access_token
    - POST action=token_manual: Guardar token manual (como antes)
    """
    
    # Credenciales de la app ML
    CLIENT_ID = "2109946238600277"
    CLIENT_SECRET = "FLwEh7gcKUuc5DvqgaYtO8OyrMDB9R0Z"
    REDIRECT_URI = "https://www.google.com"
    
    # Generar URL de autorización
    url_autorizacion = (
        f"https://auth.mercadolibre.com.ar/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=offline_access"
    )
    
    if request.method == 'POST':
        accion = request.form.get('action', 'token_manual')
        
        # ─── OPCIÓN 1: Canjear code por token automáticamente ───
        if accion == 'canjear_code':
            code = request.form.get('code', '').strip()
            
            if not code:
                flash('❌ Debes ingresar el CODE de la URL de redirección', 'error')
                return redirect(url_for('ml_configurar_token'))
            
            try:
                response = requests.post(
                    "https://api.mercadolibre.com/oauth/token",
                    data={
                        "grant_type": "authorization_code",
                        "client_id": CLIENT_ID,
                        "client_secret": CLIENT_SECRET,
                        "code": code,
                        "redirect_uri": REDIRECT_URI
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    token_data = {
                        "access_token": data.get("access_token"),
                        "refresh_token": data.get("refresh_token"),  # None si ML no lo da
                        "expires_at": time.time() + data.get("expires_in", 21600) - 300,
                        "client_id": CLIENT_ID,
                        "client_secret": CLIENT_SECRET
                    }
                    
                    if guardar_ml_token(token_data):
                        if token_data.get("refresh_token"):
                            flash('✅ Token configurado con auto-renovación activada', 'success')
                        else:
                            flash('✅ Token configurado correctamente (válido por 6 horas)', 'success')
                        return redirect(url_for('ventas_activas'))
                    else:
                        flash('❌ Error al guardar el token', 'error')
                
                else:
                    error_msg = response.json().get('message', 'Error desconocido')
                    flash(f'❌ Error al canjear el code: {error_msg}', 'error')
                    
            except Exception as e:
                flash(f'❌ Error: {str(e)}', 'error')
            
            return redirect(url_for('ml_configurar_token'))
        
        # ─── OPCIÓN 2: Pegar token manual (como antes) ───
        else:
            access_token = request.form.get('access_token', '').strip()
            
            if not access_token:
                flash('❌ Debes ingresar un ACCESS_TOKEN', 'error')
                return redirect(url_for('ml_configurar_token'))
            
            token_data = {
                'access_token': access_token,
                'fecha_configuracion': datetime.now().isoformat()
            }
            
            if guardar_ml_token(token_data):
                flash('✅ Token configurado correctamente', 'success')
                return redirect(url_for('ventas_activas'))
            else:
                flash('❌ Error al guardar token', 'error')
    
    # Verificar estado actual del token
    token_actual = cargar_ml_token()
    
    # Ver si tiene auto-refresh
    tiene_refresh = False
    horas_restantes = None
    try:
        token_path = 'config/ml_token.json'
        if os.path.exists(token_path):
            with open(token_path, 'r') as f:
                data = json.load(f)
                tiene_refresh = bool(data.get('refresh_token'))
                expires_at = data.get('expires_at')
                if expires_at:
                    segundos = expires_at - time.time()
                    if segundos > 0:
                        horas_restantes = round(segundos / 3600, 1)
    except:
        pass
    
    return render_template('ml_configurar_token.html',
                          token_actual=token_actual,
                          url_autorizacion=url_autorizacion,
                          tiene_refresh=tiene_refresh,
                          horas_restantes=horas_restantes)
