-- ============================================
-- UBICACIONES PARA ALMOHADAS (SIN ROMPER COMBOS)
-- ============================================

-- ============================================
-- PASO 1: VERIFICAR SITUACIÓN ACTUAL
-- ============================================

-- Ver almohadas actuales
SELECT sku, nombre, tipo, stock_actual 
FROM productos_base 
WHERE tipo = 'almohada'
ORDER BY sku;

-- Ver combos que usan almohadas (NO queremos romper esto)
SELECT pc.producto_sku, pc.componente_sku, pc.cantidad, pb.nombre
FROM productos_compuestos pc
JOIN productos_base pb ON pc.componente_sku = pb.sku
WHERE pb.tipo = 'almohada'
ORDER BY pc.producto_sku;

-- Ejemplos de lo que deberías ver:
-- PLATINOX4 usa PLATINO (cantidad: 4)
-- Combos de colchón+almohada usan SKUs de almohadas

-- ============================================
-- PASO 2: AGREGAR COLUMNA stock_full
-- ============================================

-- Agregar columna para stock en Full ML
ALTER TABLE productos_base 
ADD COLUMN stock_full INT DEFAULT 0 
COMMENT 'Stock en Full ML (0 = no aplica)' 
AFTER stock_actual;

-- Inicializar en 0 para todos los productos
UPDATE productos_base SET stock_full = 0;

-- ============================================
-- PASO 3: VERIFICAR QUE SE AGREGÓ CORRECTAMENTE
-- ============================================

-- Ver estructura de la tabla
DESCRIBE productos_base;

-- Debe mostrar:
-- stock_actual   | int
-- stock_full     | int     ← NUEVO
-- stock_minimo_pausar | int

-- Ver almohadas con la nueva columna
SELECT sku, nombre, stock_actual AS dep, stock_full AS full 
FROM productos_base 
WHERE tipo = 'almohada'
ORDER BY sku;

-- ============================================
-- CÓMO FUNCIONA AHORA:
-- ============================================

/*
Tabla productos_base:
┌─────────┬──────────────────┬──────────────┬────────────┐
│ sku     │ nombre           │ stock_actual │ stock_full │
├─────────┼──────────────────┼──────────────┼────────────┤
│ PLATINO │ Almohada Platino │ 50 (DEP)     │ 0 (FULL)   │
│ BAMBOO  │ Almohada Bamboo  │ 30 (DEP)     │ 0 (FULL)   │
└─────────┴──────────────────┴──────────────┴────────────┘

Productos Compuestos (NO SE ROMPE):
┌───────────┬────────────────┬──────────┐
│ producto  │ componente_sku │ cantidad │
├───────────┼────────────────┼──────────┤
│ PLATINOX4 │ PLATINO        │ 4        │ ← Sigue funcionando
└───────────┴────────────────┴──────────┘

Cargar Stock:
- Cargar en Depósito → suma a stock_actual
- Cargar en Full → suma a stock_full

Transferir Stock:
- Depósito → Full: resta stock_actual, suma stock_full
- Full → Depósito: resta stock_full, suma stock_actual

Ventas:
- Primero intenta descontar de stock_actual (DEP)
- Si no hay, puede descontar de stock_full (FULL)
- Los combos siguen funcionando con el SKU original
*/

-- ============================================
-- PASO 4: EJEMPLOS DE USO
-- ============================================

-- Ejemplo: Cargar 20 almohadas PLATINO en Depósito
UPDATE productos_base 
SET stock_actual = stock_actual + 20 
WHERE sku = 'PLATINO';

-- Ejemplo: Cargar 10 almohadas PLATINO en Full
UPDATE productos_base 
SET stock_full = stock_full + 10 
WHERE sku = 'PLATINO';

-- Ejemplo: Transferir 5 de Depósito a Full
UPDATE productos_base 
SET stock_actual = stock_actual - 5,
    stock_full = stock_full + 5
WHERE sku = 'PLATINO';

-- Ver resultado
SELECT sku, nombre, stock_actual AS deposito, stock_full AS full 
FROM productos_base 
WHERE sku = 'PLATINO';

-- ============================================
-- VENTAJAS DE ESTA SOLUCIÓN:
-- ============================================

/*
1. ✅ SKUs NO cambian
   - PLATINO sigue siendo PLATINO
   - BAMBOO sigue siendo BAMBOO
   
2. ✅ Combos NO se rompen
   - PLATINOX4 sigue usando PLATINO
   - productos_compuestos funciona igual
   
3. ✅ Stock separado por ubicación
   - stock_actual = Depósito
   - stock_full = Full ML
   
4. ✅ Fácil de extender
   - Misma columna para Compac si quieres unificar
   - Compatible con sistema actual
   
5. ✅ Fácil de revertir
   - Solo eliminar la columna si algo sale mal
*/

-- ============================================
-- ROLLBACK (si algo sale mal)
-- ============================================

-- Para volver atrás:
-- ALTER TABLE productos_base DROP COLUMN stock_full;

-- ============================================
-- RESUMEN PARA TODOS LOS PRODUCTOS:
-- ============================================

/*
COMPAC (con _DEP y _FULL en SKU):
- CCO100_DEP → stock_actual
- CCO100_FULL → stock_actual
(Dos filas separadas)

ALMOHADAS (con columna stock_full):
- PLATINO → stock_actual (DEP) + stock_full (FULL)
(Una sola fila con dos columnas)

OTROS PRODUCTOS:
- CEX140, CPR20, etc. → solo stock_actual
(stock_full siempre en 0)
*/

-- ============================================
-- ¿QUÉ SIGUE?
-- ============================================

/*
Después de ejecutar este SQL, necesitas:

1. Modificar app.py:
   - cargar_stock(): permitir elegir ubicación para almohadas
   - transferir_stock(): agregar sección para almohadas
   - dashboard_visual(): mostrar ambas columnas para almohadas
   
2. Crear interfaz de transferencia para almohadas
   
3. Actualizar historial para registrar ubicación
   
4. Modificar nueva_venta() para descontar de la ubicación correcta
*/
