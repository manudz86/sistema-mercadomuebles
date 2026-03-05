# 📝 EJEMPLOS VISUALES - CÓMO REEMPLAZAR VALORES

## ⚠️ REGLA GENERAL:

**REEMPLAZÁS TODO** el texto placeholder (incluyendo las palabras como `TU_CLIENT_ID_AQUI`).

**LAS COMILLAS "" SÍ SE DEJAN** ✅

---

## 📋 EJEMPLO 1: CLIENT_ID

### ❌ INCORRECTO:

```python
# Dejaste el placeholder:
CLIENT_ID = "TU_CLIENT_ID_AQUI"

# Pusiste tu valor pero dejaste el placeholder:
CLIENT_ID = "TU_CLIENT_ID_AQUI1234567890123456"

# Le sacaste las comillas:
CLIENT_ID = 1234567890123456

# Pusiste paréntesis (no existen en Python para esto):
CLIENT_ID = "(1234567890123456)"
```

### ✅ CORRECTO:

```python
# Solo tu valor entre comillas:
CLIENT_ID = "1234567890123456"
```

---

## 📋 EJEMPLO 2: CLIENT_SECRET

### ❌ INCORRECTO:

```python
CLIENT_SECRET = "TU_CLIENT_SECRET_AQUIabcdefGHIJKLmnop"
CLIENT_SECRET = abcdefGHIJKLmnopQRST
CLIENT_SECRET = (abcdefGHIJKLmnopQRST)
```

### ✅ CORRECTO:

```python
CLIENT_SECRET = "abcdefGHIJKLmnopQRST"
```

---

## 📋 EJEMPLO 3: CODE

El CODE que copiás de Google tiene este formato:
```
TG-65f3a4b2e4b0c3000123456a-12345678
```

### ❌ INCORRECTO:

```python
CODE = "TG-XXXXXXXXXTG-65f3a4b2e4b0c3000123456a-12345678"
CODE = TG-65f3a4b2e4b0c3000123456a-12345678
CODE = "code=TG-65f3a4b2e4b0c3000123456a-12345678"  # ← NO incluyas "code="
```

### ✅ CORRECTO:

```python
CODE = "TG-65f3a4b2e4b0c3000123456a-12345678"
```

---

## 📋 EJEMPLO 4: ACCESS_TOKEN

El ACCESS_TOKEN tiene este formato:
```
APP_USR-1234567890-021523-abcdef123456-987654321
```

### ❌ INCORRECTO:

```python
ACCESS_TOKEN = "APP_USR-XXXXXXXXXXXXXXXXXXXXXXXXXAPP_USR-1234567890-021523-abcdef123456-987654321"
ACCESS_TOKEN = APP_USR-1234567890-021523-abcdef123456-987654321
ACCESS_TOKEN = "(APP_USR-1234567890-021523-abcdef123456-987654321)"
```

### ✅ CORRECTO:

```python
ACCESS_TOKEN = "APP_USR-1234567890-021523-abcdef123456-987654321"
```

---

## 🎯 RESUMEN VISUAL:

```python
# ANTES (archivo original):
CLIENT_ID = "TU_CLIENT_ID_AQUI"
CLIENT_SECRET = "TU_CLIENT_SECRET_AQUI"
CODE = "TG-XXXXXXXXX"

# DESPUÉS (con tus datos):
CLIENT_ID = "1234567890123456"
CLIENT_SECRET = "abcdefGHIJKLmnopQRST"
CODE = "TG-65f3a4b2e4b0c3000123456a-12345678"
```

---

## ⚡ TIPS:

1. **Las comillas se quedan** → `"tu_valor"`
2. **Paréntesis NO se usan** → ❌ `("valor")`
3. **Reemplazás TODO** el placeholder → No dejes `TU_CLIENT_ID_AQUI`
4. **Espacios NO** → ❌ `"valor 123"` (a menos que tu credencial realmente tenga espacios)

---

## 🔍 CÓMO SABER SI LO HICISTE BIEN:

### Tu archivo debería verse así:

```python
# ✏️ REEMPLAZÁ ESTOS 3 VALORES:
CLIENT_ID = "1234567890123456"               # ← Solo números/letras entre comillas
CLIENT_SECRET = "abcdefGHIJKLmnopQRST"       # ← Solo letras entre comillas
CODE = "TG-65f3a4b2e4b0c3000123456a-12345678"  # ← Empieza con TG-, entre comillas
```

### ❌ Si ves esto, está MAL:

```python
CLIENT_ID = "TU_CLIENT_ID_AQUI"              # ← No reemplazaste
CLIENT_ID = "TU_CLIENT_ID_AQUI1234567890"    # ← Pegaste mal
CLIENT_ID = 1234567890123456                 # ← Faltan comillas
CLIENT_ID = "(1234567890123456)"             # ← Paréntesis de más
```

---

## 💡 REGLA DE ORO:

**Si el valor original tiene comillas, tu valor también.**

**Borrás TODO el texto del placeholder y ponés solo tu valor.**

---

¡Con esto deberías poder reemplazar sin problemas! 🎯
