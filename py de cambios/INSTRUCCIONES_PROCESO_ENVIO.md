# 📦 PROCESO DE ENVÍO - INSTALACIÓN COMPLETA

## 🎯 QUÉ HACE:

### Vista:
- Muestra ventas con `estado_entrega = 'en_proceso'`
- Filtros completos (búsqueda, tipo entrega, método, zona, canal, pago)
- Información completa de cada venta

### 2 Acciones:
1. **✅ Marcar Entregada** 
   - Solo cambia estado a 'entregada'
   - NO toca stock (ya se descontó en Ventas Activas)

2. **❌ Cancelar y Devolver Stock**
   - Cambia estado a 'cancelada'
   - **DEVUELVE** el stock descontado
   - Respeta ubicaciones (DEP/FULL)
   - Recompone combos
   - Bases grandes devuelven 2 bases chicas

---

## 📝 INSTALACIÓN:

### PASO 1: Agregar Template

**Guardar como:** `templates/proceso_envio.html`

**Archivo:** `proceso_envio.html`

---

### PASO 2: Agregar Rutas en app.py

**Ubicación:** Después de las rutas de `/ventas/activas` (línea ~400 aprox)

**Acción:**
1. Buscar donde terminan las rutas de ventas activas
2. Pegar todo el contenido de: `proceso_envio_RUTAS.py`

Esto incluye:
- `@app.route('/ventas/proceso')` - Vista principal
- `@app.route('/ventas/proceso/<id>/entregada')` - Marcar entregada
- `@app.route('/ventas/proceso/<id>/cancelar')` - Cancelar y devolver
- `def devolver_stock_item()` - Función auxiliar
- `def devolver_stock_simple()` - Función auxiliar

---

### PASO 3: Actualizar Dashboard Principal

**En app.py, buscar la función `index()` (línea ~93):**

Cambiar:
```python
# Contar ventas en proceso
result = query_one("SELECT COUNT(*) as total FROM ventas WHERE estado_entrega = 'en_proceso'")
stats['ventas_en_proceso'] = result['total'] if result else 0
```

Por:
```python
# Contar ventas en proceso
result = query_one("SELECT COUNT(*) as total FROM ventas WHERE estado_entrega = 'en_proceso'")
stats['ventas_en_proceso'] = result['total'] if result else 0
```

(Ya está correcto, solo verifica que diga `'en_proceso'`)

---

### PASO 4: Agregar Link en Menú

**Opcional pero recomendado:**

En `templates/base.html`, buscar el menú de navegación y agregar:

```html
<li class="nav-item">
    <a class="nav-link" href="/ventas/proceso">
        <i class="bi bi-box-seam"></i> Proceso Envío
    </a>
</li>
```

---

### PASO 5: Reiniciar Flask

```bash
Ctrl+C
python app.py
```

---

## ✅ PRUEBA COMPLETA:

### Test 1: Flujo Normal

1. **Crear venta:**
   - 1x CEX140
   - 1x SEXP140
   - Método: "Flete Propio" (DEP)
   
2. **Anotar stock inicial:**
   - CEX140: ___
   - CEXP140: ___
   - BASE_CHOC140: ___

3. **En Ventas Activas:**
   - Click "Pasar a Proceso"
   - Verificar que stock se descontó

4. **Ir a Proceso de Envío:**
   ```
   http://localhost:5000/ventas/proceso
   ```
   - ✅ Debe aparecer la venta
   - ✅ 2 botones: "Entregada" y "Cancelar + Stock"

5. **Click "Marcar Entregada":**
   - ✅ Venta desaparece de Proceso
   - ✅ Stock sigue igual (no cambia)

---

### Test 2: Cancelar con Devolución

1. **Crear otra venta:**
   - 2x CEX140
   - Método: "Full" (FULL)

2. **Anotar stock antes:**
   - CEX140: ___

3. **Pasar a Proceso desde Activas:**
   - Stock se descuenta -2

4. **En Proceso de Envío:**
   - Click "Cancelar + Stock"
   - Confirmar

5. **Verificar:**
   - ✅ Venta desaparece
   - ✅ Stock CEX140 vuelve al valor original (+2)
   - ✅ Mensaje: "Stock devuelto correctamente"

---

### Test 3: Combo con Devolución

1. **Crear venta:**
   - 1x SEXP140 (sommier)
   - Método: "Flete Propio" (DEP)

2. **Anotar stock:**
   - CEXP140: ___
   - BASE_CHOC140: ___

3. **Pasar a Proceso:**
   - CEXP140: -1
   - BASE_CHOC140: -1

4. **Cancelar desde Proceso:**
   - Click "Cancelar + Stock"

