# 🚀 GUÍA: MEJORAS EN IMPORTACIÓN DE MERCADO LIBRE

## 📋 NUEVAS CARACTERÍSTICAS:

### 1️⃣ **Filtrar ventas ya importadas**
- ✅ NO muestra órdenes que ya están en tu sistema
- ✅ Compara el ID de orden de ML con `numero_venta` en BD
- ✅ Solo muestra órdenes nuevas para importar

### 2️⃣ **Importar datos de envío automáticamente**
- ✅ Dirección completa de entrega
- ✅ Tipo de envío (Mercadoenvios/Flex/Full)
- ✅ Ubicación de despacho (DEP/FULL)
- ✅ Zona inferida automáticamente (Capital/Sur/Norte/Oeste)
- ✅ Datos adicionales: Ciudad, Provincia, Código Postal

---

## 🔧 INSTALACIÓN:

### **PASO 1: Actualizar funciones en app.py**

#### 1.1 - Agregar función obtener_shipping_details (NUEVA)
**Ubicación:** Después de la función `procesar_orden_ml`

Copiá desde: `funciones_ml_ACTUALIZADAS.py` → Función `obtener_shipping_details`

---

#### 1.2 - Reemplazar función procesar_orden_ml
**Ubicación:** Buscar función `procesar_orden_ml` actual

**Reemplazarla** con la versión de: `funciones_ml_ACTUALIZADAS.py`

**Qué hace ahora:**
- ✅ Extrae datos de shipping de la orden
- ✅ Determina método de envío (Full/Flex/Mercadoenvios)
- ✅ Extrae dirección completa
- ✅ Infiere zona según ciudad

---

#### 1.3 - Reemplazar función ml_importar_ordenes
**Ubicación:** Buscar `@app.route('/ventas/ml/importar')`

**Reemplazarla** con la versión de: `funciones_ml_ACTUALIZADAS.py`

**Qué hace ahora:**
- ✅ Obtiene ventas ya importadas de la BD
- ✅ Filtra órdenes que ya existen
- ✅ Solo muestra órdenes nuevas

---

#### 1.4 - Reemplazar función ml_seleccionar_orden
**Ubicación:** Buscar `@app.route('/ventas/ml/seleccionar/<orden_id>')`

**Reemplazarla** con la versión de: `funcion_ml_seleccionar_orden_ACTUALIZADA.py`

**Qué hace ahora:**
- ✅ Guarda datos de shipping en sesión

---

#### 1.5 - Reemplazar función ml_guardar_mapeo
**Ubicación:** Buscar `@app.route('/ventas/ml/mapear', methods=['POST'])`

**Reemplazarla** con la versión de: `funcion_ml_guardar_mapeo_ACTUALIZADA.py`

**Qué hace ahora:**
- ✅ Guarda datos de shipping en sesión después del mapeo

---

### **PASO 2: Actualizar template nueva_venta_ml.html**

**Ubicación:** Sección "ENTREGA" (línea ~151-214)

**Reemplazarla** con el código de: `ACTUALIZAR_nueva_venta_ml_ENVIO.html`

**Qué hace ahora:**
- ✅ Precarga tipo de entrega desde ML
- ✅ Precarga método de envío (Mercadoenvios/Flex/Full)
- ✅ Precarga dirección completa
- ✅ Precarga zona inferida
- ✅ Muestra info adicional (ciudad, provincia, CP)

---

## 📊 CÓMO FUNCIONA:

### **FLUJO COMPLETO:**

```
1. Usuario hace click en "Importar de ML"
   ↓
2. Sistema trae órdenes de ML (últimas 50)
   ↓
3. Filtra órdenes ya importadas
   ↓
4. Procesa cada orden y extrae:
   - Productos
   - Comprador
   - 🆕 Datos de envío (dirección, método, zona)
   ↓
5. Muestra solo órdenes nuevas
   ↓
6. Usuario selecciona orden
   ↓
7. Sistema precarga formulario con:
   - Cliente
   - Productos
   - 🆕 Dirección
   - 🆕 Método de envío
   - 🆕 Zona
   ↓
8. Usuario verifica y guarda
```

---

## 🎯 EJEMPLO PRÁCTICO:

