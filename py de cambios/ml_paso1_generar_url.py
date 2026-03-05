# ═══════════════════════════════════════════════════════
# 📋 PASO 1: GENERAR URL DE AUTORIZACIÓN
# ═══════════════════════════════════════════════════════
# 
# INSTRUCCIONES:
# 1. Reemplazá "TU_CLIENT_ID_AQUI" por tu App ID
# 2. DEJÁ LAS COMILLAS ("")
# 3. Ejecutá el script
# 4. Copiá la URL que aparece
# 5. Abrila en tu navegador
# 6. Autorizá la app en Mercado Libre
# 7. Te redirige a Google - copiá el CODE de la URL
# 
# ═══════════════════════════════════════════════════════

# ✏️ REEMPLAZÁ ESTO:
CLIENT_ID = "TU_CLIENT_ID_AQUI"  # ← Pegá tu App ID entre las comillas

# ═══════════════════════════════════════════════════════
# NO TOCAR ABAJO
# ═══════════════════════════════════════════════════════

REDIRECT_URI = "https://www.google.com"

url_autorizacion = f"https://auth.mercadolibre.com.ar/authorization?response_type=code&client_id={2109946238600277}&redirect_uri={REDIRECT_URI}&scope=offline_access"

print("\n" + "="*70)
print("🔐 URL DE AUTORIZACIÓN DE MERCADO LIBRE")
print("="*70)
print("\n1️⃣ Copiá esta URL completa:\n")
print(url_autorizacion)
print("\n2️⃣ Abrila en tu navegador")
print("3️⃣ Autorizá la aplicación en Mercado Libre")
print("4️⃣ ML te redirige a Google con una URL tipo:")
print("   https://www.google.com/?code=TG-xxxxxxxxxxxxx")
print("\n5️⃣ Copiá solo la parte del CODE (TG-xxxxx)")
print("6️⃣ Guardá ese código para el PASO 2")
print("\n" + "="*70)
print("\n✅ Listo para ejecutar\n")
