# 🔧 ERROR: items_venta is not defined

## 📋 PROBLEMA:

La variable `items_venta` no existe en tu función `guardar_venta()`.

---

## ✅ SOLUCIÓN (2 OPCIONES):

### OPCIÓN 1: Construir desde request.form (más segura)

En `guardar_venta()`, en la sección de DETECTAR ALERTAS, usar:

→ Código de `SOLUCION_items_vendidos.py`

Esto construye la lista directamente del formulario buscando campos `agregar_SKU`.

---

### OPCIÓN 2: Usar variable existente (necesito tu ayuda)

**Necesito que me muestres** cómo está tu función `guardar_venta()`.

Específicamente, buscar donde guardas los items en la BD. Algo como:

```python
# Ejemplo posible:
for key in request.form.keys():
    if key.startswith('agregar_'):
        sku = ...
        cantidad = ...
        # Aquí INSERT en items_venta
```

**O:**

```python
# Otro ejemplo:
items = []
for producto in productos:
    cantidad = request.form.get(f'agregar_{producto.sku}')
    if cantidad:
        items.append(...)
```

**Necesito ver esa parte** para saber cómo se llama tu variable y cómo la construyes.

---

## 🔧 CAMBIO RÁPIDO (Opción 1):

En `guardar_venta()`, **BUSCAR:**

```python
        # Pasar lista de items vendidos a la función
        items_vendidos_lista = []
        for item in items_venta:  # ← ESTA LÍNEA CAUSA EL ERROR
            items_vendidos_lista.append({
                'sku': item['sku'],
                'cantidad': item['cantidad']
            })
        
        productos_sin_stock = detectar_alertas_stock_bajo(cursor, items_vendidos_lista)
```

**REEMPLAZAR CON:**

```python
        # Construir lista de items vendidos desde el formulario
        items_vendidos_lista = []
        
        for key in request.form.keys():
            if key.startswith('agregar_'):
                sku = key.replace('agregar_', '')
                cantidad_str = request.form.get(key)
                
                if cantidad_str and int(cantidad_str) > 0:
                    items_vendidos_lista.append({
                        'sku': sku,
                        'cantidad': int(cantidad_str)
                    })
        
        print(f"\n🔍 Items a verificar: {items_vendidos_lista}")
        
        productos_sin_stock = detectar_alertas_stock_bajo(cursor, items_vendidos_lista)
```

---

## 📦 ARCHIVO:

**SOLUCION_items_vendidos.py** - Código completo de la sección

---

**¿Probás con ese cambio?** O mandame la parte de tu código donde insertás los items en la BD para ver qué variable usás. 🔍
