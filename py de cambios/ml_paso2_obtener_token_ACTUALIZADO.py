"""
ml_paso2_obtener_token.py - VERSIÓN ACTUALIZADA
Ejecutar DESPUÉS de ml_paso1_generar_url.py
Guarda access_token Y refresh_token para auto-refresh
"""

import requests
import json
import os

# ============================================================
# COMPLETAR CON TUS DATOS
# ============================================================
CLIENT_ID = "2109946238600277"
CLIENT_SECRET = "FLwEh7gcKUuc5DvqgaYtO8OyrMDB9R0Z"
REDIRECT_URI = "https://www.google.com"  # La misma que pusiste en ML
# ============================================================

# Pegá el código que viene en la URL de redirección
# Ejemplo: https://localhost?code=TG-XXXXXXXX#_=_
# El code es: TG-XXXXXXXX
CODE = "TG-6994796463d98e000136eb30-29563319"

# Obtener tokens
print("\n🔄 Obteniendo tokens...")

response = requests.post(
    "https://api.mercadolibre.com/oauth/token",
    data={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": CODE,
        "redirect_uri": REDIRECT_URI
    }
)

if response.status_code == 200:
    data = response.json()
    
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_in = data.get("expires_in", 21600)  # 6 horas en segundos
    
    print(f"\n✅ ACCESS_TOKEN obtenido!")
    print(f"✅ REFRESH_TOKEN obtenido!")
    print(f"⏱️  Expira en: {expires_in // 3600} horas")
    
    # Calcular timestamp de expiración
    import time
    expires_at = time.time() + expires_in - 300  # 5 minutos de margen
    
    # Guardar en config/ml_token.json
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    
    os.makedirs("config", exist_ok=True)
    with open("config/ml_token.json", "w") as f:
        json.dump(token_data, f, indent=4)
    
    print(f"\n✅ Tokens guardados en config/ml_token.json")
    print(f"\n📋 ACCESS_TOKEN: {access_token[:30]}...")
    print(f"📋 REFRESH_TOKEN: {refresh_token[:30]}...")
    
else:
    print(f"\n❌ Error: {response.status_code}")
    print(response.json())