5. **Verificar:**
   - ✅ CEXP140: Stock vuelve (+1)
   - ✅ BASE_CHOC140: Stock vuelve (+1)

---

### Test 4: Filtros

1. **Crear varias ventas en proceso:**
   - Venta A: Zona Capital, Full
   - Venta B: Zona Sur, Flete Propio
   - Venta C: Zona Capital, Flex

2. **Probar filtros:**
   - Filtro Zona: Capital → Solo A y C ✅
   - Filtro Método: Full → Solo A ✅
   - Búsqueda: "CEX" → Ventas con CEX ✅

---

## 📊 FLUJO COMPLETO DEL SISTEMA:

```
┌─────────────────────────────────────────────┐
│ NUEVA VENTA                                 │
│ - estado_entrega = 'pendiente'              │
│ - NO descuenta stock                        │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ VENTAS ACTIVAS                              │
│ - Muestra pendientes                        │
│                                             │
│ Acciones:                                   │
│ ┌─────────────────────────────────────────┐ │
│ │ PASAR A PROCESO                         │ │
│ │ - estado = 'en_proceso'                 │ │
│ │ - DESCUENTA STOCK                       │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ MARCAR ENTREGADA                        │ │
│ │ - estado = 'entregada'                  │ │
│ │ - DESCUENTA STOCK                       │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ CANCELAR                                │ │
│ │ - estado = 'cancelada'                  │ │
│ │ - NO descuenta stock                    │ │
│ └─────────────────────────────────────────┘ │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ PROCESO DE ENVÍO (NUEVO)                    │
│ - Muestra 'en_proceso'                      │
│                                             │
│ Acciones:                                   │
│ ┌─────────────────────────────────────────┐ │
│ │ MARCAR ENTREGADA                        │ │
│ │ - estado = 'entregada'                  │ │
│ │ - NO toca stock (ya descontado)         │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ CANCELAR Y DEVOLVER STOCK               │ │
│ │ - estado = 'cancelada'                  │ │
│ │ - DEVUELVE STOCK                        │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

---

## 🔍 DETALLES TÉCNICOS:

### Devolución de Stock:

```python
# Funciona exactamente al revés de descontar_stock_item()

# Descontar (Ventas Activas → Proceso):
UPDATE productos_base SET stock_actual = stock_actual - cantidad

# Devolver (Proceso → Cancelada):
UPDATE productos_base SET stock_actual = stock_actual + cantidad
```

### Ubicaciones:
```python
if ubicacion_despacho == 'FULL':
    # Almohadas: devuelve a stock_full
    UPDATE SET stock_full = stock_full + cantidad
    
    # Compac: devuelve a _FULL
    sku_real = sku.replace('_DEP', '_FULL')
    
else:  # DEP
    # Almohadas: devuelve a stock_actual
    UPDATE SET stock_actual = stock_actual + cantidad
    
    # Compac: devuelve a _DEP
    sku_real = sku.replace('_FULL', '_DEP')
```

### Combos:
```python
# SEXP140 x 1 devuelve:
# - CEXP140: +1
# - BASE_CHOC140: +1

# Consulta componentes igual que al descontar
# Pero SUMA en lugar de RESTAR
```

---

## 📦 ARCHIVOS ENTREGADOS:

1. **proceso_envio.html** - Template con filtros
2. **proceso_envio_RUTAS.py** - Rutas completas Python
3. **INSTRUCCIONES_PROCESO_ENVIO.md** - Esta guía

---

## ⚠️ IMPORTANTE:

**DIFERENCIA CLAVE entre Ventas Activas y Proceso:**

| Acción | Ventas Activas | Proceso de Envío |
|--------|----------------|------------------|
| Cancelar | NO descuenta stock | DEVUELVE stock |
| Marcar Entregada | DESCUENTA stock | NO toca stock |

**¿Por qué?**
- En Activas: Stock aún no se descontó
- En Proceso: Stock ya fue descontado

---

## 🐛 SI HAY ERRORES:

### "Estado no es en_proceso"
```
Verifica que la venta tenga estado_entrega = 'en_proceso'
SELECT estado_entrega FROM ventas WHERE id = X;
```

### Stock no se devuelve
```
1. Verifica que ubicacion_despacho tenga valor
2. Console del servidor debe mostrar los UPDATE
3. Ejecuta manualmente: SELECT * FROM productos_base WHERE sku='CEX140'
```

### Venta no aparece en Proceso
```
1. Verifica que pasaste la venta con "Pasar a Proceso" desde Activas
2. Query manual: SELECT * FROM ventas WHERE estado_entrega='en_proceso'
```

---

**¿Listo para instalar?** 🚀
