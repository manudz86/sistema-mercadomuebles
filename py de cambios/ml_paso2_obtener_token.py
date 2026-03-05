# ═══════════════════════════════════════════════════════
# 🔑 PASO 2: CANJEAR CÓDIGO POR ACCESS TOKEN
# ═══════════════════════════════════════════════════════
# 
# INSTRUCCIONES:
# 1. Reemplazá los 3 valores con tus datos
# 2. DEJÁ LAS COMILLAS ("")
# 3. Ejecutá el script
# 4. El script te muestra tu ACCESS_TOKEN
# 5. GUARDÁ ESE TOKEN (lo necesitás para el Paso 3)
# 
# ═══════════════════════════════════════════════════════

import requests
import json

# ✏️ REEMPLAZÁ ESTOS 3 VALORES:
CLIENT_ID = "2109946238600277"          # ← App ID
CLIENT_SECRET = "FLwEh7gcKUuc5DvqgaYtO8OyrMDB9R0Z"  # ← Secret Key
CODE = "TG-6993b080edb939000102ae49-29563319"                     # ← Código que copiaste de Google

# ═══════════════════════════════════════════════════════
# EJEMPLO DE CÓMO DEBE QUEDAR:
# 
# CLIENT_ID = "1234567890123456"
# CLIENT_SECRET = "abcdefGHIJKLmnopQRST"
# CODE = "TG-6993b080edb939000102ae49-29563319"
# 
# ═══════════════════════════════════════════════════════
# NO TOCAR ABAJO
# ═══════════════════════════════════════════════════════

REDIRECT_URI = "https://www.google.com"

print("\n" + "="*70)
print("🔄 CANJEANDO CÓDIGO POR ACCESS TOKEN...")
print("="*70)

# Datos para el request
data = {
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": CODE,
    "redirect_uri": REDIRECT_URI
}

try:
    # Request a ML
    response = requests.post(
        "https://api.mercadolibre.com/oauth/token",
        data=data
    )
    
    # Ver respuesta
    if response.status_code == 200:
        token_data = response.json()
        
        print("\n✅ ¡TOKEN OBTENIDO EXITOSAMENTE!\n")
        print("="*70)
        print("ACCESS_TOKEN:")
        print(token_data['access_token'])
        print("="*70)
        print(f"\nREFRESH_TOKEN:")
        print(token_data['refresh_token'])
        print("="*70)
        print(f"\nExpira en: {token_data['expires_in']} segundos (~6 horas)")
        print(f"User ID: {token_data['user_id']}")
        print("\n⚠️ IMPORTANTE:")
        print("   → GUARDÁ el ACCESS_TOKEN para usarlo en el PASO 3")
        print("   → GUARDÁ el REFRESH_TOKEN para renovarlo cuando expire")
        print("\n" + "="*70)
        
        # Guardar en archivo
        with open('ml_token.json', 'w') as f:
            json.dump(token_data, f, indent=4)
        print("\n💾 Token guardado en: ml_token.json")
        
    else:
        print("\n❌ ERROR:")
        print(f"Status: {response.status_code}")
        print(f"Respuesta: {response.text}")
        print("\n⚠️ Verificá que:")
        print("   1. El CLIENT_ID sea correcto")
        print("   2. El CLIENT_SECRET sea correcto")
        print("   3. El CODE sea el último que copiaste (solo sirve 1 vez)")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n⚠️ Verificá que tengas instalado 'requests':")
    print("   pip install requests")

print("\n")