### **Orden de ML:**
```
Cliente: Fabio Durando
Producto: Colchón Compac 140x190 - $405,600
Envío: Full
Dirección: Av. Corrientes 1234, CABA
```

### **Formulario precargado:**
```
✅ Nombre: Fabio Durando
✅ Nickname: FABIODURANDO
✅ Producto: CCO140_FULL - Colchón Compac 140x190
✅ Cantidad: 1
✅ Precio: $405,600
✅ Tipo Entrega: Envío
✅ Método Envío: Full
✅ Ubicación: FULL
✅ Dirección: Av. Corrientes 1234, CABA
✅ Zona: Capital (inferida)
```

---

## 🗺️ INFERENCIA DE ZONA:

El sistema detecta automáticamente la zona según la ciudad:

| Ciudad | Zona Asignada |
|--------|---------------|
| Capital Federal, CABA | Capital |
| La Plata, Quilmes, Avellaneda | Sur |
| San Isidro, Tigre, Pilar | Norte-Noroeste |
| Morón, Merlo, Ituzaingó | Oeste |
| Otras | (vacío - seleccionar manual) |

---

## 📋 MÉTODO DE ENVÍO DETECTADO:

| ML logistic_type | Método en sistema |
|------------------|-------------------|
| `fulfillment` | Full |
| `cross_docking` | Flex |
| `me2` | Mercadoenvios |
| Otro | Mercadoenvios (default) |

---

## ✅ VERIFICACIÓN:

Para verificar que funciona:

### 1. Filtrado de ventas importadas:
1. Importá una orden de ML
2. Guardá la venta
3. Volvé a "Importar de ML"
4. ✅ Esa orden ya NO debería aparecer en la lista

### 2. Datos de envío:
1. Seleccioná una orden con envío
2. ✅ Verificá que el formulario tenga:
   - Dirección precargada
   - Método de envío correcto (Full/Flex/Mercadoenvios)
   - Zona inferida (si aplica)

---

## 🆘 TROUBLESHOOTING:

### **Las órdenes importadas siguen apareciendo:**
→ Verificá que reemplazaste la función `ml_importar_ordenes`

### **No trae la dirección:**
→ Verificá que reemplazaste `procesar_orden_ml`

### **La zona no se infiere:**
→ Normal si la ciudad no está en la lista de keywords
→ Podés seleccionarla manualmente

### **Método de envío siempre Mercadoenvios:**
→ ML podría no estar enviando el campo `logistic_type`
→ Podés cambiarlo manualmente en el formulario

---

## 📦 ARCHIVOS INCLUIDOS:

1. `funciones_ml_ACTUALIZADAS.py` - Funciones para app.py
2. `funcion_ml_seleccionar_orden_ACTUALIZADA.py` - Función específica
3. `funcion_ml_guardar_mapeo_ACTUALIZADA.py` - Función específica
4. `ACTUALIZAR_nueva_venta_ml_ENVIO.html` - Template actualizado
5. `GUIA_MEJORAS_IMPORTACION_ML.md` - Esta guía

---

## 🎉 BENEFICIOS:

### **ANTES:**
```
❌ Ves órdenes ya importadas (duplicados potenciales)
❌ Tenés que copiar la dirección manualmente
❌ Tenés que identificar si es Full o Mercadoenvios
❌ Tenés que seleccionar la zona manualmente
```

### **AHORA:**
```
✅ Solo ves órdenes nuevas (sin duplicados)
✅ Dirección precargada automáticamente
✅ Método de envío detectado (Full/Flex/Mercadoenvios)
✅ Zona inferida automáticamente (Buenos Aires)
✅ Solo verificás y guardás
```

---

## ⏱️ AHORRO DE TIEMPO:

**Por venta con envío:**
- Buscar dirección: ~20 seg
- Copiar dirección: ~10 seg
- Verificar método: ~5 seg
- Seleccionar zona: ~5 seg
- **Total ahorrado: ~40 segundos por venta**

**Con 30 ventas/día:**
- **20 minutos ahorrados diarios**
- **2.3 horas ahorradas semanales**

---

**¡Seguí la guía paso a paso y tendrás importación automática completa!** 🚀
