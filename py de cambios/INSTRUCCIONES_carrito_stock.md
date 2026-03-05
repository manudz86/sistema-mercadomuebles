# 🛒 CARRITO DE CARGA DE STOCK - INSTALACIÓN

## 🎯 PROBLEMA ACTUAL:

Al cargar stock:
- Se va poniendo cantidad en cada SKU
- Con muchos productos, no se ve qué se cargó antes de confirmar
- No hay vista previa del total a cargar

---

## ✅ SOLUCIÓN:

**Carrito de Carga** con vista previa en tiempo real:

```
┌──────────────────────────────────────┐
│ Buscador                             │
│ [Buscar producto...]                 │
│                                      │
│ Formulario Individual                │
│ Cantidad: [5]                        │
│ [+ Agregar al Carrito]               │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ 🛒 CARRITO DE CARGA (3)              │
├──────────────────────────────────────┤
│ • CEX140: +3 unidades (DEP)     [X] │
│ • SEXP140: +5 unidades (FULL)   [X] │
│ • CDO80: +2 unidades (DEP)      [X] │
├──────────────────────────────────────┤
│ [Confirmar Carga (10 unidades)]     │
│ [Limpiar Todo]                       │
└──────────────────────────────────────┘
```

---

## 📝 CARACTERÍSTICAS:

### ✅ Vista Previa en Tiempo Real:
- Panel lateral con todos los productos agregados
- Cantidad total de unidades
- Ubicación (DEP/FULL) de cada item
- Motivo de carga

### ✅ Gestión del Carrito:
- Agregar productos uno por uno
- Eliminar items individuales
- Limpiar todo el carrito
- Editar cantidades (agregando más del mismo producto)

### ✅ Modal de Confirmación Final:
- Tabla resumen de toda la carga
- Total de unidades y productos
- Confirmación antes de ejecutar

---

## 🚀 INSTALACIÓN:

### PASO 1: Reemplazar Template

**Ubicación:** `templates/cargar_stock.html`

**Acción:** Reemplazar con: `cargar_stock_CON_CARRITO.html`

---

### PASO 2: Agregar Rutas en app.py

**Ubicación:** En app.py, agregar estas 2 rutas nuevas:

#### Ruta 1: API de Productos (línea ~800 aprox)
```python
@app.route('/api/productos')
def api_productos():
    # Copiar desde RUTAS_carrito_stock.py
```

#### Ruta 2: POST Cargar Stock (línea ~850 aprox)
```python
@app.route('/cargar-stock', methods=['POST'])
def cargar_stock_carrito():
    # Copiar desde RUTAS_carrito_stock.py
```

**Nota:** Si ya existe una ruta `/cargar-stock` POST, renombrar la nueva a `/cargar-stock-carrito` y actualizar en el JavaScript del template.

---

### PASO 3: Verificar tabla historial_movimientos

**Verificar que existe:**
```sql
DESCRIBE historial_movimientos;
```

**Si no existe, crear:**
```sql
CREATE TABLE historial_movimientos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    tipo_movimiento ENUM('carga', 'descarga', 'transferencia', 'ajuste') NOT NULL,
    cantidad INT NOT NULL,
    ubicacion VARCHAR(20),
    motivo TEXT,
    usuario VARCHAR(100),
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sku (sku),
    INDEX idx_fecha (fecha)
);
```

---

### PASO 4: Reiniciar

```bash
Ctrl+C
python app.py
```

---

## ✅ CÓMO USAR:

### Flujo Completo:

1. **Buscar producto:**
   - Escribir en el buscador: "CEX" o "Exclusive"
   - Click en el producto deseado

2. **Completar formulario:**
   - Cantidad: 5
   - Ubicación: Stock General (DEP) o Stock FULL ML
   - Motivo: "Compra proveedor X"
   - Click "Agregar al Carrito"

3. **Repetir para más productos:**
   - El formulario se cierra
   - Buscar otro producto
   - Agregar al carrito
   - El panel derecho muestra todos los agregados

4. **Ver carrito:**
   - Panel derecho muestra:
     * Cada producto con cantidad
     * Ubicación (DEP/FULL)
     * Motivo
     * Botón [X] para eliminar individual

5. **Confirmar carga:**
   - Click "Confirmar Carga (X unidades)"
   - Aparece modal con tabla resumen
   - Click "Confirmar y Cargar"
   - ✅ Stock actualizado

---

## 🎨 DISEÑO VISUAL:

### Layout de 2 Columnas:

