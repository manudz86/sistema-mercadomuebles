# ============================================================================
# REEMPLAZAR ESTAS 2 FUNCIONES EN app.py
# ============================================================================

import time  # Agregar este import si no lo tenés

def refresh_ml_token():
    """
    Renovar el access_token usando el refresh_token
    Retorna el nuevo access_token o None si falla
    """
    try:
        token_path = 'config/ml_token.json'
        if not os.path.exists(token_path):
            return None
        
        with open(token_path, 'r') as f:
            data = json.load(f)
        
        refresh_token = data.get('refresh_token')
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        if not refresh_token or not client_id or not client_secret:
            print("⚠️  No hay refresh_token o credenciales guardadas")
            return None
        
        print("🔄 Renovando access_token de ML...")
        
        response = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            }
        )
        
        if response.status_code == 200:
            new_data = response.json()
            
            # Actualizar datos guardados
            data['access_token'] = new_data.get('access_token')
            data['refresh_token'] = new_data.get('refresh_token', refresh_token)  # ML puede dar uno nuevo
            data['expires_at'] = time.time() + new_data.get('expires_in', 21600) - 300
            
            with open(token_path, 'w') as f:
                json.dump(data, f, indent=4)
            
            print(f"✅ Token renovado automáticamente!")
            return data['access_token']
        else:
            print(f"❌ Error renovando token: {response.status_code} - {response.json()}")
            return None
    
    except Exception as e:
        print(f"Error en refresh_ml_token: {e}")
        return None


def cargar_ml_token():
    """
    Cargar ACCESS_TOKEN desde config/ml_token.json
    Si está vencido, lo renueva automáticamente con el refresh_token
    """
    try:
        token_path = 'config/ml_token.json'
        if not os.path.exists(token_path):
            return None
        
        with open(token_path, 'r') as f:
            data = json.load(f)
        
        access_token = data.get('access_token')
        expires_at = data.get('expires_at', 0)
        
        # Verificar si el token está vencido
        if expires_at and time.time() > expires_at:
            print("⚠️  Token ML vencido, renovando automáticamente...")
            access_token = refresh_ml_token()
        
        return access_token
    
    except Exception as e:
        print(f"Error cargando token ML: {e}")
        return None


def guardar_ml_token(token_data):
    """
    Guardar datos del token en config/ml_token.json
    Mantiene el refresh_token si ya existía
    """
    try:
        os.makedirs('config', exist_ok=True)
        
        token_path = 'config/ml_token.json'
        
        # Si ya hay un archivo, preservar refresh_token y credenciales
        if os.path.exists(token_path):
            with open(token_path, 'r') as f:
                existing = json.load(f)
            
            # Preservar datos existentes que no vengan en el nuevo token_data
            if 'refresh_token' not in token_data and 'refresh_token' in existing:
                token_data['refresh_token'] = existing['refresh_token']
            if 'client_id' not in token_data and 'client_id' in existing:
                token_data['client_id'] = existing['client_id']
            if 'client_secret' not in token_data and 'client_secret' in existing:
                token_data['client_secret'] = existing['client_secret']
        
        # Si se guarda solo el access_token manual, no ponemos expires_at
        # para que no intente auto-refresh sin refresh_token
        if 'refresh_token' not in token_data:
            token_data.pop('expires_at', None)
        
        with open(token_path, 'w') as f:
            json.dump(token_data, f, indent=4)
        
        return True
    
    except Exception as e:
        print(f"Error guardando token ML: {e}")
        return False
