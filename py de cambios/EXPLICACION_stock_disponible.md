# 🔧 PROBLEMA: Stock Disponible Mal Calculado

## 📋 QUÉ PASABA:

La ruta `/stock` consultaba la vista `stock_disponible_ml` que:
- ❌ Solo mostraba stock físico
- ❌ NO restaba ventas activas
- ❌ Stock Disponible = Stock Físico (incorrecto)

**Resultado:**
```
CEX140: Stock Físico 3 | Disponible 3 ❌ (debería ser 0)
```

---

## ✅ SOLUCIÓN:

La nueva función calcula correctamente:

### 1. Obtiene productos base
```sql
SELECT sku, nombre, stock_actual, stock_full
FROM productos_base
```

### 2. Obtiene ventas activas (descompuestas)
```sql
SELECT sku, SUM(cantidad) as vendido
FROM items_venta
WHERE estado = 'pendiente'
-- Descomponiendo combos a componentes
```

### 3. Calcula stock disponible
```python
stock_disponible = stock_fisico - vendido
```

### 4. Determina estado
```python
if stock_disponible <= 0:
    estado = 'SIN_STOCK'
elif stock_disponible <= 2:
    estado = 'POCO_STOCK'
else:
    estado = 'DISPONIBLE'
```

---

## 🔧 INSTALACIÓN:

**Reemplazar** en app.py la función `ver_stock()` con:

→ Contenido de `RUTA_ver_stock_CORREGIDA.py`

---

## ✅ RESULTADO CORRECTO:

### CEX140 (3 vendidos):
```
Stock Físico: 3
Vendido: 3
Disponible: 0 ✅
Estado: SIN_STOCK
```

### SEX140 (1 combo vendido):
Al descomponerse en componentes (CEX140 + BASE):
```
CEX140:
  Stock Físico: 3
  Vendido: 1 (del combo SEX140)
  Disponible: 2 ✅
```

---

## 🎯 VENTAJAS:

- ✅ Cálculo en tiempo real
- ✅ Incluye combos descompuestos
- ✅ Mismo cálculo que el dashboard
- ✅ Mantiene todos los filtros

---

**¡Reemplazá la función y listo!** 🚀