```
┌─────────────────────────────────┬──────────────────────┐
│ IZQUIERDA (8 cols)              │ DERECHA (4 cols)     │
│                                 │                      │
│ [Buscador]                      │ 🛒 CARRITO (sticky)  │
│                                 │                      │
│ Resultados:                     │ Item 1          [X]  │
│ • CEX140 → (click)              │ Item 2          [X]  │
│ • SEXP140                       │ Item 3          [X]  │
│                                 │                      │
│ ┌─────────────────────────────┐│ ─────────────────── │
│ │ Formulario de Carga      [X]││ [Confirmar (10)]    │
│ │ CEX140 - Exclusive 140      ││ [Limpiar Todo]      │
│ │ Cantidad: [5]               ││                      │
│ │ Ubicación: [DEP ▼]          ││                      │
│ │ Motivo: [Compra...]         ││                      │
│ │ [+ Agregar al Carrito]      ││                      │
│ └─────────────────────────────┘│                      │
└─────────────────────────────────┴──────────────────────┘
```

---

## 📊 EJEMPLO DE USO:

### Escenario: Cargar stock de 3 productos

**1. Agregar CEX140:**
```
Buscar: "cex"
Click: CEX140 - Colchón Exclusive 140x190
Cantidad: 3
Ubicación: DEP
Motivo: "Compra Proveedor ABC"
[Agregar al Carrito]
```

**2. Agregar SEXP140:**
```
Buscar: "sexp"
Click: SEXP140 - Sommier Exclusive Pillow 140x190
Cantidad: 5
Ubicación: FULL ML
Motivo: "Stock para Full"
[Agregar al Carrito]
```

**3. Agregar CDO80:**
```
Buscar: "doral"
Click: CDO80 - Colchón Doral 80x190
Cantidad: 2
Ubicación: DEP
Motivo: "Compra Proveedor ABC"
[Agregar al Carrito]
```

**4. Ver Carrito:**
```
🛒 CARRITO DE CARGA (3)
━━━━━━━━━━━━━━━━━━━━━━
• CEX140: +3 unidades (DEP)        [X]
  Compra Proveedor ABC
  
• SEXP140: +5 unidades (FULL)      [X]
  Stock para Full
  
• CDO80: +2 unidades (DEP)         [X]
  Compra Proveedor ABC
━━━━━━━━━━━━━━━━━━━━━━
[Confirmar Carga (10 unidades)]
[Limpiar Todo]
```

**5. Confirmar:**
```
Modal aparece con tabla:
┌────────┬─────────────┬──────────┬──────────┬─────────────┐
│ SKU    │ Producto    │ Cantidad │ Ubicación│ Motivo      │
├────────┼─────────────┼──────────┼──────────┼─────────────┤
│ CEX140 │ Colchón...  │    +3    │   DEP    │ Compra...   │
│SEXP140 │ Sommier...  │    +5    │   FULL   │ Stock...    │
│ CDO80  │ Colchón...  │    +2    │   DEP    │ Compra...   │
└────────┴─────────────┴──────────┴──────────┴─────────────┘

Total: 10 unidades en 3 productos

[Cancelar]  [Confirmar y Cargar]
```

---

## 🔍 VENTAJAS:

### Antes (sin carrito):
```
❌ Buscas producto
❌ Pones cantidad
❌ Confirmas
❌ Buscas otro
❌ Pones cantidad
❌ Confirmas
❌ No ves qué cargaste antes
```

### Después (con carrito):
```
✅ Buscas productos
✅ Agregas al carrito uno por uno
✅ VES TODO lo que vas a cargar
✅ Puedes eliminar/editar antes
✅ Confirmas TODO de una vez
```

---

## 📦 ARCHIVOS:

1. **cargar_stock_CON_CARRITO.html** - Template con carrito
2. **RUTAS_carrito_stock.py** - Rutas de API
3. **INSTRUCCIONES_carrito_stock.md** - Esta guía

---

## ⚠️ IMPORTANTE:

### Si ya tienes una ruta POST /cargar-stock:

**Opción 1:** Renombrar la nueva ruta:
```python
@app.route('/cargar-stock-carrito', methods=['POST'])
```

Y en el JavaScript del template (línea ~370):
```javascript
const response = await fetch('/cargar-stock-carrito', {
```

**Opción 2:** Eliminar la ruta antigua si ya no se usa.

---

## 🎉 RESULTADO FINAL:

Con el carrito de carga:
- ✅ Vista previa de toda la carga
- ✅ Gestión fácil de items
- ✅ Modal de confirmación final
- ✅ Total de unidades visible
- ✅ Eliminar items antes de confirmar
- ✅ Todo en una sola confirmación

**¿Instalamos el carrito de carga?** 🛒
