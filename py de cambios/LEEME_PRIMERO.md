# 🚀 GUÍA: CONECTAR CON API DE MERCADO LIBRE

## 📋 ARCHIVOS INCLUIDOS:

1. `ml_paso1_generar_url.py` - Genera URL de autorización
2. `ml_paso2_obtener_token.py` - Obtiene ACCESS_TOKEN
3. `ml_paso3_traer_ordenes.py` - Trae tus ventas de ML

---

## ⚙️ REQUISITOS PREVIOS:

```bash
pip install requests
```

---

## 🔐 TUS CREDENCIALES:

Necesitás tener a mano:
- ✅ CLIENT_ID (App ID)
- ✅ CLIENT_SECRET (Secret Key)
- ✅ Redirect URI: `https://www.google.com`

---

## 📝 PASO A PASO:

### PASO 1: GENERAR URL DE AUTORIZACIÓN

1. Abrí `ml_paso1_generar_url.py`
2. Buscá esta línea:
   ```python
   CLIENT_ID = "TU_CLIENT_ID_AQUI"
   ```
3. Reemplazá `TU_CLIENT_ID_AQUI` por tu App ID
4. **DEJÁ LAS COMILLAS**
5. Guardá el archivo
6. Ejecutá:
   ```bash
   python ml_paso1_generar_url.py
   ```
7. Copiá la URL que aparece
8. Abrila en tu navegador
9. Autorizá la aplicación en Mercado Libre
10. ML te redirige a Google con una URL tipo:
    ```
    https://www.google.com/?code=TG-65f3a4b2e4b0c3000123456a-12345678
    ```
11. **Copiá solo el CODE** (la parte después de `code=`)
    Ejemplo: `TG-65f3a4b2e4b0c3000123456a-12345678`


code=TG-6993ae1c1cb51900012afa0c-29563319
     TG-6993b080edb939000102ae49-29563319


ACCESS_TOKEN:
APP_USR-2109946238600277-021620-7c8a1d74b33c020e6a7fb84c08f48643-29563319
---

### PASO 2: OBTENER ACCESS TOKEN

1. Abrí `ml_paso2_obtener_token.py`
2. Buscá estas 3 líneas:
   ```python
   CLIENT_ID = "TU_CLIENT_ID_AQUI"
   CLIENT_SECRET = "TU_CLIENT_SECRET_AQUI"
   CODE = "TG-XXXXXXXXX"
   ```
3. Reemplazá:
   - `TU_CLIENT_ID_AQUI` → Tu App ID
   - `TU_CLIENT_SECRET_AQUI` → Tu Secret Key
   - `TG-XXXXXXXXX` → El código que copiaste en Paso 1
4. **DEJÁ LAS COMILLAS**
5. Guardá el archivo
6. Ejecutá:
   ```bash
   python ml_paso2_obtener_token.py
   ```
7. El script te muestra tu **ACCESS_TOKEN**
8. **COPIÁ Y GUARDÁ ESE TOKEN** (lo necesitás para Paso 3)
9. El script también crea un archivo `ml_token.json` con todos los datos

⚠️ **IMPORTANTE:** El CODE solo sirve 1 vez. Si te da error, repetí el Paso 1.

---

### PASO 3: TRAER ÓRDENES DE MERCADO LIBRE

1. Abrí `ml_paso3_traer_ordenes.py`
2. Buscá esta línea:
   ```python
   ACCESS_TOKEN = "APP_USR-XXXXXXXXXXXXXXXXXXXXXXXXX"
   ```
3. Reemplazá `APP_USR-XXXXXXXXXXXXXXXXXXXXXXXXX` por tu token del Paso 2
4. **DEJÁ LAS COMILLAS**
5. Guardá el archivo
6. Ejecutá:
   ```bash
   python ml_paso3_traer_ordenes.py
   ```
7. El script te muestra tus últimas ventas de ML
8. También crea un archivo `ml_ordenes.json` con todos los datos

---

## 🎯 QUÉ VAS A VER:

El script muestra para cada venta:
- ✅ ID de orden (ej: 123456789)
- ✅ Fecha y hora de venta
- ✅ Estado de la orden
- ✅ Productos vendidos (nombre, cantidad, precio)
- ✅ Total de la venta
- ✅ Datos del comprador (nombre, nickname)
- ✅ Dirección de entrega completa

---

## 📦 ARCHIVOS QUE SE CREAN:

- `ml_token.json` - Tu token y datos de autenticación
- `ml_ordenes.json` - Tus ventas en formato JSON completo

---

## ⚠️ REGLAS IMPORTANTES:

### ✅ CORRECTO:
```python
CLIENT_ID = "1234567890123456"  # ← Con comillas
```

### ❌ INCORRECTO:
```python
CLIENT_ID = "TU_CLIENT_ID_AQUI1234567890123456"  # ❌ No reemplazaste completo
CLIENT_ID = 1234567890123456  # ❌ Faltan comillas
```

---

## 🔄 SI EL TOKEN EXPIRA:

El ACCESS_TOKEN dura ~6 horas. Cuando expire:
1. Repetí el Paso 1 para obtener un nuevo CODE
2. Repetí el Paso 2 para obtener un nuevo TOKEN
3. Usá el nuevo TOKEN en el Paso 3

---

## 🆘 ERRORES COMUNES:

### "Invalid client_id"
→ Verificá que el CLIENT_ID sea correcto

### "Invalid code"
→ El CODE ya fue usado o expiró. Repetí Paso 1.

### "Invalid grant"
→ El CODE solo sirve 1 vez. Repetí Paso 1.

### "Access token expired"
→ El token expiró. Repetí Pasos 1 y 2.

---

## 🎯 PRÓXIMOS PASOS:

Una vez que veas tus datos de ML:
1. Analizamos qué datos necesitás para tu sistema
2. Te hago un script que importe las ventas automáticamente
3. Lo integramos con tu Flask app

---

## 📞 AYUDA:

Si tenés algún error, mandame:
1. El mensaje de error completo
2. En qué paso estás

¡Éxito! 🚀
