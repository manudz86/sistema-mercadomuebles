# 🔍 DEBUG - INSTRUCCIONES

## 🎯 OBJETIVO:

Ver exactamente qué está pasando cuando detectas alertas.

---

## 🔧 PASO 1: Instalar función con debug

**Reemplazar** en app.py la función `detectar_alertas_stock_bajo()` con:

→ Contenido de `FUNCION_con_DEBUG.py`

---

## 🧪 PASO 2: Preparar el test

### En la base de datos, verificar:

```sql
-- Ver stock de CEX160
SELECT sku, nombre, stock_actual, stock_full, tipo
FROM productos_base 
WHERE sku = 'CEX160';
```

**Anotar:** 
- Stock actual: ___
- Stock full: ___
- Total: ___

```sql
-- Ver ventas activas de CEX160
SELECT v.numero_venta, iv.sku, iv.cantidad, v.estado_entrega
FROM items_venta iv
JOIN ventas v ON iv.venta_id = v.id
WHERE iv.sku = 'CEX160' 
AND v.estado_entrega = 'pendiente';
```

**Anotar:** Cantidad de ventas pendientes: ___

---

## 🧪 PASO 3: Crear venta

1. Resetear todo (para empezar limpio):
   ```sql
   -- Borrar ventas de prueba
   DELETE FROM items_venta WHERE venta_id IN (
       SELECT id FROM ventas WHERE numero_venta LIKE 'VENTA-%'
   );
   DELETE FROM ventas WHERE numero_venta LIKE 'VENTA-%';
   
   -- Asegurar stock de CEX160
   UPDATE productos_base SET stock_actual = 2, stock_full = 0 WHERE sku = 'CEX160';
   ```

2. Crear **primera venta** de 1 CEX160

3. **VER LA CONSOLA** donde corre Flask (terminal/cmd)
   - Deberías ver prints con toda la info
   - Copiar TODO el output

4. Crear **segunda venta** de 1 CEX160

5. **VER LA CONSOLA** de nuevo
   - Debería decir "⚠️ SIN STOCK - DEBE ALERTAR"
   - Copiar TODO el output

---

## 📋 PASO 4: Mandame la info

Necesito que me mandes:

1. **Stock de CEX160** (del SELECT)
2. **Ventas activas** antes de las pruebas
3. **Output de consola** de la primera venta
4. **Output de consola** de la segunda venta
5. **Screenshot** si apareció o no el modal

---

## 🎯 QUÉ BUSCAR EN LA CONSOLA:

```
🔍 DEBUG - DETECTAR ALERTAS
Items vendidos: [{'sku': 'CEX160', 'cantidad': 1}]

📦 Procesando item: CEX160 x1
  → Es PRODUCTO BASE  (o Es COMBO)

📋 SKUs a verificar: {'CEX160'}
📋 Cantidades venta actual: {'CEX160': 1}

📊 Ventas activas en BD: {'CEX160': 0} (o {'CEX160': 1})

🔎 Verificando: CEX160
  ✅ Encontrado: Colchón Exclusive 160x190
  📊 Stock físico: 2
  📊 Vendido anterior: 0 (o 1)
  📊 Vendido actual: 1
  📊 Vendido TOTAL: 1 (o 2)
  📊 Disponible: 1 (o 0)
  ⚠️ SIN STOCK - DEBE ALERTAR (solo en la segunda)
```

---

**Con esa info podré ver exactamente qué está mal.** 🔍
